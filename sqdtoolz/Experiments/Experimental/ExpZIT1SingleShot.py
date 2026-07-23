from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import DFitExponential
from laboneq_applications.experiments import lifetime_measurement
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import numpy as np

class ExpZIT1SingleShot(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False
        self._fit_vals = []
        self._expect_rise = kwargs.pop('expect_rise', False)    #Only for unnormalised fitting
        super().__init__(name, expt_config, lifetime_measurement, hal_QPU, qubit_ids, **kwargs)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        kwargs['override_ACQ_params'] = {'AveragingOrder': "SingleShot", 'AcquisitionMode': "DISCRIMINATION"}
        return super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        self._fit_vals = []
        for qubit_dataset in self._qubit_ids:
            leData = self.retrieve_last_dataset(qubit_dataset)
            arr = leData.get_numpy_array()
            #For each time-point get the number of 0s/1s/2s (i.e. counts for states g, e and f respectively)
            statz = np.zeros((arr.shape[1],3))
            for m in range(arr.shape[1]):
                counts = np.bincount(np.array(arr[:,m,0], dtype=np.int64), minlength=3)
                statz[m] = counts/arr.shape[0]
            times = leData.param_vals[1]
            #
            fig, ax = plt.subplots(1)
            norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(times)
            ax.plot(times/norm_fac, statz[:,0])
            ax.plot(times/norm_fac, statz[:,1])
            ax.plot(times/norm_fac, statz[:,2])
            ax.legend(['G','E','F'])
            ax.set_xlabel(f'Wait Times ({norm_prefix}s)')
            ax.set_ylabel(f'Population')
            if self._transition == 'ef':
                ax.set_title('Initialising F')
            elif self._transition == 'ge':
                ax.set_title('Initialising E')

            # TODO: fit T1 to f state

            fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
