import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize
from scipy.special import kn
import os
import pandas as pd
import re
import warnings
from sqdtoolz.Utilities.FileIO import FileIOReader
from resonator_tools import circuit  # type: ignore
from pprint import pprint
from pathlib import Path
import csv

warnings.filterwarnings("ignore", "Covariance of the parameters could not be estimated")

# imports for plotting (optional)
plot_backend = None
try:
    from bokeh.models import Whisker, ColumnDataSource, TeeHead, Band, Range1d
    from bokeh.models.formatters import FuncTickFormatter, NumeralTickFormatter
    from bokeh.plotting import figure, show
    from bokeh.io import output_notebook, export
    from bokeh.palettes import Viridis256, Category10, Category20
    from bokeh.layouts import gridplot
except Exception as e:
    import warnings
    warnings.warn(f"Bokeh not imported: {e}. Requires version 2.4.3.")
    PLOT_BACKEND = "matplotlib"
else:
    PLOT_BACKEND = "bokeh"

class ResonatorPowerSweep:
    """
    Class for analysis and plotting of power-swept Q-factor
    measurements for CPW resonators taken at a single temperature.
    Includes TLS-fitting capabilities.

    Inputs:
        - data_path     The data path where all data is contained.
                        Can be in sub-directories of the path.
        - sample_name   Name of the sample
        - save_path     Directory where all output files should
                        be saved (Defaults to data_path).
        - res_freqs     List of expected resonator frequencies in Hz.
        - power_dict    Dictionary of keywords used for different line
                        attenuations during measurement runs.
                        e.g. power_dict = {"lowPower" : -120,
                                           "midPower" : -120,
                                           "default" : -70}
        - TLSfit_bounds (Optional) Bounds for fitting parameters
                        [F_delta_TLS0, n_c, Q_HP, beta]. Tuple of lists,
                        defaults to ([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1])
        - print_log     Boolean to choose if prinouts occur during
                        execution (optional, defaults to False)
        - with_fit      Boolean to choose whether or not to fit data with
                        a TLS model
        - n_ph_lims     Photon number range to be used for fitting and 
                        plotting
        - Qi_lims      Limits for Qi values to be used for fitting and
                        plotting. Defaults to [1e3, 1e8].
        - TLS_model     Which TLS model to use for fitting. Defaults to "mcrae".
        - temperature   Temperature of the measurement in Kelvin.
                        Defaults to 30 mK.
        - notebook      Boolean to choose whether to use Bokeh notebook
                        output (default False). If True, Bokeh figures
                        will not export LaTeX text.
        - fit_data      Dictionary containing pre-fitted data to be used
                        for plotting. If provided, it will be used instead
                        of fitting the data again.
    """

    def __init__(
        self,
        data_path=None,
        sample_name=None,
        temperature=30*1e-3,
        save_path=None,
        power_dict={"lowPower" : -132, 
                    "highPower" : -82,
                    "default" : -82
                    },
        TLSfit_bounds=None,
        print_log=False,
        notebook=False,
        fit_data={},
        with_fit=None,
        n_ph_lims=[0, 1e10],
        qi_lims=[1e3, 5e7],
        TLS_model="mcrae"
    ):
        # initialise data
        self.data_path = data_path
        if save_path == None:
            self.save_path = data_path
        else:
            self.save_path = save_path
        self.name = sample_name
        self.power_dict = power_dict
        self.T = temperature
        self.TLSfit_bounds = TLSfit_bounds
        self.print_log = print_log
        self.data = {}
        self.fit_data = fit_data
        self.res_data = {}
        self.num_resonators = None
        self.frequencies = []
        self.freq_bin_labels = []
        self.do_TLS_fit = with_fit
        self.n_ph_lims = n_ph_lims
        self.TLS_model = TLS_model
        self.qi_lims = qi_lims

        # private class variables
        self._data_file_name = "data.h5"
        self._config_file_name = "experiment_configurations.txt"
        self._fitted_data_file_name = "circlefit.txt"
        self._data_from_text_file = False

        # figure
        self.plot_backend = PLOT_BACKEND
        if self.plot_backend == "bokeh":
            if notebook:
                output_notebook()
                warnings.warn(
                    f"\nNotebook output set (by notebook=True)... please note that LaTeX text in Bokeh figures will not be exported.\n"
                )
            self._colourmap = Viridis256
            self.fig_bokeh = figure(
                width=1000,
                height=600,
                x_axis_label=r"Photon number  ⟨n⟩",
                y_axis_label=r"$$Q_i$$",
                y_axis_type="log",
                x_axis_type="log",
            )
        else:
            self._colourmap = plt.cm.viridis
        self.fig_mpl = plt.figure(figsize=(10, 6))
        self.ax_ph_mpl = self.fig_mpl.add_subplot(111)
        plt.close(self.fig_mpl)  # prevent display for now

    # import data from file
    def import_data(
        self,
        line_attenuation=0,
        power_dict=None,
        additional_attenuation=0,
        print_log="none",
        files_to_ignore=None,
        power_config_order="last",
        from_text_file=False,
        qi_lims=None
    ):
        """
        Searches for and imports all data.h5 files in a given directory into a dictionary. Extracts the VNA power and measurement name corresponding to each data file.

        The extracted data and metada are stored in self.data with structure:

            self.data = {'<measurement_name>' : {
                            'raw_data' : {
                                ...
                            }
                        }

        Inputs:
        - line_attenuation          Attenuation on measurement line
                                    (overwritten by self.power_dict).
                                    Only use if all measurements were taken
                                    with the same attenuation.
        - power_dict                Dictionary of key-value pairs of keyword
                                    containing power reference in an imported
                                    filename with the corresponding attenuation
                                    value.
        - additional_attenuation    Additional attenuation on line (i.e. if
                                    you want to add a constant to attenuations
                                    defined in self.power_dict)
        - print_log                 Options for printout. Defaults to "errors".
                                    Other options are "all" or "none".
        - files_to_ignore           List of files that will be skipped
                                    during data import. Should be a list of strings.
        - power_config_order        Which power value should we look for in the 
                                    config file? Defaults to 'first', other options
                                    are 'last'.
        - from_text_file            Boolean to choose whether to read from circlefit.txt 
                                    if it exists.

        Outputs:
        - self.data                 Dictionary containing measurement data and metadata.
        """
        if from_text_file == True or isinstance(from_text_file, str):
            self._data_from_text_file = True
        power_dict = self.power_dict if power_dict == None else 0
        assert power_config_order in ["first", "last"], "power_config_order should be either 'first' or 'last'."
        assert print_log in [
            "errors",
            "all",
            "none",
        ], "Print log options are 'errors', 'all', or 'none'."
        if self.print_log == False:
            print_log = "none"
        if files_to_ignore:
            assert isinstance(
                files_to_ignore, list
            ), "files_to_ignore should be a list of strings, e.g. ['file1', 'file2']."
            assert isinstance(
                files_to_ignore[0], str
            ), "Entries in list files_to_ignore should be strings, e.g. ['file1', 'file2']."
        if qi_lims == None:
            qi_lims = self.qi_lims
        else:
            self.qi_lims = qi_lims
        if print_log != "none":
            print(f"Importing data from {self.data_path}\n")

        # IMPORT METHOD: DIRECT PATH FROM TEXT
        if isinstance(from_text_file, str):
            # Direct path to text file
            fit_data_path = from_text_file
            if os.path.isfile(fit_data_path) and "circlefit.txt" in os.path.basename(fit_data_path):
                self.fit_data = {}  # clear fit_data
                with open(fit_data_path, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter='\t')  # Tab-delimited
                    for header in reader.fieldnames:
                        self.fit_data[header] = []
                    for row in reader:
                        for header in reader.fieldnames:
                            value = row[header]
                            try:
                                self.fit_data[header].append(float(value) if value.replace('.', '', 1).isdigit() else value)
                            except ValueError:
                                self.fit_data[header].append(value)
                self.fit_data = pd.DataFrame(self.fit_data)  # Convert to DataFrame
                self.trim_fit_data_by_qi(qi_lims=qi_lims)
                print(f"Read {fit_data_path} into self.fit_data (direct path).")
                return self.fit_data
            else:
                print(f" Invalid path or missing 'circlefit.txt': {fit_data_path}")
                print(f" Continuing to search for data.h5 files in {self.data_path}...")

        # IMPORT METHOD LOOP THROUGH DIRECTORY
        for root, _, files in os.walk(self.data_path):
            root_path = Path(root)
            root_shortened = Path(*root_path.parts[-2:])
            print(f" Checking {root}...")

            # IMPORT METHOD: SEARCH FOR `circlefit.txt` IN DIRECTORY AND IMPORT IF IT EXISTS
            if from_text_file == True:
                # first, check for existing circlefit data
                circlefit_match = next((f for f in files if "circlefit.txt" in f), None)
                if circlefit_match:
                    # read circlefit into self.fit_data, skip searching
                    self.fit_data = {} # clear fit_data
                    fit_data_path = os.path.join(root, circlefit_match)
                    with open(fit_data_path, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f, delimiter='\t')  # Tab-delimited
                        # get headers 
                        for header in reader.fieldnames:
                            self.fit_data[header] = []
                        for row in reader:
                            if not any(ignored in row["measurement name"] for ignored in files_to_ignore):
                                for header in reader.fieldnames:
                                    value = row[header]
                                    try:
                                        # Try to convert to float if possible
                                        self.fit_data[header].append(float(value) if value.replace('.', '', 1).isdigit() else value)
                                    except ValueError:
                                        # If it's not a number, keep it as a string
                                        self.fit_data[header].append(value)
                    self.fit_data = pd.DataFrame(self.fit_data)  # Convert to DataFrame
                    print(f'  Read {circlefit_match} into self.fit_data')
                    self.trim_fit_data_by_qi(qi_lims=qi_lims)
                    return self.fit_data
                # if circlefit.text is not found, continue
                else:
                    continue

            # IMPORT METHOD: FROM H5 FILE FOUND IN DIRECTORY
            if files_to_ignore:
                ignore_match = [(i in str(root_shortened)) for i in files_to_ignore]
                good_file = True not in ignore_match
            else:
                good_file = True
            if (
                (self._data_file_name in files)
                and (self._config_file_name in files)
                and good_file
            ):
                attenuation = line_attenuation
                file_path = os.path.join(root, self._data_file_name)
                # read data
                cur_data = FileIOReader(file_path)
                arr = cur_data.get_numpy_array()
                freqs_meas = cur_data.param_vals[1]
                i_vals, q_vals = arr[0, :, 0], arr[0, :, 1]
                # Check for NaNs or infinite values
                if np.isnan(i_vals).any() or np.isinf(i_vals).any():
                    if print_log != "none":
                        print(
                            "'i_vals' contains NaNs or infinite values. Skipping data retrieval."
                        )
                elif np.isnan(q_vals).any() or np.isinf(q_vals).any():
                    if print_log != "none":
                        print(
                            "'q_vals' contains NaNs or infinite values. Skipping data retrieval."
                        )
                else:
                    # add line attenuation by dictionary
                    if self.power_dict != None:
                        if "default" not in self.power_dict.keys():
                            self.power_dict["default"] = 0
                            print(f"There was no 'default' value in your power_dict. Setting default=0 and proceeding.") if self.print_log else 0
                        for label, _ in self.power_dict.items():
                            if label.casefold() in root.casefold():
                                attenuation = (
                                    self.power_dict[label] + additional_attenuation
                                )
                                break
                            else:
                                attenuation = (
                                    self.power_dict["default"] + additional_attenuation
                                )
                    # add constant attenuation (i.e. same physical attenuation for all measurements)
                    elif line_attenuation != 0:
                        attenuation = line_attenuation
                    else:
                        attenuation = line_attenuation
                        warnings.warn(
                            "You have not added any additional attenuation to your data."
                            "Power will be calculated directly from the VNA output power."
                        )
                # get VNA measurement power, and adjust to include line attenuation
                config_file_path = os.path.join(root, self._config_file_name)
                with open(config_file_path, "r") as param_file:
                    content = param_file.read()
                    matches = re.findall(r'"Power":\s*(-?\d+\.\d+)', content)
                    if matches:
                        if power_config_order == "last":
                            vna_power = float(matches[-1])
                        elif power_config_order == "first":
                            vna_power = float(matches[0])
                        else:
                            vna_power = 0
                            warnings.warn("No power value found in config file. Setting VNA power to 0 dBm.")
                        total_power = vna_power + attenuation
                    self.data[str(root_shortened)] = {
                        "raw_data": {
                            "freqs": freqs_meas,
                            "i_vals": i_vals,
                            "q_vals": q_vals,
                            "iq_vals": i_vals + 1j * q_vals,
                            "power": total_power,
                            "line_attenuation": attenuation,
                            "measurement_name": str(root_shortened),
                        }
                    }
                    if print_log == "all":
                        print(f"Collected\t\t{root_shortened}")
            else:
                if print_log != "none":
                    print(f"Invalid\t\t{root_shortened}")
        assert (self.data or self.fit_data), "No valid data found at data_path."
        if from_text_file != False:
            self.trim_fit_data_by_qi(qi_lims=qi_lims)
        print("\nData import complete!")
        return self.data

    # do circlefit
    def do_circlefit(
        self, expected_qi_lims=(1e3, 1e8), remove_duplicates=True, n_ph_lims=None, save_fit=True, circuit_type="notch_port"
    ):
        """
        Does circlefits on measurement runs contained in self.data['rawdata'].
        Using fitting from https://github.com/sebastianprobst/resonator_tools.
        Adds fitted data to self.data in nested dictionary 'fit'. Structure:

            self.data = {'<measurement_name>' : {
                            'raw_data' : {
                                ...
                            },
                            'fit' : {
                                ...
                            }
                        }

        Inputs:
        - expected_qi_lims  Upper and lower limits on reasonable Qi values
                            obtained from circlefit. Defined by default as
                            (1e3, 1e8).
        - print_log         Boolean value to print live log while fitting.
                            Defaults to True.
        - remove_duplicates Boolean to choose whether duplicates in
                            power should be removed
        - save_fit          Boolean to save fitted data to self.save_path
                            (tab-delimited .txt file). Defaults to True.
        - circuit_type      (Defaults to "notch_port") Type of measurement to
                            fit. Options are "notch_port" or "reflection_port".

        Outputs:
        - self.fit_data     Pandas DataFrame containing all fitted values for
                            each measurement.
        """

        # exit if fit_data already exists
        if isinstance(self.fit_data, pd.DataFrame):
            if not self.fit_data.empty:
                if 'absQc' in self.fit_data.columns:
                    self.fit_data.rename(columns={'absQc': 'Qc_dia_corr'}, inplace=True)
                # sort self.fit_data
                self.sort_fit_data(n_ph_lims=n_ph_lims)
                # add frequency binning to help with plotting
                self.get_frequency_bins()
                print(f"Checked self.fit_data which already existed.")
                return self.fit_data

        assert (isinstance(expected_qi_lims, (list, tuple))) and (
            len(expected_qi_lims) == 2
        ), "expected_qi_lims should be a list or tuple of length two (min, max)."

        assert self.data, "Run import_data() first - there's no data yet!"

        fits_completed = 0
        invalid_data = []  # to track invalid data runs (failed fitting)
        for measurement_name, measurement_data in self.data.items():
            assert ("freqs" in measurement_data["raw_data"]) and (
                "iq_vals" in measurement_data["raw_data"]
            ), "'raw_data' should have keys 'freqs' and 'iq_vals' to allow for fitting."
            # setup circlefit
            if circuit_type == "notch_port":
                port = circuit.notch_port()
            elif circuit_type == "reflection_port":
                port = circuit.reflection_port()
            port.add_data(
                measurement_data["raw_data"]["freqs"],
                measurement_data["raw_data"]["iq_vals"],
            )
            try:
                port.autofit()
            except:
                print(f"Fitting {measurement_name} failed - skipping import.")
                invalid_data.append(measurement_name)
            else:
                if circuit_type == "reflection_port":
                    # rename fit results to match notch_port
                    port.fitresults["Qi_dia_corr"] = port.fitresults["Qi"]
                    port.fitresults["absQc"] = port.fitresults["Qc"]
                # write fit results to data dictionary
                if (
                    expected_qi_lims[0]
                    < port.fitresults["Qi_dia_corr"]
                    < expected_qi_lims[1]
                ):
                    fit_keys = port.fitresults.keys()
                    self.data[measurement_name]["fit"] = {}
                    # add fit results to self.data
                    for key in fit_keys:
                        self.data[measurement_name]["fit"][key] = port.fitresults[key]
                    # include single photon power calc and power
                    if circuit_type == "notch_port":
                        single_photon_power = port.get_single_photon_limit(diacorr=True)
                        n_ph = port.get_photons_in_resonator(power=measurement_data['raw_data']['power'], diacorr=True)
                    elif circuit_type == "reflection_port":
                        single_photon_power = port.get_single_photon_limit()
                        n_ph = port.get_photons_in_resonator(power=measurement_data['raw_data']['power'])
                    self.data[measurement_name]["fit"][
                        "single photon power"
                    ] = single_photon_power
                    self.data[measurement_name]["fit"]["power"] = measurement_data[
                        "raw_data"
                    ]["power"]
                    self.data[measurement_name]["fit"]["measurement name"] = (
                        measurement_data["raw_data"]["measurement_name"]
                    )
                    fits_completed += 1
                    filename_only = re.split(r'[\\/]', measurement_name)[-1]
                    (
                        print(
                            f"{fits_completed}\t{filename_only}\t"
                            f"f = {port.fitresults['fr']:.1e}, "
                            f"Qi = {port.fitresults['Qi_dia_corr']:.1e}, "
                            f"P = {measurement_data['raw_data']['power']:.1f} dBm "
                            f"({measurement_data['raw_data']['line_attenuation']} dB)"
                            f"\t-> n_ph = {n_ph:.1e}"
                        )
                        if self.print_log == True
                        else 0
                    )
                else:
                    (
                        print(f"x\t{measurement_name}\tQi out of range")
                        if self.print_log == True
                        else 0
                    )
                    invalid_data.append(measurement_name)
        print("Fitting complete.")
        # remove invalid measurements from self.dict
        for invalid_measurement in invalid_data:
            self.data.pop(invalid_measurement)
        # make sure fit data has been added to dictionary
        self.assert_subkey_exists(self.data, "fit")
        # add n_ph to dictionary
        self.n_ph_calculator()
        # sort fit data and add to self.fit_data
        self.fit_data_to_sorted_dataframe(n_ph_lims=n_ph_lims)
        # add frequency binning to help with plotting
        self.get_frequency_bins()
        # remove duplicates
        self.remove_duplicates() if remove_duplicates else 0
        # save data to text file
        if save_fit:
            txt_output = os.path.join(self.save_path, f"{self.name}_circlefit.txt")
            if circuit_type == "notch_port":
                self.df_to_csv(
                    self.fit_data,
                    txt_output,
                    columns_to_use=[
                        "freq bin",
                        "fr",
                        "power",
                        "n_ph",
                        "Qi_dia_corr",
                        "Qi_dia_corr_err",
                        "absQc",
                        "Ql",
                        "measurement name",
                    ],
                )
            elif circuit_type == "reflection_port":
                self.df_to_csv(
                    self.fit_data,
                    txt_output,
                    columns_to_use=[
                        "freq bin",
                        "fr",
                        "power",
                        "n_ph",
                        "Qi_dia_corr",
                        "absQc",
                        "Ql",
                        "measurement name",
                    ],
                )
        # returns fit data
        return self.fit_data

    # single photon power averager and 'n_ph' appender
    def n_ph_calculator(self):
        # calculate average power for single photon number from fits
        sph_average = self.sph_average_from_data_dict()
        # add 'n_ph' to self.data
        for measurement_name, _ in self.data.items():
            self.data[measurement_name]["fit"]["n_ph"] = (
                10
                ** (
                    ((self.data[measurement_name]["fit"]["power"] - sph_average) - 30)
                    / 10
                )
                * 1e3
            )

    # sort along axes
    def fit_data_to_sorted_dataframe(self, axes_to_sort=["fr", "power"], n_ph_lims=None):
        fit_data_list = []
        first = True
        for _, measurement_data in self.data.items():
            fit_data_list.append(measurement_data["fit"])
            if first:
                columns = measurement_data["fit"].keys()
                first = False
        # convert to DataFrame
        df = pd.DataFrame(fit_data_list, columns=columns)
        # convert only numeric-looking columns to float
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass  # Keep non-convertible columns as-is
        # sort by specified axes
        df_sorted = df.sort_values(by=axes_to_sort, ascending=[True]*len(axes_to_sort)).reset_index(drop=True)
        # apply photon number filtering if needed
        if n_ph_lims is not None:
            assert isinstance(n_ph_lims, list) and len(n_ph_lims) == 2
            if "n_ph" in df_sorted.columns:
                df_sorted = df_sorted[(df_sorted['n_ph'] > n_ph_lims[0]) & (df_sorted['n_ph'] < n_ph_lims[1])]
        # remove rows with NaNs in any column used for sorting or analysis
        df_sorted = df_sorted.dropna(subset=axes_to_sort + (["n_ph"] if n_ph_lims else []))
        # remove invalid rows (e.g., 0 power)
        if "power" in df_sorted.columns:
            df_sorted = df_sorted[df_sorted["power"] != 0]
        self.fit_data = df_sorted
    
    def sort_fit_data(self, axes_to_sort=["fr", "power"], n_ph_lims=None):
        if not isinstance(self.fit_data, pd.DataFrame):
            self.fit_data = pd.DataFrame(self.fit_data)
        df = self.fit_data
        # convert only numeric-looking columns to float
        for col in df.columns:
            if col not in ["freq bin", "measurement name"]:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    #print(f"Converted column '{col}' to numeric type.")
                except Exception:
                    #print(f"Could not convert column '{col}' to numeric type. Keeping it as-is.")
                    pass  # Keep non-convertible columns as-is
        # sort by specified axes
        df_sorted = df.sort_values(by=axes_to_sort, ascending=[True]*len(axes_to_sort)).reset_index(drop=True)
        # apply photon number filtering if needed
        if n_ph_lims is not None:
            assert isinstance(n_ph_lims, list) and len(n_ph_lims) == 2
            if "n_ph" in df_sorted.columns:
                df_sorted = df_sorted[(df_sorted['n_ph'] > n_ph_lims[0]) & (df_sorted['n_ph'] < n_ph_lims[1])]
        # remove rows with NaNs in any column used for sorting or analysis
        df_sorted = df_sorted.dropna(subset=axes_to_sort + (["n_ph"] if n_ph_lims else []))
        # remove invalid rows (e.g., 0 power)
        if "power" in df_sorted.columns:
            df_sorted = df_sorted[df_sorted["power"] != 0]
        self.fit_data = df_sorted

    # get labels for frequency bins
    def get_frequency_bin_labels(self):
        freq_list = np.array(self.fit_data["fr"], dtype=float)
        freq_list_rounded = (freq_list * 1e-9).round(2)
        freq_bins = list(set(freq_list_rounded))
        self.num_resonators = len(freq_bins)
        freq_bins.sort()
        self.freq_bin_labels = [f"{i:.2f} GHz" for i in freq_bins]
        print(f"Detected {len(self.freq_bin_labels)} frequency bins: {self.freq_bin_labels}")
        assert len(self.freq_bin_labels) == self.num_resonators, "Bin labelling failed."
        return self.freq_bin_labels

    # search for frequencies and create bins
    def get_frequency_bins(self):
        # Ensure 'fr' is float
        self.fit_data["fr"] = pd.to_numeric(self.fit_data["fr"], errors='coerce')
        self.get_frequency_bin_labels()
        assert (
            self.num_resonators
        ), "num_resonators not set, so frequency binning is not well-defined."
        bin_labels = self.freq_bin_labels
        self.fit_data["freq bin"] = pd.cut(
            self.fit_data["fr"], bins=self.num_resonators, labels=bin_labels
        )
        # re-sort with freq binning
        self.fit_data = self.fit_data.sort_values(
            by=["freq bin", "power"], ascending=[True, True]
        ).reset_index(drop=True)

    # remove duplicates
    def remove_duplicates(self, duplicate_threshold=1):
        # Identify rows where the difference is below the threshold
        df = self.fit_data
        to_keep = [True]  # Keep the first value
        for i in range(1, len(df)):
            # Compare current value with the previous one
            if (
                abs(abs(df.loc[i, "power"]) - abs(df.loc[i - 1, "power"]))
                <= duplicate_threshold
            ):
                to_keep.append(False)  # Mark as False if it's too close
            else:
                to_keep.append(True)  # Otherwise, keep it
        # df_sorted.drop_duplicates(keep="last", inplace=True)
        df_filtered = df[to_keep]
        false_locations = [i for i, e in enumerate(to_keep) if e == False]
        if self.print_log:
            list_of_removed_duplicates = [
                f'{df.loc[i, "freq bin"]}: {df.loc[i, "power"]} dBm'
                for i in false_locations
            ]
            print(
                f"{to_keep.count(False)} duplicate(s) removed...\n{list_of_removed_duplicates}"
            )
        self.fit_data = df_filtered

    def get_text_summary(
            self, 
            save_directory=None,
            n_ph_HP=1e6,
            do_fit=True,
            output_name=None,
            include_resonators=None
            ):
        '''
        Saves a text file with a complete data summary to the data_path.
        '''

        if include_resonators == None:
            include_resonators = list(range(self.num_resonators))
        
        do_fit = self.do_TLS_fit if self.do_TLS_fit != None else 0

        # double check frequency bins set
        assert self.freq_bin_labels, "Frequency bin labels not set. Run get_frequency_bins() first."

        if save_directory != None:
            save_path = save_directory
        else:
            save_path = self.save_path
        if output_name == None:
            export_path = os.path.join(save_path, f"data_summary_{self.name}.txt")
        else:
            export_path = os.path.join(save_path, f"{output_name}_{self.name}.txt")
        col_width = 13
        headers_per_res = ["Qi,LP", "Qi,HP", "Qc med", "Qc range", "f med [Hz]", "f range [Hz]", "F*tanδ", "n_c"]
        headers_stats = ["Qi,LP \tmax", "Qi,LP \tAv +/- SE", "Qi,HP \tmax", "Qi,HP \tAv +/- SE", "Qc    \tAv +/- SE", "Qc    \tmax", "Qc    \tmin", "F*tanδ  Av +/- SE", "F*tanδ  min"]

        with open(export_path, "w") as file:
            # Format headers with equal spacing
            file.write(f"Q-factor summary: {self.name}\nData: {self.data_path}\n\n")  # Write headers to file
            header_line = "".join(h.ljust(col_width) for h in headers_per_res)
            file.write("Per resonator\n" + header_line + "\n")  # Write headers to file
            file.write("-" * (col_width * len(headers_per_res)) + "\n")  # Add a separator line

        # setup for calculating statistical values
        Qi_LP = []
        Qi_HP = []
        F_tan_delta = []
        n_c = []
        if "Qc_dia_corr" in self.fit_data.columns:
            Qc = np.array(self.fit_data["Qc_dia_corr"])
        elif "absQc" in self.fit_data.columns:
            Qc = np.array(self.fit_data["absQc"])

        counter = 0
        for i, freq_bin_cur in enumerate(self.freq_bin_labels):
            print(f"Gathering data for {freq_bin_cur} resonator...")
            if (include_resonators != None) and (i in include_resonators):
                res_data = self.isolate_resonator_data(freq_bin_cur)
                # print(f"res data\n{pd.DataFrame(res_data)}")

                LP_indx = self.find_photon_number_index(
                    data=res_data, photon_number=1
                )
                Qi_LP.append(np.array(res_data["Qi"])[LP_indx])
                print(f" LP index: {LP_indx:<3}, Qi_LP: {np.array(res_data['Qi'])[LP_indx]}")

                # get high power Qi
                HP_indx = self.find_photon_number_index(
                    data=res_data, photon_number="maximum"
                )

                # adjust HP_indx if it is outside the measured range of n_ph
                if HP_indx > len(np.array(res_data["Qi"])):
                    HP_indx = len(np.array(res_data["Qi"])) - 1
                Qi_HP.append(np.array(res_data["Qi"])[HP_indx])
                print(f" HP index: {HP_indx:<3}, Qi_HP: {np.array(res_data['Qi'])[HP_indx]}")

                # calculate per-resonator values
                f_av = self.filtered_mean_iqr(res_data["f"])
                Qc_av = self.filtered_mean_iqr(res_data["Qc"]) 
                f_range = self.filtered_mean_iqr(res_data["f"], filtered_range=True)
                Qc_range = self.filtered_mean_iqr(res_data["Qc"], filtered_range=True)

                if do_fit:
                    # calculate F*tanδ
                    fit_dict, _, _ = self.TLS_fit(np.array(res_data["n_ph"], dtype=float), 
                                                np.array(res_data["Qi"], dtype=float), 
                                                f=f_av, 
                                                T=self.T, 
                                                # Qerr=res_data["Qerr"], 
                                                bounds=self.TLSfit_bounds, 
                                                n_ph_lims=self.n_ph_lims,
                                                TLS_model=self.TLS_model)
                    F_tan_delta.append(fit_dict["F_tan_delta"])
                    n_c.append(fit_dict["n_c"])
                else:
                    F_tan_delta.append(0)
                    n_c.append(0)

                # print to file
                vals = [Qi_LP[counter], Qi_HP[counter], Qc_av, Qc_range, f_av, f_range, F_tan_delta[counter], n_c[counter]]
                with open(export_path, "a") as file:
                    file.write("".join(f"{float(val):<{col_width}.2e}" for val in vals) + "\n")
                counter += 1

        # calculate statistical values
        Qi_LP_max = np.max(np.array(Qi_LP, dtype=float))
        Qi_LP_av = self.filtered_mean_iqr(np.array(Qi_LP))
        Qi_LP_SE = np.std(np.array(Qi_LP, dtype=float), ddof=1) / np.sqrt(len(Qi_LP))
        Qi_HP_max = np.max(np.array(Qi_HP, dtype=float))
        Qi_HP_av = self.filtered_mean_iqr(np.array(Qi_HP))
        Qi_HP_SE = np.std(np.array(Qi_HP, dtype=float), ddof=1) / np.sqrt(len(Qi_HP))
        Qc_av = self.filtered_mean_iqr(np.array(Qc, dtype=float))
        Qc_SE = self.filtered_mean_iqr(np.array(Qc, dtype=float), filtered_SE=True)
        Qc_max = np.max(np.array(Qc, dtype=float))
        Qc_min = np.min(np.array(Qc, dtype=float))
        if do_fit:
            F_tan_delta_av = self.filtered_mean_iqr(np.array(F_tan_delta))
            F_tan_delta_SE = self.filtered_mean_iqr(np.array(F_tan_delta), filtered_SE=True)
            F_tan_delta_min = np.min(np.array(F_tan_delta, dtype=float))
        else:
            F_tan_delta_av = 0
            F_tan_delta_SE = 0
            F_tan_delta_min = 0

        with open(export_path, "a") as file:
            file.write("\n\nStatistical values across all resonators\n")
            file.write("-" * (col_width * len(headers_per_res)) + "\n")  # Add a separator line
            # add values as strings
            vals = [
                f"{Qi_LP_max:.3e}",
                f"{Qi_LP_av:.3e} +/- {Qi_LP_SE:.3e}\n",
                f"{Qi_HP_max:.3e}",
                f"{Qi_HP_av:.3e} +/- {Qi_HP_SE:.3e}\n",
                f"{Qc_av:.3e} +/- {Qc_SE:.3e}",
                f"{Qc_max:.3e}",
                f"{Qc_min:.3e}\n",
                f"{F_tan_delta_av:.3e} +/- {F_tan_delta_SE:.3e}",
                f"{F_tan_delta_min:.3e}\n"                  
            ]
            assert len(vals) == len(headers_stats)
            for i, val in enumerate(vals):
                file.write(f"{headers_stats[i]:<{2*col_width}}{val}\n")
            file.write(f"\n\nNotes:\n- HP (high power) is roughly {n_ph_HP:.0e} photons\n- LP (low power) is roughly one photon\n- Values outside 1.5*IQR are removed before calculating\n  mean (av), range, standard error (SE)")
        print(f"File printed at {export_path}")
    
    @staticmethod
    def filtered_mean_iqr(data, filtered_range=False, filtered_SE=False):
        data = pd.to_numeric(pd.Series(data), errors='coerce')
        data = data.dropna()                         
        data = np.array(data, dtype=float)  # Convert to NumPy array
        q1, q3 = np.percentile(data, [25, 75])  # First & third quartiles
        iqr = q3 - q1  # Interquartile range
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        filtered_data = data[(data >= lower_bound) & (data <= upper_bound)]  # Keep only in-range values

        if filtered_range == True:
            # Compute range (max - min) from filtered data
            return np.ptp(filtered_data) if filtered_data.size > 0 else np.ptp(data)  # Avoid empty array issues
        elif filtered_SE == True:
            return np.std(filtered_data, ddof=1) / np.sqrt(len(filtered_data)) if filtered_data.size > 0 else np.std(data, ddof=1) / np.sqrt(len(data)) # Avoid empty array issues # Avoid empty array issues
        else:
            return np.mean(filtered_data) if filtered_data.size > 0 else np.mean(data)  # Avoid empty slice


    def isolate_resonator_data(self, freq_bin_label):
        # initialise plot data for new resonator
        n_ph, Qi, Qc, f, Qerr = [], [], [], [], []
        frequency = float(freq_bin_label.split()[0]) * 1e9  # Hz
        if "absQc" in self.fit_data.columns:
            Qc_col = "absQc"
        elif "Qc_dia_corr" in self.fit_data.columns:
            Qc_col = "Qc_dia_corr"
        for _, row in self.fit_data.iterrows():
            # add measurement from self.fit_data if in current bin
            if row["freq bin"] == freq_bin_label:
                n_ph.append(row["n_ph"])
                Qi.append(row["Qi_dia_corr"])
                Qc.append(row[Qc_col])
                f.append(row['fr'])
                Qerr.append(row["Qi_dia_corr_err"])
        # Sort the data by n_ph
        n_ph = np.array(n_ph, dtype=float)
        sorted_data = sorted(zip(n_ph, Qi, Qc, f, Qerr), key=lambda x: x[0])
        n_ph, Qi, Qc, f, Qerr = zip(*sorted_data) if sorted_data else ([], [], [], [], [])
        return dict(n_ph=n_ph, Qi=Qi, Qc=Qc, f=f, Qerr=Qerr)

    # Qi vs photon number
    def plot_Qi_n_ph(
        self,
        with_fit=True,
        with_errorbars=True,
        with_errorband=False,
        legend_location="bottom_right",
        show_plot=True,
        save_plot=True,
        backend=None,
        ylims=None,
        plot_frequencies=None
    ):

        with_fit = self.do_TLS_fit if self.do_TLS_fit != None else 0
        assert self.freq_bin_labels, "Frequency bin labels not set. Run get_frequency_bins() first."
        assert isinstance(self.fit_data, pd.DataFrame)
        if backend == None:
            backend = self.plot_backend
        # check backend is valid
        assert backend in [
            "matplotlib",
            "bokeh",
        ], "Please choose 'matplotlib' or 'bokeh' as the backend"
        if plot_frequencies:
            assert isinstance(plot_frequencies, list), "Please give plot frequencies as a list of indeces corresponding to the resonators you want to plot, i.e. [0, 1, 2]"
        # bokeh setup
        if backend == "bokeh":
            self.fig_bokeh = figure(
                title=f"{self.name}: internal Q-factor",
                width=1000,
                height=600,
                x_axis_type="log",
                y_axis_type="log",
                y_axis_label=r"$$Q_i$$",
                x_axis_label=r"Photon number  ⟨n⟩",
            )
            self._colourmap = Viridis256
            if ylims != None:
                self.fig_bokeh.y_range = Range1d(ylims[0], ylims[1])
        # matplotlib setup
        elif backend == "matplotlib":
            self._colourmap = plt.cm.viridis
            colors = [
                self._colourmap(i / (self.num_resonators - 1))
                for i in range(self.num_resonators)
            ]
            self.ax_ph_mpl.legend(loc="best")
            self.ax_ph_mpl.set_title(f"{self.name}: " + r"$Q_i$")
            self.ax_ph_mpl.set_xlabel(r"Photon number $\langle n \rangle$")
            self.ax_ph_mpl.set_ylabel(r"$Q_i$")
            self.ax_ph_mpl.set_xscale("log")
            self.ax_ph_mpl.set_yscale("log")
            self.ax_ph_mpl.grid(True, which="both", alpha=0.2, lw=1)
            if ylims != None:
                self.ax_ph_mpl.set_ylim(bottom=ylims[0], top=ylims[1])
        # loop through frequency bins
        if plot_frequencies != None:
            freqs_to_use = plot_frequencies
        elif plot_frequencies == None:
            freqs_to_use = range(self.num_resonators)
        for i, freq_bin_cur in enumerate(self.freq_bin_labels):
            if i in freqs_to_use:
                # initialise plot data for new resonator
                n_ph, Qi, Qi_upper, Qi_lower, Qerr = [], [], [], [], []
                f = float(freq_bin_cur.split()[0]) * 1e9  # Hz
                for _, row in self.fit_data.iterrows():
                    # add measurement from self.fit_data if in current bin
                    if row["freq bin"] == freq_bin_cur:
                        n_ph.append(row["n_ph"])
                        Qi.append(row["Qi_dia_corr"])
                        Qi_upper.append(float(row["Qi_dia_corr"]) + float(row["Qi_dia_corr_err"]))
                        Qi_lower.append(float(row["Qi_dia_corr"]) - float(row["Qi_dia_corr_err"]))
                        Qerr.append(row["Qi_dia_corr_err"])
                # convert to ColumnDataSource for Bokeh plotting
                source = ColumnDataSource(
                    data=dict(n_ph=n_ph, Qi=Qi, upper=Qi_upper, lower=Qi_lower, Qerr=Qerr)
                )
                # get single photon Qi
                sph_indx = self.find_photon_number_index(
                    data=source.data, photon_number=1
                )
                sph_Qi = np.array(source.data["Qi"])[sph_indx]

                # TLS fit
                n_ph_TLS, TLSfit = None, None
                if with_fit == True:
                    _, n_ph_TLS, TLSfit = self.TLS_fit(
                        n_ph=source.data["n_ph"],
                        Qi=source.data["Qi"],
                        f=f,
                        T=self.T,
                        Qerr=source.data["Qerr"],
                        bounds=self.TLSfit_bounds,
                        n_ph_lims=self.n_ph_lims,
                        TLS_model=self.TLS_model
                    )

                # bokeh plot
                if backend == "bokeh":
                    color = self._colourmap[i * len(self._colourmap) // self.num_resonators]
                    # do plotting
                    self.fig_bokeh.scatter(
                        source=source,
                        x="n_ph",
                        y="Qi",
                        size=10,
                        color=color,
                        alpha=0.7,
                        legend_label=f"{freq_bin_cur} (Single photon Qi = {sph_Qi:.1e})",
                    )
                    # errorband
                    if with_errorband == True:
                        band2 = Band(
                            base="n_ph",
                            upper="upper",
                            lower="lower",
                            source=source,
                            level="underlay",
                            fill_color=color,
                            line_alpha=0.2,
                            fill_alpha=0.1,
                            line_width=1,
                            line_color=color,
                        )
                        self.fig_bokeh.add_layout(band2)
                    # errorbars
                    if with_errorbars == True:
                        errorbars = Whisker(
                            base="n_ph",
                            upper="upper",
                            lower="lower",
                            source=source,
                            line_color=color,
                            line_alpha=0.7,
                            line_cap="round",
                            line_width="2",
                            upper_head=TeeHead(line_color=color, line_alpha=0.7, size=6),
                            lower_head=TeeHead(line_color=color, line_alpha=0.7, size=6),
                        )
                        self.fig_bokeh.add_layout(errorbars)
                    if with_fit == True:
                        self.fig_bokeh.line(
                            n_ph_TLS, TLSfit, line_color=color, line_alpha=0.2, line_width=3
                        )

                # matplotlib plot
                if backend == "matplotlib":
                    # errorbars
                    if with_errorbars == True:
                        self.ax_ph_mpl.errorbar(
                            x=source.data["n_ph"],
                            y=source.data["Qi"],
                            yerr=source.data["Qerr"],
                            fmt="o",
                            color=color,
                            alpha=1,
                            linewidth=2,
                            label=f"{freq_bin_cur} (Single photon Qi = {sph_Qi:.1e})",
                        )
                    else:
                        self.ax_ph_mpl.scatter(
                            x=source.data["n_ph"],
                            y=source.data["Qi"],
                            size=10,
                            color=color,
                            alpha=1,
                            label=f"{freq_bin_cur} (Single photon Qi = {sph_Qi:.1e})",
                        )
                    # TLS fit
                    n_ph_TLS, TLSfit = None, None
                    if with_fit == True:
                        _, n_ph_TLS, TLSfit = self.TLS_fit(
                            n_ph=source.data["n_ph"],
                            Qi=source.data["Qi"],
                            f=f,
                            T=self.T,
                            Qerr=source.data["Qerr"],
                            bounds=self.TLSfit_bounds,
                            n_ph_lims=self.n_ph_lims,
                            TLS_model=self.TLS_model
                        )
                        self.ax_ph_mpl.plot(
                            n_ph_TLS, TLSfit, color=color, alpha=0.4, linewidth=3
                    )

        if backend == "bokeh":
            # legend
            self.fig_bokeh.legend.location = legend_location
            # title
            self.fig_bokeh.title = f"{self.name}: Internal Q-factor"
            # show plot
            if show_plot == True:
                show(self.fig_bokeh)
            # save plot
            if save_plot == True:
                export_path = os.path.join(self.save_path, f"{self.name}_Qi_bokeh.png")
                export.export_png(obj=self.fig_bokeh, filename=export_path)
                print(f"Plot saved at {export_path}")
        if backend == "matplotlib":
            # legend
            self.ax_ph_mpl.legend(loc="best")
            # title
            self.ax_ph_mpl.set_title(self.name)
            # plot settings
            self.ax_ph_mpl.set_xlabel(r"Photon number $\langle n \rangle$")
            self.ax_ph_mpl.set_ylabel(r"$Q_i$")
            self.ax_ph_mpl.loglog()
            self.ax_ph_mpl.grid(True, which="both", alpha=0.2, lw=1)
            # show plot
            if show_plot == True:
                plt.show()
            # save plot
            if save_plot == True:
                export_path = os.path.join(self.save_path, f"{self.name}_Qi_mpl.png")
                self.fig_mpl.savefig(export_path)
                print(f"Plot saved at {export_path}")

    def plot_fr_n_ph(
        self,
        backend=None,
        with_errorbars=True,
        show_plot=True,
        save_plot=True,
        as_deviation=True,
        plot_frequencies=None
    ):
        if self._data_from_text_file == True:
            print(
                "Data loaded from text file, so frequency data is not available. "
                "Please read data from .h5 files to plot frequency."
            )
            return
        # auto set with_errorbars = False if fr_err doesnt exist
        if "fr_err" not in self.fit_data.columns:
            with_errorbars = False
            print("No frequency error data found, setting with_errorbars to False.")
        if backend == None:
            backend = self.plot_backend
        # check backend is valid
        assert backend in [
            "matplotlib",
            "bokeh",
        ], "Please choose 'matplotlib' or 'bokeh' as the backend"
        if plot_frequencies != None:
            freqs_to_use = plot_frequencies
        elif plot_frequencies == None:
            freqs_to_use = range(self.num_resonators)
        df_rev = self.fit_data[::-1]
        # bokeh
        if backend == "bokeh":
            self.fig_bokeh = figure(
                title=f"{self.name}: Frequency",
                x_axis_type="log",
                x_axis_label="Photon number " + "⟨n⟩",
                width=1000,
                height=600,
            )
            if as_deviation == True:
                self.fig_bokeh.yaxis.axis_label = r"Frequency deviation (Hz)"
            else:
                self.fig_bokeh.yaxis.axis_label = r"Frequency (Hz)"
            self._colourmap = Viridis256
            # loop through frequency bins
            for i, freq_bin_cur in enumerate(self.freq_bin_labels):
                if i in freqs_to_use:
                    # initialise plot data for new resonator
                    n_ph, fr, fr_upper, fr_lower, fr_err = [], [], [], [], []
                    f = float(freq_bin_cur.split()[0]) * 1e9  # Hz
                    first_of_freq = True
                    for _, row in df_rev.iterrows():
                        # add measurement from self.fit_data if in current bin
                        if row["freq bin"] == freq_bin_cur:
                            if (first_of_freq == True) and (as_deviation == True):
                                fr_comp = row["fr"]
                                first_of_freq = False
                            if as_deviation == True:
                                fr.append(row["fr"] - fr_comp)
                                fr_upper.append(row["fr"] - fr_comp + row["fr_err"])
                                fr_lower.append(row["fr"] - fr_comp - row["fr_err"])
                            else:
                                fr.append(row["fr"])
                                fr_upper.append(row["fr"] + row["fr_err"])
                                fr_lower.append(row["fr"] - row["fr_err"])
                            n_ph.append(row["n_ph"])
                            fr_err.append(row["fr_err"])
                    # convert to ColumnDataSource for Bokeh plotting
                    source = ColumnDataSource(
                        data=dict(
                            n_ph=n_ph, fr=fr, upper=fr_upper, lower=fr_lower, fr_err=fr_err
                        )
                    )
                    # do plotting
                    color = self._colourmap[i * len(self._colourmap) // self.num_resonators]
                    self.fig_bokeh.scatter(
                        source=source,
                        x="n_ph",
                        y="fr",
                        size=10,
                        color=color,
                        alpha=0.7,
                        legend_label=f"{freq_bin_cur}",
                    )
                    # errorbars
                    if with_errorbars == True:
                        errorbars = Whisker(
                            base="n_ph",
                            upper="upper",
                            lower="lower",
                            source=source,
                            line_color=color,
                            line_alpha=0.7,
                            line_cap="round",
                            line_width="2",
                            upper_head=TeeHead(line_color=color, line_alpha=0.7, size=6),
                            lower_head=TeeHead(line_color=color, line_alpha=0.7, size=6),
                        )
                        self.fig_bokeh.add_layout(errorbars)
            # legend
            # p.legend.location = legend_location
            # show plot
            if show_plot == True:
                show(self.fig_bokeh)
            # save plot
            if save_plot == True:
                export_path = os.path.join(self.save_path, f"{self.name}_fr_bokeh.png")
                export.export_png(obj=self.fig_bokeh, filename=export_path)
                print(f"Plot saved at {export_path}")
        # matplotlib
        elif backend == "matplotlib":
            self._colourmap = plt.cm.viridis
            colors = [
                self._colourmap(i / (self.num_resonators - 1))
                for i in range(self.num_resonators)
            ]
            # loop through frequency bins
            for i, freq_bin_cur in enumerate(self.freq_bin_labels):
                if i in freqs_to_use:
                    # initialise plot data for new resonator
                    n_ph, fr, fr_err = [], [], []
                    f = float(freq_bin_cur.split()[0]) * 1e9  # Hz
                    first_of_freq = True
                    for _, row in df_rev.iterrows():
                        # add measurement from self.fit_data if in current bin
                        if row["freq bin"] == freq_bin_cur:
                            if (first_of_freq == True) and (as_deviation == True):
                                fr_comp = row["fr"]
                                first_of_freq = False
                            if as_deviation == True:
                                fr.append(row["fr"] - fr_comp)
                            else:
                                fr.append(row["fr"])
                            n_ph.append(row["n_ph"])
                            fr_err.append(row["fr_err"])
                    # colour
                    color = colors[i]
                    # convert to dict
                    source = {"n_ph": n_ph, "fr": fr, "fr_err": fr_err}
                    # errorbars
                    if with_errorbars == True:
                        self.ax_ph_mpl.errorbar(
                            x=source["n_ph"],
                            y=source["fr"],
                            yerr=source["fr_err"],
                            fmt="o",
                            color=color,
                            alpha=1,
                            linewidth=2,
                            label=f"{freq_bin_cur}",
                        )
                    else:
                        self.ax_ph_mpl.scatter(
                            x=source["n_ph"],
                            y=source["fr"],
                            size=10,
                            color=color,
                            alpha=1,
                            label=f"{freq_bin_cur}",
                        )
            # legend
            self.ax_ph_mpl.legend(loc="best")
            # title
            self.ax_ph_mpl.set_title(f"{self.name}: Frequency")
            # plot settings
            self.ax_ph_mpl.set_xlabel(r"Photon number $\langle n \rangle$")
            if as_deviation == True:
                self.ax_ph_mpl.set_ylabel(r"Frequency deviation (Hz)")
            else:
                self.ax_ph_mpl.set_ylabel(r"Frequency (Hz)")
            self.ax_ph_mpl.set_xscale("log")
            self.ax_ph_mpl.grid(True, which="both", alpha=0.2, lw=1)
            # show plot
            if show_plot == True:
                plt.show()
            # save plot
            if save_plot == True:
                export_path = os.path.join(self.save_path, f"{self.name}_fr_mpl.png")
                self.fig_mpl.savefig(export_path)
                print(f"Plot saved at {export_path}")

    def plot_Qc_n_ph(
        self,
        backend=None,
        with_errorbars=True,
        show_plot=True,
        save_plot=True,
        ylims=None,
        plot_frequencies=None
    ):
        # overrun with_errorbars if absQc doesnt exist
        if self._data_from_text_file == True:
            with_errorbars = False

        if backend == None:
            backend = self.plot_backend
        # check backend is valid
        assert backend in [
            "matplotlib",
            "bokeh",
        ], "Please choose 'matplotlib' or 'bokeh' as the backend"
        if ylims:
            assert isinstance(ylims, (list, tuple)), "Set ylims=[min, max] or None."
        if plot_frequencies != None:
            freqs_to_use = plot_frequencies
        elif plot_frequencies == None:
            freqs_to_use = range(self.num_resonators)
        # check column naming conventions
        if "Qc_dia_corr" in self.fit_data.columns:
            self.fit_data = self.fit_data.rename(columns={"Qc_dia_corr": "absQc"})
        # bokeh setup
        if backend == "bokeh":
            self.fig_bokeh = figure(
                title=f"{self.name}: external Q-factor",
                width=1000,
                height=600,
                x_axis_type="log",
                y_axis_type="log",
                y_axis_label=r"$$Q_c$$",
                x_axis_label=r"Photon number  ⟨n⟩",
            )
            self._colourmap = Viridis256
            if ylims != None:
                self.fig_bokeh.y_range = Range1d(ylims[0], ylims[1])
        # matplotlib setup
        elif backend == "matplotlib":
            self._colourmap = plt.cm.viridis
            colors = [
                self._colourmap(i / (self.num_resonators - 1))
                for i in range(self.num_resonators)
            ]
            self.ax_ph_mpl.legend(loc="best")
            self.ax_ph_mpl.set_title(f"{self.name}: " + r"$Q_c$")
            self.ax_ph_mpl.set_xlabel(r"Photon number $\langle n \rangle$")
            self.ax_ph_mpl.set_ylabel(r"$Q_c$")
            self.ax_ph_mpl.set_xscale("log")
            self.ax_ph_mpl.set_yscale("log")
            self.ax_ph_mpl.grid(True, which="both", alpha=0.2, lw=1)
            if ylims != None:
                self.ax_ph_mpl.set_ylim(bottom=ylims[0], top=ylims[1])
        # loop through frequency bins
        for i, freq_bin_cur in enumerate(self.freq_bin_labels):
            if i in freqs_to_use:
                # initialise plot data for new resonator
                n_ph, Qc, Qc_upper, Qc_lower, Qc_err = [], [], [], [], []
                f = float(freq_bin_cur.split()[0]) * 1e9  # Hz
                for _, row in self.fit_data.iterrows():
                    # add measurement from self.fit_data if in current bin
                    if row["freq bin"] == freq_bin_cur:
                        Qc.append(row["absQc"])
                        n_ph.append(row["n_ph"])
                        if with_errorbars:
                            Qc_upper.append(row["absQc"] + row["absQc_err"])
                            Qc_lower.append(row["absQc"] - row["absQc_err"])
                            Qc_err.append(row["absQc_err"])

                # convert to ColumnDataSource for Bokeh plotting
                if with_errorbars == True:
                    source = ColumnDataSource(
                        data=dict(
                            n_ph=n_ph, Qc=Qc, upper=Qc_upper, lower=Qc_lower, Qc_err=Qc_err
                        )
                    )
                else:
                    source = ColumnDataSource(
                        data=dict(
                            n_ph=n_ph, Qc=Qc
                        )
                    )
                # bokeh
                if backend == "bokeh":
                    color = self._colourmap[i * len(self._colourmap) // self.num_resonators]
                    self.fig_bokeh.scatter(
                        source=source,
                        x="n_ph",
                        y="Qc",
                        size=10,
                        color=color,
                        alpha=0.7,
                        legend_label=f"{freq_bin_cur}",
                    )
                    # errorbars
                    if with_errorbars == True:
                        errorbars = Whisker(
                            base="n_ph",
                            upper="upper",
                            lower="lower",
                            source=source,
                            line_color=color,
                            line_alpha=0.7,
                            line_cap="round",
                            line_width="2",
                            upper_head=TeeHead(line_color=color, line_alpha=0.7, size=6),
                            lower_head=TeeHead(line_color=color, line_alpha=0.7, size=6),
                        )
                        self.fig_bokeh.add_layout(errorbars)
                # matplotlib
                elif backend == "matplotlib":
                    # colour
                    color = colors[i]
                    # errorbars
                    if with_errorbars == True:
                        self.ax_ph_mpl.errorbar(
                            x=source.data["n_ph"],
                            y=source.data["Qc"],
                            yerr=source.data["Qc_err"],
                            fmt="o",
                            color=color,
                            alpha=1,
                            linewidth=2,
                            label=f"{freq_bin_cur}",
                        )
                    else:
                        self.ax_ph_mpl.scatter(
                            x=source.data["n_ph"],
                            y=source.data["Qc"],
                            size=10,
                            color=color,
                            alpha=1,
                            label=f"{freq_bin_cur}",
                        )
        if backend == "bokeh":
            # show plot
            if show_plot == True:
                show(self.fig_bokeh)
            # save plot
            if save_plot == True:
                export_path = os.path.join(self.save_path, f"{self.name}_Qc_bokeh.png")
                export.export_png(obj=self.fig_bokeh, filename=export_path)
                print(f"Plot saved at {export_path}")
        if backend == "matplotlib":
            if show_plot == True:
                plt.show()
            # save plot
            if save_plot == True:
                export_path = os.path.join(self.save_path, f"{self.name}_Qc_mpl.png")
                self.fig_mpl.savefig(export_path)
                print(f"Plot saved at {export_path}")

    # TLS fit
    @staticmethod
    def TLS_fit(
        n_ph, Qi, f, T, bounds=None, Qerr=None, print_log=False, print_fit=True, n_ph_lims=None, TLS_model="mcrae"
    ):
        """
        Function for fitting TLS loss model (e.g. in doi: 10.1063/5.0004622) to n_ph vs. Qi. Note: this is a static method (i.e. does not have access to class variables; all arguments must be passed). Fits parameters [F_delta_TLS0, n_c, Q_HP, beta].

        Inputs:
        - n_ph      List-like of n_ph (x) data.
        - Qi        List-like of Qi (y) data.
        - f         Frequency of resonator in Hz.
        - T         Temperature of sample during measurement in K.
        - bounds    (Optional) Bounds for fitting parameters
                    [F_delta_TLS0, n_c, Q_HP, beta]. Tuple of lists,
                    defaults to ([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1])
        - Qerr      (Optional) List-like of Qerr (y error) data.
        - print_log (Defaults to False) Boolean to activate printouts during fitting.
        - print_fit (Defaults to True) Prints fit parameters for each fit
        - n_ph_lims Photon number range to be used for fitting 

        Outputs:
        - Tuple containing (x, y, z)
            - x: dict of fit parameters {"F_tan_delta", "n_c", "Q_HP", "beta"}
            - y: n_ph (array)
            - z: the TLS fit as a function of n_ph (array)
        """

        assert isinstance(T, (float, int)), "Temperature should be a float or int."
        assert T > 0, "Temperature should be greater than 0 K."
        assert isinstance(f, (float, int)), "Frequency should be a float or int."
        assert len([n_ph, Qi, Qerr]) > 0, "Please provide n_ph and Qi data."
        assert TLS_model in ["mcrae", "crowley"], "Please choose TLS model from ['mcrae', 'crowley']"

        # convert to array of floats (if not already)
        n_ph = np.array(n_ph, dtype=float)
        Qi = np.array(Qi, dtype=float)
        assert isinstance(n_ph[0], float)

        # sort Qi, n_ph by n_ph
        sorted_indices = np.argsort(n_ph)
        n_ph = n_ph[sorted_indices]
        Qi = Qi[sorted_indices]
        assert all(n_ph[i] <= n_ph[i + 1] for i in range(len(n_ph) - 1)), "Data is not sorted by photon number."

        # filter n_ph lims
        if n_ph_lims is not None:
            mask = (n_ph > n_ph_lims[0]) & (n_ph < n_ph_lims[1])
            n_ph = n_ph[mask]
            Qi = Qi[mask]
            print(f"Photon range limited to {n_ph[0]} < n_ph < {n_ph[-1]} for fitting.")

        # constants
        hbar = 1.054 * 10 ** (-34)
        kB = 1.380649 * 10 ** (-23)

        if TLS_model == "mcrae":
            """
            4 fit parameters, power-dependence only. 
            From doi: 10.1063/5.0004622 (Mcrae et al. 2020).
            Parameters: F_delta_TLS0, n_c, Q_HP, beta
            """
            numerator = np.tanh((hbar * 2.0 * np.pi * f) / (2 * kB * T))
            # define model
            def TLS_model(n_ph, F_delta_TLS0, n_c, Q_HP, beta):
                denominator = (1.0 + (n_ph / n_c)) ** beta
                delta_TLS = F_delta_TLS0 * (numerator / denominator) + (1 / Q_HP)
                return delta_TLS ** (-1)

            # initial guesses
            init_guesses = [2.0e-6, 1, 1.0e6, 0.5]
            # default bounds
            if bounds == None:
                bounds = ([1e-10, 1e-10, 10, 1e-10], [1, 1e6, 1e10, 1])
            else:
                assert isinstance(
                    bounds, tuple
                ), "Bounds should be passed as a tuple of lists, with elements corresponding to [F_delta_TLS0, n_c, Q_HP, beta]. The first tuple entry is lower bounds, and the second is upper. e.g. bounds = ([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1])"
                assert (
                    len(bounds[0]) == 4
                ), "Bounds should be passed as a tuple of lists, with elements corresponding to [F_delta_TLS0, n_c, Q_HP, beta]. The first tuple entry is lower bounds, and the second is upper. e.g. bounds = ([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1])"
            # DO FIT
            # with error bars
            if Qerr is not None and np.any(Qerr):
                try:
                    popt, pcov, infodict, mesg, ier = scipy.optimize.curve_fit(
                        TLS_model,
                        xdata=np.array(n_ph),
                        ydata=np.array(Qi),
                        p0=init_guesses,
                        sigma=np.array(Qerr),
                        bounds=bounds,
                        full_output=True,
                    )
                except:
                    popt = [0, 0, 0, 0]
            # without error bars
            else:
                try:
                    popt, pcov, infodict, mesg, ier = scipy.optimize.curve_fit(
                        TLS_model,
                        xdata=np.array(n_ph),
                        ydata=np.array(Qi),
                        p0=init_guesses,
                        bounds=bounds,
                        full_output=True,
                    )
                except:
                    popt = [0, 0, 0, 0]
            # print info
            if print_log == True:
                print(f"TLS fit for resonator at {f*1e-9:.2f} GHz")
                pprint(infodict)
                print(f"TLS fit 'mesg' --> {mesg}\n")

            if print_fit == True:
                print(f"TLS fit ({f*1e-9:.2f} GHz)")
                print(f" F delta_TLS = {popt[0]:.2e}")
                print(f" n_c         = {popt[1]:.2f}")
                print(f" Q_HP        = {popt[2]:.2e}")
                print(f" beta        = {popt[3]:.2f}\n")
            
            fit_dict = {
                "F_tan_delta": popt[0],
                "n_c": popt[1],
                "Q_HP": popt[2],
                "beta": popt[3],
            }

        elif TLS_model == "crowley":
            """
            7 fit parameters, power-dependence only here, but includes temp dependence. 
            From http://arxiv.org/abs/2301.07848 (from Crowley et al. 2023).
            Parameters: t_c, Q_TLS0, Q_QP0, Q_other, D, beta1, beta2
            """
            omega = 2 * np.pi * f
            # define model
            def TLS_model(n_ph, t_c, Q_TLS0, Q_QP0, Q_other, D, beta1, beta2):
                if isinstance(T, (list)):
                    assert T.any() > 0, f"Temperature {T} is negative. Check your data."
                else:
                    assert T > 0, f"Temperature {T} is negative. Check your data."
                # superconducting gap
                delta_0 = 1.764 * kB * t_c
                # QP term (T)
                k0 = kn(0, (hbar * omega)/(2 * kB * T))
                sinh = np.sinh((hbar * omega)/(2 * kB * T))
                #numerator = np.exp(delta_0/(kB * T))
                Q_QP = Q_QP0 * (np.exp(delta_0/(kB * T)) / (sinh * k0))
                # TLS term (n, T)
                tanh = np.tanh((hbar * omega)/(2 * kB * T))
                numerator = np.sqrt(1 + ((n_ph**beta2)/(D * T**beta1)) * np.tanh((hbar * omega)/(2 * kB * T)))
                Q_TLS = Q_TLS0 * (numerator/tanh)
                # check validity of fitted Q values
                assert Q_QP.any() > 0, f"Fitted Q_QP={Q_QP} is negative. Check your data."
                assert Q_TLS.any() > 0, f"Fitted Q_TLS={Q_TLS} is negative. Check your data."
                assert Q_other.any() > 0, f"Fitted Q_other={Q_other} is negative. Check your data."
                # combining all
                Q_i = ((1/Q_TLS) + (1/Q_QP) + (1/Q_other))**(-1)
                # return
                return Q_i
            # init guesses
            init_guesses = [1, 1e5, 1e5, 1e6, 1, 0.8, 0.5]
            # default bounds
            if bounds == None:
                bounds = ([0.1, 1e-3, 1e-3, 1e1, 1e-5, 0.01, 0.01], [10, 1e10, 1e10, 1e10, 1e6, 2, 2])
            else:
                assert isinstance(
                    bounds, tuple
                ), "Bounds should be passed as a tuple of lists, with elements corresponding to [t_c, Q_TLS0, Q_QP0, Q_other, D, beta1, beta2]. The first tuple entry is lower bounds, and the second is upper."
                assert (
                    len(bounds[0]) == 7
                ), "Bounds should be passed as a tuple of lists, with elements corresponding to [t_c, Q_TLS0, Q_QP0, Q_other, D, beta1, beta2]. The first tuple entry is lower bounds, and the second is upper."
            # with error bars
            if Qerr:
                try:
                    popt, pcov, infodict, mesg, ier = curve_fit(
                        TLS_model,
                        xdata=np.array(n_ph),
                        ydata=np.array(Qi),
                        p0=init_guesses,
                        sigma=np.array(Qerr),
                        bounds=bounds,
                        full_output=True,
                    )
                except: 
                    popt = [0, 0, 0, 0, 0, 0, 0]
            # without error bars
            else:
                try:
                    popt, pcov, infodict, mesg, ier = curve_fit(
                        TLS_model,
                        xdata=np.array(T),
                        ydata=np.array(Qi),
                        p0=init_guesses,
                        bounds=bounds,
                        full_output=True,
                    )
                except: 
                    popt = [0, 0, 0, 0, 0, 0, 0]
            # print info: t_c, Q_TLS0, Q_QP0, Q_other, D, beta1, beta2
            print(f"TLS fit (f = {f*1e-9:.2f} GHz)")
            print(f" Tc       = {popt[0]:.2f}")
            print(f" Q_TLS0   = {popt[1]:.2e}")
            print(f" Q_QP0    = {popt[2]:.2e}")
            print(f" Q_other  = {popt[3]:.2e}")
            print(f" D        = {popt[4]:.2e}")
            print(f" beta1    = {popt[5]:.2f}")
            print(f" beta2    = {popt[6]:.2f}")
            fit_dict = {
                "t_c": popt[0],
                "Q_TLS0": popt[1],
                "Q_QP0": popt[2],
                "Q_other": popt[3],
                "D": popt[4],
                "beta1": popt[5],
                "beta2": popt[6]
            }

        # check guesses are valid (if not, move within bounds)
        for i, init in enumerate(init_guesses):
            if init < bounds[0][i]:
                init_guesses[i] = bounds[0][i] + 1e-8
            elif init > bounds[1][i]:
                init_guesses[i] = bounds[1][i] - 1e-8

        # return (x, y) tuple of fit data
        return (fit_dict, n_ph, TLS_model(np.array(n_ph, dtype=np.float64), *popt))

    # Function to generate a unique file name by incrementing if file exists
    def get_unique_filename(self, directory=None, base_filename="fitted_data"):
        """
        Unique filename (from base_filename) generator. Checks the save_path for existing files with similar names to the base_filename. If duplicates exist, returns a filename appended with a new integer.

        Inputs:
        - base_filename     Filename to search for. "fitted data" by default.
        """
        if directory == None:
            directory = self.save_path
        file_name, file_extension = os.path.splitext(base_filename)
        counter = 1
        # Increment the filename until a non-existing file is found
        while os.path.exists(os.path.join(directory, base_filename)):
            unique_filename = f"{file_name}_{counter}{file_extension}"
            counter += 1
        return unique_filename

    # extract values from location in dict self.data
    def sph_average_from_data_dict(self):
        """
        Recursively extracts values for a specific key from a nested dictionary.
        """
        values = []
        for measurement, data in self.data.items():
            assert data["fit"]["single photon power"]
            v = data["fit"]["single photon power"]
            values.append(v)
        average = sum(values) / len(values) if values else 0
        if self.print_log == True:
            print(f"\nAverage single photon power = {average:.1f} dBm\n")
        return average

    @staticmethod
    def round_to(x, base):
        return base * round(x / base)

    # Function to assert the presence of subkeys
    @staticmethod
    def assert_subkey_exists(data: dict, required_subkey: str):
        for key, sub_dict in data.items():
            assert isinstance(
                sub_dict, dict
            ), f"Value under '{key}' is not a dictionary."
            assert (
                required_subkey in sub_dict
            ), f"'{required_subkey}' is missing in '{key}'"

    @staticmethod
    def find_photon_number_index(data: dict, photon_number=1):
        assert "n_ph" in data and "Qi" in data, "Data must contain keys 'n_ph' and 'Qi'."

        photon_number_array = np.array(data["n_ph"], dtype=float)
        Qi_array = np.array(data["Qi"], dtype=float)

        if isinstance(photon_number, (float, int)):
            # Find indices of photon numbers greater than the given value
            candidates = [(i, val) for i, val in enumerate(photon_number_array) if val > photon_number]
            if not candidates:
                raise ValueError(f"No photon numbers greater than {photon_number} found.")
            # Choose the closest one above threshold
            index, value = min(candidates, key=lambda x: abs(x[1] - photon_number))
        elif photon_number == "maximum":
            # Index of photon number with the **maximum Qi**
            index = np.argmax(Qi_array)
        elif photon_number == "minimum":
            # Index of photon number with the **minimum Qi**
            index = np.argmin(Qi_array)
        else:
            raise ValueError(f"Invalid photon_number argument: {photon_number}")
        return index

    @staticmethod
    def df_to_csv(df: pd.DataFrame, output_path: str, columns_to_use=[]):
        if columns_to_use == []:
            df.to_csv(output_path, sep="\t", index=False, float_format="%.2e")
        else:
            df[columns_to_use].to_csv(
                output_path, sep="\t", index=False, float_format="%.2e"
            )
        print(f"Fit data written to {output_path}")

    @staticmethod
    def single_circlefit(freq_data, i_vals, q_vals, power_dBm, expected_qi_lims=(0, 1e8)):
        """
        Method for a single circlefit. Returns fit results as a dictionary.
        """
        # setup circlefit
        port = circuit.notch_port()
        port.add_data(
            freq_data,
            i_vals + 1j * q_vals,
        )
        try:
            port.autofit()
        except:
            print(f"Fitting failed.")
            return 0
        else:
            # write fit results to data dictionary
            if (
                expected_qi_lims[0]
                < port.fitresults["Qi_dia_corr"]
                < expected_qi_lims[1]
            ):
                Qi = port.fitresults['Qi_dia_corr']
                Qi_err = port.fitresults['Qi_dia_corr_err']
                n_ph = port.get_photons_in_resonator(power_dBm, unit='dBm', diacorr=True)
                Qc = port.fitresults['absQc']
                # write fit results to plot and save
                port.plotall(save_path="circlefit.pdf", 
                             text=f"$Q_i=${Qi:.1e} $\\pm$ {Qi_err:.1e}, $\\langle n \\rangle ={n_ph:.1e}$")
                return port.fitresults
            else:
                print(f"Fitted Qi value outside of range (Qi, fitted: {port.fitresults['Qi_dia_corr_err']}).")
        
    @classmethod
    def multisample_plot(
        cls,
        main_data_directory,
        sample_options,
        output_directory=None,
        include_bar_graph=True,
        from_text_file=True,
        legend_location="top_right",
        qi_lims=None,
        name_prefix=None
    ):
        """
        Creates a bokeh plot for Qi comparison of multiple resonator samples. 

        Inputs:
        - main_data_directory       The directory in which to search for the data (string).
        - sample_options            A dictionary containing information pertaining to each sample.
                                    Example:
                                    sample_options = {
                                        'IQM-03-01' : {
                                            'resonator_index_to_plot' : [1, 2, 3, 4, 5],
                                            'name' : "IQM-03-01",
                                            'files_to_ignore' : None,
                                            'power_dict' : default_power_dict,
                                            'from_text_file' : "path/to/file/circlefit.txt",
                                            'with_fit' : True,
                                            'qi_lims' : [1e4, 1e8]
                                            },
                                        }
            Sample options:
            - output_directory          The directory in which to save the plot (string).
            - include_bar_graph         Boolean to include a bar graph of the Qi values, or "only" to plot only the bar graph.
            - from_text_file            Boolean or string to indicate whether to import data from a text file. 
                                        If True, uses the default text file name. If a string, uses that as the file name.
                                        If False, imports data from the directory specified in sample_options.
            - additional_attenuation    Optional additional attenuation to apply to the data (in dB).
            - qi_lims                   Qi limits for data import
    
        This function handles import and fitting, before passing the data to
        cls.plot_Qi_multisample_bokeh().
        """
        # default values
        default_power_dict = {"lowPower" : -132, 
                              "highPower" : -82,
                              "default" : -82
                            }
        default_T = 25*1e-3
        assert os.path.isdir(main_data_directory), f"Main data directory '{main_data_directory}' does not exist."
        if output_directory is None:
            output_directory = main_data_directory
        else:
            assert os.path.isdir(output_directory), f"Selected output directory '{output_directory}' does not exist."

        # check for valid options, complete setup
        for sample in sample_options.keys():
            assert sample_options[sample].get('name') != None
            if sample_options[sample].get('power_dict') == None:
                sample_options[sample]['power_dict'] = default_power_dict
            if sample_options[sample].get('T') == None:
                sample_options[sample]['T'] = default_T
        # initialise multi-sample dataset
        print(f'Multi-sample plot: {list(sample_options.keys())}\n')
        data = {key: {} for key in sample_options.keys()}
        for sample in sample_options.keys():

            # setup sample options
            sample_path = os.path.join(main_data_directory, sample)
            from_text = sample_options[sample].get('from_text_file', False)
            additional_attenuation = sample_options[sample].get('additional_attenuation', 0)
            qi_lims = sample_options[sample].get('qi_lims', (1e4, 1e8))
            if from_text == False:
                assert os.path.isdir(sample_path), f"Sample directory '{sample_path}' does not exist."
            print(f"{sample}\n Acquiring data...")
            # create class instance
            chunk = ResonatorPowerSweep(data_path = sample_path,
                        sample_name = sample,
                        temperature = 26e-3,
                        power_dict= sample_options[sample]['power_dict'],
                        TLSfit_bounds=([0, 10, 0, 0.0], [1, 1e3, 1e9, 1]),
                        print_log=False,
                        qi_lims=qi_lims
                        )

            # import from text file if specified
            if isinstance(from_text, str) or from_text == True:
                chunk.import_data(additional_attenuation=additional_attenuation, 
                    files_to_ignore=sample_options[sample]['files_to_ignore'],
                    from_text_file=from_text
                    )
                chunk.do_circlefit(remove_duplicates=True, save_fit=False)
            # otherwise, import from directory
            else:
                # do import and fitting etc. get a dict back
                chunk.import_data(additional_attenuation=additional_attenuation, 
                                files_to_ignore=sample_options[sample]['files_to_ignore'],
                                from_text_file=False
                                )
                chunk.do_circlefit(remove_duplicates=True, save_fit=False)
            
            # sort dictionary
            chunk.sort_fit_data(axes_to_sort=["fr", "power"])

            # assign dict
            data[sample] = pd.DataFrame(chunk.fit_data)   
            sample_options[sample]['freq_bin_labels'] = chunk.freq_bin_labels
            print("\n")

        # pass multi-sample data to plotting function
        cls.plot_Qi_multisample_bokeh(data=data, 
                                      sample_options=dict(sample_options), 
                                      output_data_directory=output_directory,
                                      include_bar_graph=include_bar_graph,
                                      ylims=qi_lims,
                                      legend_location=legend_location,
                                      name_prefix=name_prefix,
                                      )
        print(f"Data passed to plot_Qi_multisample_bokeh()")

    @classmethod
    # Qi vs photon number (static) and bar-graph with sample statistics
    def plot_Qi_multisample_bokeh(
        cls,
        data,
        sample_options,
        output_data_directory,
        include_bar_graph=True,
        with_fit=True,
        with_errorbars=True,
        legend_location=None,
        show_plot=True,
        save_plot=True,
        ylims=None,
        shared_axes=True,
        name_prefix=None
    ):
        """
        Plots Qi vs. photon number for multiple samples using Bokeh. Also includes a bar graph of the average Qi values for each sample.
        
        Inputs:
        - data                      Dictionary containing data for each sample, 
                                    with keys as sample names and values as DataFrames.
        - sample_options            Dictionary containing options for each sample, such as 
                                    resonator indices to plot, frequency bin labels, and whether to include fits.
        - output_data_directory     Directory to save the plot.
        - include_bar_graph         Boolean to include a bar graph of the average Qi values. 
                                    Can also choose "only" to plot only the bar graph.
        - with_fit                  Boolean to include TLS fits in the plot.
        - with_errorbars            Boolean to include error bars in the plot.
        - legend_location           Location of the legend in the plot.
        - show_plot                 Boolean to show the plot.
        - save_plot                 Boolean to save the plot.
        - ylims                     Optional y-axis limits for the plot.
        - shared_axes               Boolean to share axes between plots.
        """

        assert len(data.keys()) == len(sample_options.keys()), f"Mismatch between data (length {len(data.keys())}) and sample (length {len(sample_options.keys())}) options "
        for sample in data.keys():
            assert isinstance(data[sample], pd.DataFrame)

        num_samples = len(data.keys())
        sample_names = list(data.keys())

        # bokeh setup - Qi vs. n_ph
        fig_line = figure(
            width=600,
            height=600,
            x_axis_type="log",
            y_axis_type="log",
            y_axis_label=r"$$Q_i$$",
            x_axis_label=r"Photon number  ⟨n⟩",
        )

        # bokeh setup - box plot
        fig_box = figure(
            x_range=sample_names,
            title=r"Single photon Qi",
            width=600,
            height=600,
            y_axis_type="log",
            y_axis_label=r"$$Q_i$$",
            x_axis_label=r"Sample name",
        )

        
        # colours
        if num_samples <= 10:
            base_colors = Category10[num_samples]
        elif num_samples <= 20:
            base_colors = Category20[num_samples]
        else:
            indices = np.linspace(0, 255, num_samples).astype(int)
            base_colors = [Viridis256[i] for i in indices]
        
        # loop through each sample
        for i, sample in enumerate(sample_options.keys()):
            # create class instance
            chunk = cls(fit_data = pd.DataFrame(data[sample]))

            freq_bin_labels = sorted(set(chunk.fit_data["freq bin"]))
            #freq_bin_labels = sample_options[sample]['freq_bin_labels']
            num_resonators = len(freq_bin_labels)
            name = sample_options[sample].get('name', sample)

            # check which resonators to plot
            res_idx = sample_options[sample].get('resonator_index_to_plot')
            if res_idx is not None:
                freqs_to_use = res_idx
            else:
                freqs_to_use = range(freq_bin_labels)
            # check for optional TLS-fit range
            n_ph_lims = sample_options[sample].get('n_ph_lims')
            # determine colour for each resonator
            base_color = base_colors[i]
            # Generate shades by adjusting brightness
            shades = [cls.adjust_lightness_bokeh(base_color, 0.8 + 0.2 * i / max(1, num_resonators - 1)) for i in range(num_resonators)]

            # loop through frequency bins
            Qi_sph = []  # list to store single photon Qi values for each resonator
            for j, freq_bin_cur in enumerate(freq_bin_labels):
                if j in freqs_to_use:
                    print(f"Plotting {sample}: {freq_bin_cur}")
                    # initialise plot data for new resonator
                    n_ph, Qi, Qi_upper, Qi_lower, Qerr  = [], [], [], [], []
                    f = float(freq_bin_cur.split()[0]) * 1e9  # Hz
                    for _, row in data[sample].iterrows():
                        # add measurement from self.fit_data if in current bin
                        if row["freq bin"] == freq_bin_cur:
                            n_ph.append(row["n_ph"])
                            Qi.append(row["Qi_dia_corr"])
                            Qi_upper.append(row["Qi_dia_corr"] + row["Qi_dia_corr_err"])
                            Qi_lower.append(float(row["Qi_dia_corr"]) - float(row["Qi_dia_corr_err"]))
                            Qerr.append(row["Qi_dia_corr_err"])

                    # sort lists by n_ph
                    sorted_data = sorted(zip(n_ph, Qi, Qi_upper, Qi_lower, Qerr), key=lambda x: x[0])
                    n_ph, Qi, Qi_upper, Qi_lower, Qerr = map(np.array, zip(*sorted_data)) if sorted_data else ([], [], [], [], [])

                    # filter n_ph and Qi
                    if n_ph_lims is not None:
                        mask = (n_ph > n_ph_lims[0]) & (n_ph < n_ph_lims[1])
                        n_ph = n_ph[mask]
                        Qi = Qi[mask]
                        Qi_upper = Qi_upper[mask]
                        Qi_lower = Qi_lower[mask]
                        Qerr = Qerr[mask]

                    # convert to ColumnDataSource for Bokeh plotting
                    source = ColumnDataSource(
                        data=dict(n_ph=n_ph, Qi=Qi, upper=Qi_upper, lower=Qi_lower, Qerr=Qerr)
                    )

                    # get single photon Qi
                    sph_indx = cls.find_photon_number_index(
                        data=source.data
                    )
                    sph_Qi = np.array(source.data["Qi"])[sph_indx]
                    Qi_sph.append(sph_Qi)

                    # TLS fit
                    n_ph_TLS, TLSfit = None, None
                    with_fit = sample_options[sample].get('with_fit', True)
                    if with_fit == True:
                        _, n_ph_TLS, TLSfit = cls.TLS_fit(
                            n_ph=source.data["n_ph"],
                            Qi=source.data["Qi"],
                            f=f,
                            T=sample_options[sample]['T'],
                            Qerr=source.data["Qerr"],
                            bounds=chunk.TLSfit_bounds,
                            n_ph_lims=n_ph_lims
                        )
                    # do plotting
                    fig_line.line(
                        source=source,
                        x="n_ph",
                        y="Qi",
                        # size=8, 
                        color=shades[j],
                        alpha=0.7,
                        legend_label=f"{sample}: {freq_bin_cur} (Qi = {sph_Qi:.1e})",
                    )

                    fig_line.scatter(
                        source=source,
                        x="n_ph",
                        y="Qi",
                        size=4,
                        color=shades[j],
                        fill_color="white",
                        alpha=0.7,
                    )

                    # errorbars
                    if with_errorbars == True:
                        errorbars = Whisker(
                            base="n_ph",
                            upper="upper",
                            lower="lower",
                            source=source,
                            line_color=shades[j],
                            line_alpha=0.7,
                            line_cap="round",
                            line_width="2",
                            upper_head=TeeHead(line_color=shades[j], line_alpha=0.7, size=6),
                            lower_head=TeeHead(line_color=shades[j], line_alpha=0.7, size=6),
                        )
                        fig_line.add_layout(errorbars)
                    if with_fit == True:
                        fig_line.line(
                            n_ph_TLS, TLSfit, line_color=shades[j], line_alpha=0.2, line_width=3
                    )

            # box plot - per sample (not per resonator)
            if include_bar_graph != False:
                # calculate per-sample statistics (across all resonators on the sample)
                q1, q2, q3 = np.percentile(Qi_sph, [25, 50, 75])
                iqr = q3 - q1
                upper_whisker = min(max(Qi_sph), q3 + 1.5 * iqr)
                lower_whisker = max(min(Qi_sph), q1 - 1.5 * iqr)
                # # check data
                # print(f"q1, q2, q3: {q1:.2e}, {q2:.2e}, {q3:.2e}")
                # print(f"upper whisker: {upper_whisker:.2e}, lower whisker: {lower_whisker:.2e}")
                # prepare data for plot and add to box plot
                box_source = ColumnDataSource(data=dict(
                                    sample=[sample], q1=[q1], q2=[q2], q3=[q3],
                                    upper=[upper_whisker], lower=[lower_whisker]
                                ))
                fig_box.vbar(x='sample', top='q3', bottom='q1', source=box_source, width=0.5, fill_color=base_color, alpha=0.5, line_color="black", legend_label=f"{name}")
                # Median lines
                
                # Whiskers
                fig_box.segment('sample', 'upper', 'sample', 'q3', source=box_source, line_color="black")
                fig_box.segment('sample', 'lower', 'sample', 'q1', source=box_source, line_color="black")
                fig_box.circle('sample', 'q2', source=box_source, size=6, color="black", fill_color="white")

        # legend
        fig_line.legend.location = legend_location
        #fig_line.legend.ncols = int(np.floor(num_samples/5) + 1) # TODO: figure out columns? 
        # title
        fig_line.title = f"Internal Q-factor"
        # increase font sizes
        fig_line.title.text_font_size = '16pt'
        fig_line.xaxis.axis_label_text_font_size = '14pt'
        fig_line.yaxis.axis_label_text_font_size = '14pt'
        fig_line.xaxis.major_label_text_font_size = '12pt'
        fig_line.yaxis.major_label_text_font_size = '12pt'
        fig_box.title.text_font_size = '16pt'
        fig_box.xaxis.axis_label_text_font_size = '14pt'
        fig_box.yaxis.axis_label_text_font_size = '14pt'
        fig_box.xaxis.major_label_text_font_size = '12pt'
        fig_box.yaxis.major_label_text_font_size = '12pt'
        fig_box.legend.label_text_font_size = '10pt'
        if ylims is not None:
            fig_line.y_range.start = ylims[0]
            fig_line.y_range.end = ylims[1]
            fig_box.y_range.start = ylims[0]
            fig_box.y_range.end = ylims[1]
        if include_bar_graph == False:
            # show plot
            if show_plot == True:
                show(fig_line)
                fig_line.toolbar = None
            # save plot
            if save_plot == True:
                fig_line.toolbar_location=None
                export_name = name_prefix + "_".join(list(sample_options.keys()))
                export_path = os.path.join(output_data_directory, f"line_{export_name}.png")
                export.export_png(obj=fig_line, filename=export_path)
                print(f"Plot saved at {export_path}")
        elif include_bar_graph == True or include_bar_graph == "both":
            fig_line.legend.visible = False
            # Change font sizes
            fig_box.legend.location = legend_location
            # fig_box.legend.ncols = int(np.floor(num_samples/5) + 1) # TODO: fix
            fig_box.legend.spacing = 0  # spacing between items
            if num_samples > 5:
                fig_box.xaxis.major_label_orientation = 0.785
            if shared_axes:
                if ylims != None:
                    print(f"Setting shared ylims to {ylims}")
                    fig_line.y_range.start = ylims[0]
                    fig_line.y_range.end = ylims[1]
                    fig_box.y_range.start = ylims[0]
                    fig_box.y_range.end = ylims[1]
                else:
                    fig_box.y_range = fig_line.y_range
            layout = gridplot([[fig_line, fig_box]], width=600, height=600, toolbar_location=None)
            # show plot
            if show_plot == True:
                show(layout)
            # save plot
            if save_plot == True:
                export_name = name_prefix + "_".join(list(sample_options.keys()))
                export_path = os.path.join(output_data_directory, f"boxLine_{export_name}.png")
                export.export_png(obj=layout, filename=export_path)
                print(f"Plot saved at {export_path}")
        elif include_bar_graph == "only":
            # show plot
            fig_box.legend.location = legend_location
            if show_plot == True:
                show(fig_box)
                # fig_box.toolbar = None
            # save plot
            if save_plot == True:
                fig_box.toolbar_location=None
                export_name = name_prefix + "_".join(list(sample_options.keys()))
                export_path = os.path.join(output_data_directory, f"box_{export_name}.png")
                export.export_png(obj=fig_box, filename=export_path)
                print(f"Plot saved at {export_path}")

    @staticmethod
    def adjust_lightness_bokeh(hex_color, factor):
        import colorsys
        """Modify the brightness of a hex color."""
        hex_color = hex_color.lstrip("#")  # Remove '#' from the hex code
        r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))  # Convert to RGB [0,1]
        h, l, s = colorsys.rgb_to_hls(r, g, b)  # Convert to HLS
        l = max(0, min(1, l * factor))  # Adjust lightness
        new_r, new_g, new_b = colorsys.hls_to_rgb(h, l, s)  # Convert back to RGB
        return f"#{int(new_r * 255):02x}{int(new_g * 255):02x}{int(new_b * 255):02x}"  # Convert back to hex
    

    def sort_dict_by_key(data: dict, sort_key="n_ph"):
        # Ensure the sort key exists
        assert sort_key in data, f"'{sort_key}' not found in dictionary."
        # Get sort indices from the sort_key
        sort_indices = np.argsort(np.array(data[sort_key], dtype=float))
        # Sort each entry in the dictionary using those indices
        sorted_data = {
            key: [data[key][i] for i in sort_indices]
            for key in data
        }
        return sorted_data

    def trim_fit_data_by_qi(self, qi_lims=[1e4, 5e7]):
        """
        Trims the fit data to only include entries with Qi values within the specified limits.
        
        Inputs:
        - qi_lims: List of two values specifying the lower and upper limits for Qi.
        
        Returns:
        - None, but modifies self.fit_data in place.
        """
        assert isinstance(qi_lims, list) and len(qi_lims) == 2, "qi_lims should be a list of two values."
        assert qi_lims[0] < qi_lims[1], "Lower limit should be less than upper limit."
        
        len_before_trim = len(self.fit_data['Qi_dia_corr'])
        self.fit_data['Qi_dia_corr'] = pd.to_numeric(self.fit_data['Qi_dia_corr'], errors='coerce')
        self.fit_data = self.fit_data[
            (self.fit_data['Qi_dia_corr'] > qi_lims[0]) & 
            (self.fit_data['Qi_dia_corr'] < qi_lims[1])
        ]
        len_after_trim = len(self.fit_data['Qi_dia_corr'])
        print(f"Trimmed {len_before_trim - len_after_trim} data points for qi range {qi_lims}.")
