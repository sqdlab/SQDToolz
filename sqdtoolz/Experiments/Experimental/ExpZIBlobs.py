from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from laboneq_applications.experiments import iq_blobs
import numpy as np
from sqdtoolz.Utilities.DataIQDiscriminate import DataIQDiscriminate

class ExpZIBlobs(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
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

    @staticmethod
    def plot_fitted_results(leDIQD:DataIQDiscriminate):
        fig, axs = plt.subplots(ncols=2, layout='constrained'); fig.set_figwidth(8)
        leDIQD.plot_points(axs[0])
        axs[0].set_box_aspect(1)
        leDIQD.plot_assignment_matrix(axs[1])
        axs[1].set_box_aspect(1)
        #
        fig.suptitle(f"Average Fidelity: {leDIQD.get_average_fidelity()*100:.4g}%", y=0.92)
        return fig
