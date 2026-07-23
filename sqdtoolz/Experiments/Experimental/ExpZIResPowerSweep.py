from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from laboneq_applications.experiments import resonator_spectroscopy
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
import scipy.interpolate
import scipy.optimize
from sqdtoolz.Utilities.DataFitting import DFitPeakLorentzian

class ExpZIResPowerSweep(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_id, frequencies, **kwargs):
        assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        self._qubit_id = qubit_id

        self._amplitude_range = kwargs.pop('amplitude_range', np.linspace(0.001, 0.9, 20))

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)

        self._is_trough = kwargs.pop('is_trough', True)
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._frequencies = frequencies
        self._hal_QPU = hal_QPU

        kwargs['frequencies'] = frequencies
        super().__init__(name, expt_config, resonator_spectroscopy, hal_QPU, [qubit_id], **kwargs)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        var_ampl = VariablePropertyTransient('Amplitude', self._hal_QPU.get_qubit_obj(self._qubit_id),'ReadoutAmplitude')
        super()._run(file_path, sweep_vars=[(var_ampl, self._amplitude_range)], **kwargs)

    def _post_process(self, data):
        leData = self.retrieve_last_dataset(self._qubit_id)
        ampl_vals,freq_vals = leData.param_vals
        arr = leData.get_numpy_array()

        ampl = np.sqrt(arr[:,:,0]**2 + arr[:,:,1]**2)

        is_trough = self._is_trough

        dfit = DFitPeakLorentzian()
        res_freqs = []
        for cur_slice in ampl:
            dpkt = dfit.get_fitted_plot(freq_vals, cur_slice, dip=is_trough, dontplot=True)
            res_freqs.append(dpkt['centre'])
        res_freqs = np.array(res_freqs)

        fitted_data = {'raw_fit_freqs': res_freqs,}

        if not self._dont_plot:
            fig, ax = plt.subplots(1); fig.set_figwidth(15)
            ExpZIResPowerSweep.plot_fitted_results(ax, self._hal_QPU, self._qubit_id, freq_vals, ampl_vals, ampl, fitted_data)
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
            fig.savefig(self._file_path + 'fitted_plot.png')
    
    @staticmethod
    def plot_fitted_results(ax, hal_QPU, qubit_id, freq_vals, ampl_vals, ampl, fitted_data):
        row_means = np.nanmean(ampl, axis=1)
        ampl_corrected = (ampl.T - row_means).T
        ax.pcolor(freq_vals, ampl_vals, ampl_corrected)
        ax.plot(fitted_data['raw_fit_freqs'], ampl_vals, 'wo')
        ax.set_title(f"{qubit_id} resonator power sweep at {hal_QPU.get_qubit_obj(qubit_id).ReadoutPower} dBm")
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Readout amplitude')