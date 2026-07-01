from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ExpZIRes import ExpZIRes
from laboneq_applications.experiments import resonator_spectroscopy, qubit_spectroscopy
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sqdtoolz.Utilities.FileIO import FileIODirectory
from pathlib import Path

class ExpZIQubitFluxSweep:
    def __init__(self, name, expt_config, hal_QPU, qubit_id, res_frequencies, qubit_frequencies, flux_range, **kwargs):
        assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        self._qubit_id = qubit_id
        self._name = name
        self._expt_config = expt_config

        self._update_qubit = kwargs.pop('update_qubit_params', True)
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)

        self._is_trough = kwargs.pop('is_trough', True)
        self._fit_type = kwargs.pop('res_fit_type', 'Full')
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')
        self._flux_range = flux_range
        self._res_freq_range = res_frequencies
        self._qubit_freq_range = qubit_frequencies

        self._hal_QPU = hal_QPU

        self._enable_ZI_log_messages = kwargs.pop('enable_ZI_log_messages', False)
        self._print_file_path = kwargs.pop('print_file_path', False)
    
    def run(self, lab):
        var_flux = VariablePropertyTransient('Flux', self._hal_QPU.get_qubit_obj(self._qubit_id), 'FluxDC')
        lab.group_open(self._name)
        #
        fr = self._hal_QPU.get_qubit_obj(self._qubit_id).ReadoutFrequency
        drive_pwr = self._hal_QPU.get_qubit_obj(self._qubit_id).DrivePower
        # TODO: proper runtime estimate
        if not self._flux_range is None:
            for flux in self._flux_range:
                var_flux.Value = flux
                #
                expR = ExpZIRes(f'res_spec_{self._qubit_id}', self._expt_config, self._hal_QPU, self._qubit_id, frequencies=self._res_freq_range, dont_plot=self._dont_plot, is_trough=self._is_trough, fit_type=self._fit_type, update=True)
                lab.run_single(expR, disable_ZI_logging=not self._enable_ZI_log_messages)
                #
                expQ = ExpZIqubit(f'qubit_spec_{self._qubit_id}', self._expt_config, qubit_spectroscopy, self._hal_QPU, [self._qubit_id], frequencies=[self._qubit_freq_range], ZI_plot=not self._dont_plot, update=self._update_qubit)
                lab.run_single(expQ, disable_ZI_logging=not self._enable_ZI_log_messages)
        lab.group_close()
        if not self._update_qubit:
            self._hal_QPU.get_qubit_obj(self._qubit_id).ReadoutFrequency = fr
        #
        dataQ = FileIODirectory(expQ._file_path + f'{self._qubit_id}.h5')
        dataR = FileIODirectory(expR._file_path + f'{self._qubit_id}.h5')

        arrQ = dataQ.get_numpy_array()
        freq_valsQ = dataQ.param_vals[1]
        amplQ = np.sqrt(arrQ[:,:,0]**2 + arrQ[:,:,1]**2)
        row_means = np.nanmean(amplQ, axis=1)
        amplQ_corrected = (amplQ.T - row_means).T

        arrR = dataR.get_numpy_array()
        freq_valsR = dataR.param_vals[1]
        amplR = np.sqrt(arrR[:,:,0]**2 + arrR[:,:,1]**2)
        row_means = np.nanmean(amplR, axis=1)
        amplR_corrected = (amplR.T - row_means).T
        #
        fig, axes = plt.subplots(ncols=2, sharey=True, figsize=(14,5)); 
        fig.suptitle(f"{self._qubit_id} flux sweep", fontsize=16)
        axes[0].pcolor(freq_valsQ, self._flux_range, amplQ_corrected)
        axes[0].set_title('Qubit spectroscopy')
        axes[0].set_ylabel('Flux (V)')
        axes[1].pcolor(freq_valsR, self._flux_range, amplR_corrected)
        axes[1].set_title('Resonator spectroscopy')
        for ax in axes:
            ax.set_xlabel('Frequency (Hz)')
            ax.yaxis.grid(True, color='white', alpha=0.3, linewidth=0.8)
        fig.tight_layout()
        parent = str(Path(expQ._file_path).parent)
        fig.savefig(parent + '/Overview.png')
        #
        fig = plt.figure(figsize=(14, 5))
        gs = GridSpec(3, 2, width_ratios=[2, 1], figure=fig)
        fig.suptitle(f"{self._qubit_id} qubit spectroscopy", fontsize=16)
        ax_main = fig.add_subplot(gs[:, 0])
        ax_main.pcolor(freq_valsQ, self._flux_range, amplQ_corrected)
        ax_main.set_title(f"Flux sweep")
        ax_main.set_ylabel('Flux (V)')
        ax_main.set_xlabel('Frequency (Hz)')

        flux_min, flux_max = self._flux_range[0], self._flux_range[-1]
        flux_targets = [flux_min, (flux_min + flux_max) / 2, flux_max]
        flux_indices = [np.argmin(np.abs(self._flux_range - f)) for f in flux_targets]
        
        axes_right = [fig.add_subplot(gs[i, 1]) for i in range(3)]
        axes_right[0].set_title('Linescans')
        for ax, idx in zip(axes_right, flux_indices):
            flux_val = self._flux_range[idx]
            ax.plot(freq_valsQ, amplQ_corrected[idx, :], linewidth=1.0, label = f"Flux = {flux_val:.4g} V")
            ax.legend(loc='lower right')
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel('Amplitude')
            ax.xaxis.grid(True, color='black', alpha=0.3, linewidth=0.8)
            ax_main.axhline(flux_val, color='white', linestyle='--', linewidth=1, alpha=0.7)
        for ax in axes_right[:-1]:
            plt.setp(ax.get_xticklabels(), visible=False)
            ax.set_xlabel('')
        fig.tight_layout()
        fig.savefig(parent + '/QubitFluxSpec.png')
        #
        if self._print_file_path:
            print(r"File: {}".format(parent) + r"/{}.h5".format(self._qubit_id))
            