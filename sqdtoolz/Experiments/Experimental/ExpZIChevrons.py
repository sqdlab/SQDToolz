from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Experiments.Experimental.ZI import qubit_single_chevron
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import numpy as np
from sqdtoolz.Utilities.DataFitting import DFitPeakLorentzian

class ExpZIChevrons(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert len(qubit_ids) == 1, "Only 1 qubit is supported for this experiment..."
        self._fit_freq = None
        super().__init__(name, expt_config, qubit_single_chevron, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        leData = self.retrieve_last_dataset(self._qubit_ids[0])
        arr = leData.get_numpy_array()
        dataI = arr[:,:,0]
        dataQ = arr[:,:,1]

        freqs = leData.param_vals[0]
        times = leData.param_vals[1]
        phs = np.atan2(dataQ, dataI)

        norm_fac_freq, norm_prefix_freq = Miscellaneous.get_metric_multiplier(freqs)
        norm_fac_time, norm_prefix_time = Miscellaneous.get_metric_multiplier(times)

        fig, axs = plt.subplots(nrows=2, gridspec_kw={'height_ratios':[1,3]})
        axs[1].pcolor(freqs/norm_fac_freq, times/norm_fac_time, phs.T)
        axs[1].set_xlabel(f"Frequency ({norm_prefix_freq}Hz)")
        axs[1].set_ylabel(f"Pulse duration ({norm_prefix_time}s)")

        signal_vars = []
        for cur_freq_ind in range(freqs.size):
            signal_vars.append(np.var(phs[cur_freq_ind,:]))

        dFit = DFitPeakLorentzian()
        dpkt = dFit.get_fitted_plot(freqs, np.array(signal_vars), dontplot=True)
        dpkt['centre']
        axs[0].plot(freqs, signal_vars)
        axs[0].set_xticks([])
        axs[0].set_yticks([])
        axs[0].set_ylabel('$\sim VAR(P_z)$')
        axs[0].plot(freqs, dpkt['fit_data'], 'r-')

        axs[1].vlines([dpkt['centre']/norm_fac_freq], ymin=np.min(times)/norm_fac_time, ymax=np.max(times)/norm_fac_time, color='white', linestyle='dashed')
        axs[0].set_title(f"Frequency: {Miscellaneous.get_units(dpkt['centre'])}Hz")
        fig.subplots_adjust(hspace=0.02)

        self._fit_freq = dpkt['centre']

        fig.savefig(self._file_path + f'fitted_plot_{self._qubit_ids[0]}.png')
        if not self._dont_show_plot:
            fig.show()
        else:
            plt.close(fig)

    def update_qubits(self):
        assert self._fit_freq != None, "Must run Chevron Experiment before qubit can be updated."
        if self._transition == 'ef':
            self._hal_QPU.get_qubit_obj(self._qubit_ids[0]).DriveEF = self._fit_freq
        else:
            self._hal_QPU.get_qubit_obj(self._qubit_ids[0]).DriveGE = self._fit_freq
        self._fit_freq = None
