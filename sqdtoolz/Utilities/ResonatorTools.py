import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize
import os
import pandas as pd
import re
import warnings
from sqdtoolz.Utilities.FileIO import FileIOReader
from resonator_tools import circuit  # type: ignore
from pprint import pprint
from pathlib import Path

warnings.filterwarnings("ignore", "Covariance of the parameters could not be estimated")

# imports for plotting (optional)
plot_backend = None
try:
    from bokeh.models import Whisker, ColumnDataSource, TeeHead, Band, Range1d  # type: ignore
    from bokeh.plotting import figure, show  # type: ignore
    from bokeh.io import output_notebook, export  # type: ignore
    from bokeh.palettes import Viridis256, Category10  # type: ignore
except:
    warnings.warning("Bokeh not imported. You will have to use mpl for plotting")
    PLOT_BACKEND = "matplotlib"
    pass
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
        TLSfit_bounds=([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1]),
        print_log=False,
        notebook=False,
        fit_data={},
        with_fit=None
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

        # private class variables
        self._data_file_name = "data.h5"
        self._config_file_name = "experiment_configurations.txt"

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
                x_axis_label=r"Photon number " + r"$$\langle n \rangle$$",
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
        power_config_order="last"
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

        Outputs:
        - self.data                 Dictionary containing measurement data and metadata.
        """
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

        if print_log != "none":
            print(f"Importing data from {self.data_path}\n")
        # Loop through each sub-folder
        for root, _, files in os.walk(self.data_path):
            # root_shortened = Path(*Path(root).parts[-3:])
            root_shortened = Path(*Path(root).parts[-2:])
            # Check if data.h5 with valid config file exists in the folder
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
        assert self.data, "No valid data found at data_path."
        print("Data import complete.")
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
                print(f"Fitting {measurement_name} failed.")
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
                    (
                        print(
                            f"{fits_completed}\t{re.split(r'[\\/]', measurement_name)[-1]}\t"
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
        #  make sure fit data has been added to dictionary
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

    # sort data frame along multiple axes
    def fit_data_to_sorted_dataframe(self, axes_to_sort=["fr", "power"], n_ph_lims=None):
        fit_data_list = []
        first = True
        for _, measurement_data in self.data.items():
            fit_data_list.append(measurement_data["fit"])
            # get column names for DataFrame
            if first == True:
                columns = measurement_data["fit"].keys()
        # convert to DataFrame
        df = pd.DataFrame(fit_data_list, columns=columns)
        df_sorted = df.sort_values(by=axes_to_sort, ascending=[True, True]).reset_index(
            drop=True
        )
        if n_ph_lims != None:
            assert isinstance(n_ph_lims, list)
            assert len(n_ph_lims) == 2
            self.fit_data = df_sorted[(df_sorted['n_ph'] > n_ph_lims[0]) & (df_sorted['n_ph'] < n_ph_lims[1])]
        else:
            self.fit_data = df_sorted

    # get labels for frequency bins
    def get_frequency_bin_labels(self):
        freq_list_rounded = self.fit_data["fr"].multiply(1e-9).round(2)
        freq_bins = list(set(freq_list_rounded))
        self.num_resonators = len(freq_bins)
        freq_bins.sort()
        self.freq_bin_labels = [f"{i:.2f} GHz" for i in freq_bins]
        assert len(self.freq_bin_labels) == self.num_resonators, "Bin labelling failed."
        return self.freq_bin_labels

    # search for frequencies and create bins
    def get_frequency_bins(self):
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
            do_fit=True
            ):
        '''
        Saves a text file with a complete data summary to the data_path.
        '''
        
        do_fit = self.do_TLS_fit if self.do_TLS_fit != None else 0

        if save_directory != None:
            save_path = save_directory
        else:
            save_path = self.save_path
        export_path = os.path.join(save_path, f"data_summary_{self.name}.txt")
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
        Qc = np.array(self.fit_data["Qc_dia_corr"])

        for i, freq_bin_cur in enumerate(self.freq_bin_labels):

            res_data = self.isolate_resonator_data(freq_bin_cur)

            LP_indx = self.find_photon_number_index(
                data=self.fit_data, search_key="n_ph", photon_number=1
            )
            Qi_LP.append(np.array(res_data["Qi"])[LP_indx])
            # get high power Qi
            HP_indx = self.find_photon_number_index(
                data=self.fit_data, search_key="n_ph", photon_number=n_ph_HP
            )
            # adjust HP_indx if it is outside the measured range of n_ph
            if HP_indx > len(np.array(res_data["Qi"])):
                HP_indx = len(np.array(res_data["Qi"])) - 1
            Qi_HP.append(np.array(res_data["Qi"])[HP_indx])

            # calculate per-resonator values
            f_av = self.filtered_mean_iqr(res_data["f"])
            Qc_av = self.filtered_mean_iqr(res_data["Qc"]) 
            f_range = self.filtered_mean_iqr(res_data["f"], filtered_range=True)
            Qc_range = self.filtered_mean_iqr(res_data["Qc"], filtered_range=True)

            if do_fit:
                # calculate F*tanδ
                fit_dict, _, _ = self.TLS_fit(res_data["n_ph"], res_data["Qi"], f=f_av, T=self.T, Qerr=res_data["Qerr"], bounds=self.TLSfit_bounds)
                F_tan_delta.append(fit_dict["F_tan_delta"])
                n_c.append(fit_dict["n_c"])
            else:
                F_tan_delta.append(0)
                n_c.append(0)

            # print to file
            vals = [Qi_LP[i], Qi_HP[i], Qc_av, Qc_range, f_av, f_range, F_tan_delta[i], n_c[i]]
            with open(export_path, "a") as file:
                file.write("".join(f"{val:<{col_width}.2e}" for val in vals) + "\n")

        # calculate statistical values
        Qi_LP_max = np.max(Qi_LP)
        Qi_LP_av = self.filtered_mean_iqr(Qi_LP)
        Qi_LP_SE = np.std(Qi_LP, ddof=1) / np.sqrt(len(Qi_LP))
        Qi_HP_max = np.max(Qi_HP)
        Qi_HP_av = self.filtered_mean_iqr(Qi_HP)
        Qi_HP_SE = np.std(Qi_HP, ddof=1) / np.sqrt(len(Qi_HP))
        Qc_av = self.filtered_mean_iqr(Qc)
        Qc_SE = self.filtered_mean_iqr(Qc, filtered_SE=True)
        Qc_max = np.max(Qc)
        Qc_min = np.min(Qc)
        if do_fit:
            F_tan_delta_av = self.filtered_mean_iqr(F_tan_delta)
            F_tan_delta_SE = self.filtered_mean_iqr(F_tan_delta, filtered_SE=True)
            F_tan_delta_min = np.min(F_tan_delta)
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
        data = np.array(data)  # Convert to NumPy array
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
        for _, row in self.fit_data.iterrows():
            # add measurement from self.fit_data if in current bin
            if row["freq bin"] == freq_bin_label:
                n_ph.append(row["n_ph"])
                Qi.append(row["Qi_dia_corr"])
                Qc.append(row["Qc_dia_corr"])
                f.append(row['fr'])
                Qerr.append(row["Qi_dia_corr_err"])
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
                x_axis_label=r"Photon number " + r"$$\langle n \rangle$$",
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
                        Qi_upper.append(row["Qi_dia_corr"] + row["Qi_dia_corr_err"])
                        Qi_lower.append(row["Qi_dia_corr"] - row["Qi_dia_corr_err"])
                        Qerr.append(row["Qi_dia_corr_err"])
                # convert to ColumnDataSource for Bokeh plotting
                source = ColumnDataSource(
                    data=dict(n_ph=n_ph, Qi=Qi, upper=Qi_upper, lower=Qi_lower, Qerr=Qerr)
                )
                # get single photon Qi
                sph_indx = self.find_photon_number_index(
                    data=source.data, search_key="n_ph"
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
                    )

                # bokeh plot
                if backend == "bokeh":
                    # do plotting
                    color = self._colourmap[i * len(self._colourmap) // self.num_resonators]
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
                x_axis_label="Photon number " + r"$$\langle n \rangle$$",
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
        # bokeh setup
        if backend == "bokeh":
            self.fig_bokeh = figure(
                title=f"{self.name}: external Q-factor",
                width=1000,
                height=600,
                x_axis_type="log",
                y_axis_type="log",
                y_axis_label=r"$$Q_c$$",
                x_axis_label=r"Photon number " + r"$$\langle n \rangle$$",
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
                        Qc_upper.append(row["absQc"] + row["absQc_err"])
                        Qc_lower.append(row["absQc"] - row["absQc_err"])
                        n_ph.append(row["n_ph"])
                        Qc_err.append(row["absQc_err"])
                # convert to ColumnDataSource for Bokeh plotting
                source = ColumnDataSource(
                    data=dict(
                        n_ph=n_ph, Qc=Qc, upper=Qc_upper, lower=Qc_lower, Qc_err=Qc_err
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
        n_ph, Qi, f, T, bounds=None, Qerr=None, print_log=False, print_fit=True
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

        Outputs:
        - Tuple containing (x, y, z)
            - x: dict of fit parameters {"F_tan_delta", "n_c", "Q_HP", "beta"}
            - y: n_ph (array)
            - z: the TLS fit as a function of n_ph (array)
        """

        assert isinstance(T, (float, int)), "Temperature should be a float or int."
        assert isinstance(f, (float, int)), "Frequency should be a float or int."
        assert len([n_ph, Qi, Qerr]) > 0, "Please provide n_ph and Qi data."

        # constants
        hbar = 1.054 * 10 ** (-34)
        kB = 1.380649 * 10 ** (-23)
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
            bounds = ([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1])
        else:
            assert isinstance(
                bounds, tuple
            ), "Bounds should be passed as a tuple of lists, with elements corresponding to [F_delta_TLS0, n_c, Q_HP, beta]. The first tuple entry is lower bounds, and the second is upper. e.g. bounds = ([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1])"
            assert (
                len(bounds[0]) == 4
            ), "Bounds should be passed as a tuple of lists, with elements corresponding to [F_delta_TLS0, n_c, Q_HP, beta]. The first tuple entry is lower bounds, and the second is upper. e.g. bounds = ([0, 0.2, 0, 0.0], [1, 1e3, 1e9, 1])"

        # check guesses are valid (if not, move within bounds)
        for i, init in enumerate(init_guesses):
            if init < bounds[0][i]:
                init_guesses[i] = bounds[0][i] + 1e-8
            elif init > bounds[1][i]:
                init_guesses[i] = bounds[1][i] - 1e-8

        # with error bars
        if Qerr:
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
                    sigma=np.array(Qerr),
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
            print(f"TLS fit ({f*1e-9:.2f} GHz)") if print_log != True else 0
            print(f"\tF delta_TLS =\t{popt[0]:.2e}")
            print(f"\tn_c =\t\t{popt[1]:.2f}")
            print(f"\tQ_HP =\t\t{popt[2]:.2e}")
            print(f"\tbeta =\t\t{popt[3]:.2f}\n")
        
        fit_dict = {
            "F_tan_delta": popt[0],
            "n_c": popt[1],
            "Q_HP": popt[2],
            "beta": popt[3],
        }

        # return (x, y) tuple of fit data
        return (fit_dict, n_ph, TLS_model(np.array(n_ph), *popt))

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
    def find_photon_number_index(data: dict, search_key="n_ph", photon_number=1):
        assert search_key in data.keys()
        index, value = min(
            enumerate(data[search_key]), key=lambda x: abs(x[1] - photon_number)
        )
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
        output_directory=None
    ):
        """
        Creates a bokeh plot for Qi comparison of multiple resonator samples. 

        Inputs:
        - main_data_directory   The directory in which to search for the data (string).
        - sample_options        A dictionary containing information pertaining to each sample.
                                Example:
                                sample_options = {
                                    'IQM-05' : {
                                        'resonator_index_to_plot' : [1, 2, 3, 4, 5],
                                        'name' : "IQM-05-A",
                                        'files_to_ignore' : ['IQM-05-A', "141602"],
                                        'power_dict' : default_power_dict
                                        },
                                    'IQM-03-01' : {
                                        'resonator_index_to_plot' : [1, 2, 3, 4, 5],
                                        'name' : "IQM-03-01",
                                        'files_to_ignore' : None,
                                        'power_dict' : default_power_dict
                                        }
                                    }

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
            sample_path = os.path.join(main_data_directory, sample)
            assert os.path.isdir(sample_path), f"Sample directory '{sample_path}' does not exist."
            print(f"{sample}\n Starting data acquisition and fitting...")
            # set data path, fitting parameters, and line attenuations
            chunk = cls(data_path = sample_path,
                                    sample_name = sample,
                                    temperature = 26e-3,
                                    power_dict= sample_options[sample]['power_dict'],
                                    TLSfit_bounds=([0, 10, 0, 0.0], [1, 1e3, 1e9, 1]),
                                    print_log=False,
                                    )
            # do fitting etc. get a dict back
            chunk.import_data(additional_attenuation=0, 
                        files_to_ignore=sample_options[sample]['files_to_ignore']
                        )
            chunk.do_circlefit(remove_duplicates=True, save_fit=False)
            # assign dict
            data[sample] = chunk.fit_data   
            sample_options[sample]['freq_bin_labels'] = chunk.freq_bin_labels
            print("\n")
        # pass to plotting function
        cls.plot_Qi_multisample_bokeh(data=data, 
                                      sample_options=dict(sample_options), 
                                      main_data_directory=main_data_directory, 
                                      output_data_directory=output_directory
                                      )

    @classmethod
    # Qi vs photon number (static)
    def plot_Qi_multisample_bokeh(
        cls,
        data,
        sample_options,
        main_data_directory,
        output_data_directory,
        with_fit=True,
        with_errorbars=True,
        legend_location="bottom_right",
        show_plot=True,
        save_plot=True,
        ylims=None,
    ):
        assert len(data.keys()) == len(sample_options.keys()), f"Mismatch between data (length {len(data.keys())}) and sample (length {len(sample_options.keys())}) options "
        for sample in data.keys():
            assert isinstance(data[sample], pd.DataFrame)

        num_samples = len(data.keys())

        # bokeh setup
        fig_bokeh = figure(
            width=1000,
            height=600,
            x_axis_type="log",
            y_axis_type="log",
            y_axis_label=r"$$Q_i$$",
            x_axis_label=r"Photon number " + r"$$\langle n \rangle$$",
        )
        # colourmap = Viridis256
        if ylims != None:
            fig_bokeh.y_range = Range1d(ylims[0], ylims[1])
        
        # colours
        base_colors = Category10.get(num_samples) or Category10[10][:num_samples] if num_samples <= 10 else Viridis256(num_samples)
        
        # loop through each sample
        for i, sample in enumerate(sample_options.keys()):
            # create class instance
            chunk = cls(fit_data = pd.DataFrame(data[sample]))
            freq_bin_labels = sample_options[sample]['freq_bin_labels']
            num_resonators = len(freq_bin_labels)
            # check which resonators to plot
            if sample_options[sample]['resonator_index_to_plot'] != None:
                freqs_to_use = sample_options[sample]['resonator_index_to_plot']
            elif sample_options[sample]['resonator_index_to_plot'] == None:
                freqs_to_use = range(freq_bin_labels)
            # determine colour for each resonator
            base_color = base_colors[i]
            # Generate shades by adjusting brightness
            shades = [cls.adjust_lightness_bokeh(base_color, 0.8 + 0.2 * i / max(1, num_resonators - 1)) for i in range(num_resonators)]
            
            # loop through frequency bins
            for i, freq_bin_cur in enumerate(freq_bin_labels):
                if i in freqs_to_use:
                    # initialise plot data for new resonator
                    n_ph, Qi, Qi_upper, Qi_lower, Qerr = [], [], [], [], []
                    f = float(freq_bin_cur.split()[0]) * 1e9  # Hz
                    for _, row in data[sample].iterrows():
                        # add measurement from self.fit_data if in current bin
                        if row["freq bin"] == freq_bin_cur:
                            n_ph.append(row["n_ph"])
                            Qi.append(row["Qi_dia_corr"])
                            Qi_upper.append(row["Qi_dia_corr"] + row["Qi_dia_corr_err"])
                            Qi_lower.append(row["Qi_dia_corr"] - row["Qi_dia_corr_err"])
                            Qerr.append(row["Qi_dia_corr_err"])
                    # convert to ColumnDataSource for Bokeh plotting
                    source = ColumnDataSource(
                        data=dict(n_ph=n_ph, Qi=Qi, upper=Qi_upper, lower=Qi_lower, Qerr=Qerr)
                    )
                    # get single photon Qi
                    sph_indx = cls.find_photon_number_index(
                        data=source.data, search_key="n_ph"
                    )
                    sph_Qi = np.array(source.data["Qi"])[sph_indx]
                    # TLS fit
                    n_ph_TLS, TLSfit = None, None
                    if with_fit == True:
                        _, n_ph_TLS, TLSfit = cls.TLS_fit(
                            n_ph=source.data["n_ph"],
                            Qi=source.data["Qi"],
                            f=f,
                            T=sample_options[sample]['T'],
                            Qerr=source.data["Qerr"],
                            bounds=chunk.TLSfit_bounds,
                        )
                    # do plotting
                    fig_bokeh.line(
                        source=source,
                        x="n_ph",
                        y="Qi",
                        size=8,
                        color=shades[i],
                        alpha=0.7,
                        legend_label=f"{sample}: {freq_bin_cur} (Qi = {sph_Qi:.1e})",
                    )

                    fig_bokeh.circle(
                        source=source,
                        x="n_ph",
                        y="Qi",
                        size=8,
                        color=shades[i],
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
                            line_color=shades[i],
                            line_alpha=0.7,
                            line_cap="round",
                            line_width="2",
                            upper_head=TeeHead(line_color=shades[i], line_alpha=0.7, size=6),
                            lower_head=TeeHead(line_color=shades[i], line_alpha=0.7, size=6),
                        )
                        fig_bokeh.add_layout(errorbars)
                    if with_fit == True:
                        fig_bokeh.line(
                            n_ph_TLS, TLSfit, line_color=shades[i], line_alpha=0.2, line_width=3
                    )
        # legend
        fig_bokeh.legend.location = legend_location
        # title
        fig_bokeh.title = f"Internal Q-factor"
        # show plot
        if show_plot == True:
            show(fig_bokeh)
        # save plot
        if save_plot == True:
            export_name = "_".join(list(sample_options.keys()))
            export_path = os.path.join(output_data_directory, f"Qi_{export_name}.png")
            export.export_png(obj=fig_bokeh, filename=export_path)
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