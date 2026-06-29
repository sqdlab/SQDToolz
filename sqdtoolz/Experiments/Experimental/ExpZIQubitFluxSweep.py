from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ExpZIRes import ExpZIRes
from laboneq_applications.experiments import resonator_spectroscopy, qubit_spectroscopy
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
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
    
    def run(self, lab):
        var_flux = VariablePropertyTransient('Flux', self._hal_QPU.get_qubit_obj(self._qubit_id), 'FluxDC')
        lab.group_open(self._name)
        #
        fr = self._hal_QPU.get_qubit_obj(self._qubit_id).ReadoutFrequency
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
        flux_vals, freq_valsQ = dataQ.param_vals
        amplQ = np.sqrt(arrQ[:,:,0]**2 + arrQ[:,:,1]**2)
        arrR = dataR.get_numpy_array()
        freq_valsR = dataR.param_vals[1]
        amplR = np.sqrt(arrR[:,:,0]**2 + arrR[:,:,1]**2)
        #
        fig, axes = plt.subplots(ncols=2, sharey=True, figsize=(12,4)); 
        fig.suptitle(f"{self._qubit_id} flux sweep", fontsize=16)
        axes[0].pcolor(freq_valsQ, flux_vals, amplQ)
        axes[0].set_title('Qubit spectroscopy')
        axes[0].set_ylabel('Flux (V)')
        axes[0].set_xlabel('Frequency (Hz)')
        axes[1].pcolor(freq_valsR, flux_vals, amplR)
        axes[1].set_title('Resonator spectroscopy')
        axes[1].set_xlabel('Frequency (Hz)')
        fig.tight_layout()
        fig.savefig(str(Path(expQ._file_path).parent) + '/Overview.png')
        #
        fig, ax = plt.subplots(figsize=(8,6)); 
        ax.pcolor(freq_valsQ, flux_vals, amplQ)
        ax.set_title(f"{self._qubit_id} qubit spectroscopy")
        ax.set_ylabel('Flux (V)')
        ax.set_xlabel('Frequency (Hz)')
        fig.tight_layout()
        fig.savefig(str(Path(expQ._file_path).parent) + '/QubitFluxSpec.png')