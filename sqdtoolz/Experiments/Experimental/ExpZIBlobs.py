from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from laboneq_applications.experiments import iq_blobs
import numpy as np
from sqdtoolz.Utilities.DataIQDiscriminate import DataIQDiscriminate

class ExpZIBlobs(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        self._states = kwargs.get('states', "ge")
        self._iq_blob_data = {}
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. This is just a diagnostic experiment."
        kwargs['update'] = False
        # self._fit_vals = []
        self._leDIQDs = []
        super().__init__(name, expt_config, iq_blobs, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        self._leDIQDs = []
        for ind_qubit, qubit_dataset in enumerate(self._qubit_ids):
            calib_file = qubit_dataset + '_calib'
            leDataCalib = self.retrieve_last_dataset(calib_file)
            leDIQD = DataIQDiscriminate.fromZIcalibFileIOReader(leDataCalib)
            self._leDIQDs.append(leDIQD)
            #
            fig = ExpZIBlobs.plot_fitted_results(leDIQD)
            fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)

    def get_fidelities(self, average=True):
        assert len(self._leDIQDs) > 0, "Must run experiment first."
        if average:
            return np.array([x.get_average_fidelity() for x in self._leDIQDs])
        return np.array([x.get_fidelities() for x in self._leDIQDs])
    
    def optimal_fidelity(self):
        assert 'f' not in self._states, "f state not yet supported"
        for qubit in self._qubit_ids:     
            leData = self.retrieve_last_dataset(qubit + r'_calib')
            arr = leData.get_numpy_array()
            sweep_vals = leData.param_vals
            g_real = arr[..., 0]
            g_imag = arr[..., 1]
            e_real = arr[..., 2]
            e_imag = arr[..., 3]

            mean_g_real = np.mean(g_real, axis=-1)
            mean_g_imag = np.mean(g_imag, axis=-1)
            mean_e_real = np.mean(e_real, axis=-1)
            mean_e_imag = np.mean(e_imag, axis=-1)

            delta_real = mean_e_real - mean_g_real
            delta_imag = mean_e_imag - mean_g_imag
            
            d = np.sqrt(delta_real**2 + delta_imag**2)

            var_g = np.var(g_real, axis=-1) + np.var(g_imag, axis=-1)
            var_e = np.var(e_real, axis=-1) + np.var(e_imag, axis=-1)
            
            sigma = (np.sqrt(var_g) + np.sqrt(var_e)) / 2.0
            
            voltage_snr = d / (2.0 * sigma)
            power_snr = voltage_snr**2
            
            power_snr = np.where(power_snr <= 0, 1e-10, power_snr)
            snr_db = 10.0 * np.log10(power_snr)
            self._iq_blob_data[qubit] = snr_db


    @staticmethod
    def plot_fitted_results(leDIQD:DataIQDiscriminate, extra_title=''):
        fig, axs = plt.subplots(ncols=2, layout='constrained'); fig.set_figwidth(8)
        leDIQD.plot_points(axs[0])
        axs[0].set_box_aspect(1)
        leDIQD.plot_assignment_matrix(axs[1])
        axs[1].set_box_aspect(1)
        #
        fig.suptitle(f"Average Fidelity: {leDIQD.get_average_fidelity()*100:.4g}% {extra_title}", y=0.92)
        return fig
