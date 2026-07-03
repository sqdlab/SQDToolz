from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from laboneq_applications.experiments import qubit_spectroscopy
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
import scipy.interpolate
import scipy.optimize
from sqdtoolz.Utilities.DataFitting import DFitPeakLorentzian
from scipy.signal import find_peaks

class ExpZIQubitPowerSweep(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_id, frequencies, **kwargs):
        assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        self._qubit_id = qubit_id

        self._update_qubit = kwargs.pop('update_qubit_params', False)
        self._drive_power_range = kwargs.pop('drive_power_range', np.linspace(-30, 10, 9))
        self._num_plotted_peaks = kwargs.pop('num_plotted_peaks', 3)
        self._min_prominence = kwargs.pop('min_peak_prominence', 0.01)

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)

        self._is_trough = kwargs.pop('is_trough', False)
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')
        self._frequencies = frequencies
        self._hal_QPU = hal_QPU

        kwargs['frequencies'] = [frequencies]
        super().__init__(name, expt_config, qubit_spectroscopy, hal_QPU, [qubit_id], **kwargs)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        var_pwr = VariablePropertyTransient('Power', self._hal_QPU.get_qubit_obj(self._qubit_id), 'DrivePower')
        super()._run(file_path, sweep_vars=[(var_pwr, self._drive_power_range)], **kwargs)

    def _post_process(self, data):
        leData = self.retrieve_last_dataset(self._qubit_id)
        ampl_vals, freq_vals = leData.param_vals
        arr = leData.get_numpy_array()

        ampl = np.sqrt(arr[:,:,0]**2 + arr[:,:,1]**2)

        is_trough = self._is_trough

        all_peak_freqs = []      
        all_peak_props = []      
        primary_peak_freqs = []  

        for cur_slice in ampl:
            signal = -cur_slice if is_trough else cur_slice
            peak_indices, props = find_peaks(signal, prominence=0, distance=5)
            if len(peak_indices) == 0:
                all_peak_freqs.append(np.array([]))
                all_peak_props.append(props)
                primary_peak_freqs.append(np.nan)
                continue
            peak_freqs = freq_vals[peak_indices]
            all_peak_freqs.append(peak_freqs)
            all_peak_props.append(props)
            #
            primary_idx = peak_indices[np.argmax(props['prominences'])]
            primary_peak_freqs.append(freq_vals[primary_idx])
        primary_peak_freqs = np.array(primary_peak_freqs)

        fitted_data = {
            'all_peak_freqs': all_peak_freqs,
            'all_peak_props': all_peak_props,
            'primary_peak_freqs': primary_peak_freqs,
        }

        if not self._dont_plot:
            fig, ax = plt.subplots(1); fig.set_figwidth(15)
            ExpZIQubitPowerSweep.plot_fitted_results(ax, self._hal_QPU, self._qubit_id, freq_vals, ampl_vals, ampl, fitted_data, min_prominence=self._min_prominence, top_n=self._num_plotted_peaks)
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
            fig.savefig(self._file_path + 'fitted_plot.png')
    
    @staticmethod
    def plot_fitted_results(ax, hal_QPU, qubit_id, freq_vals, pwr_vals, ampl, fitted_data, min_prominence=None, top_n=3):
        row_means = np.nanmean(ampl, axis=1)
        ampl_corrected = (ampl.T - row_means).T
        ax.pcolor(freq_vals, pwr_vals, ampl_corrected)
        #
        all_peak_freqs = fitted_data['all_peak_freqs']
        all_peak_props = fitted_data['all_peak_props']
        primary_peak_freqs = fitted_data['primary_peak_freqs']
        #
        for pwr, peaks, props, primary_freq in zip(pwr_vals, all_peak_freqs, all_peak_props, primary_peak_freqs):
            if len(peaks) == 0:
                continue
            prominences = props['prominences']
            # print(prominences)
            is_primary = peaks == primary_freq
            sec_peaks = peaks[~is_primary]
            sec_proms = prominences[~is_primary]
            if len(sec_peaks) == 0:
                continue
            if min_prominence is not None:
                keep = sec_proms >= min_prominence
            else:
                # Default: keep top_n most prominent peaks
                n_keep = min(top_n, len(sec_peaks))
                keep_idx = np.argsort(sec_proms)[-n_keep:]
                keep = np.zeros(len(sec_peaks), dtype=bool)
                keep[keep_idx] = True
            sec_peaks = sec_peaks[keep]
            if len(sec_peaks) == 0:
                continue
            ax.plot(sec_peaks, np.full(len(sec_peaks), pwr), 'wo', markersize=2)
        valid = ~np.isnan(primary_peak_freqs)
        ax.plot(primary_peak_freqs[valid], pwr_vals[valid], 'ro', markersize=5)
        ax.set_title(f"{qubit_id} qubit spectroscopy power sweep ($f_r={hal_QPU.get_qubit_obj(qubit_id).ReadoutFrequency*1e-9:.4f}$ GHz)")
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Qubit drive power (dBm)')