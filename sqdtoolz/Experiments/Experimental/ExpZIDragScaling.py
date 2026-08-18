from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from laboneq_applications.experiments import drag_q_scaling

class ExpZIDragScaling(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._qubit_datasets = qubit_ids
        assert len(qubit_ids)==1, "Only provide one qubit."

        self._hal_QPU = hal_QPU
        self._q_scalings = kwargs.pop('q_scalings', [np.linspace(0.00, 0.05, 51)])

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        self._update_qubits = kwargs.pop('update', True)

        self._data = {}

        super().__init__(name, expt_config, drag_q_scaling, hal_QPU, qubit_ids, q_scalings=self._q_scalings, update=self._update_qubits, **kwargs)
    
    def _post_process(self, lab):
        for qubit_dataset in self._qubit_ids:
            if self._normalise_data:
                #Get calibration data
                dnorm = ExpZIqubit.normalise_qubit_data(self.retrieve_last_dataset(qubit_dataset+'_calib'), 'ge')
            #
            fig, ax = plt.subplots(1)
            fig.set_figheight(5); fig.set_figwidth(10)
            # data, arrs order: xx, xy, xmy
            data_y = {}
            for i in ['xx', 'xy', 'xmy']:
                leData = self.retrieve_last_dataset(qubit_dataset + f'_{i}')
                arr = leData.get_numpy_array()
                #
                data_x = leData.param_vals[0]
                if self._normalise_data:
                    data_y[i] = dnorm.normalise_data(arr, ax=ax)
                else:
                    data_y[i] = np.sqrt(arr[:,0]**2 + arr[:,1]**2)
                #
                m, c = np.polyfit(data_x, data_y[i], deg=1)
                data_y[f'{i}_fit'] = m*data_x + c

            self._data = data_y | {'beta': data_x} | {'qubit_name': qubit_dataset}

            if self._normalise_data:
                ExpZIDragScaling.plot_fitted_results(ax, self._data['beta'], self._data, self._normalise_data, qubit_dataset)
            else:
                ExpZIDragScaling.plot_fitted_results(ax, self._data['beta'], self._data, self._normalise_data, qubit_dataset)

            fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)

    @staticmethod
    def plot_fitted_results(ax, data_x, data:dict, data_normalised=True, qubit_name=None):
        assert {'xx', 'xy', 'xmy', 'xx_fit', 'xy_fit', 'xmy_fit'} <= data.keys()
        cs = {'xx': 'tab:blue', 'xy': 'tab:orange', 'xmy': 'tab:green'}
        for i in ['xx', 'xy', 'xmy']:
            ax.scatter(data_x, data[i], marker='x', color=cs[i], label=i)
            ax.plot(data_x, data[f'{i}_fit'], color=cs[i], linestyle='-')
        
        fit_stack = np.array([data[f'{i}_fit'] for i in ['xx', 'xy', 'xmy']])  # shape (3, N)
        spread = fit_stack.max(axis=0) - fit_stack.min(axis=0)  # or use np.std(fit_stack, axis=0)
        best_idx = np.argmin(spread)
        best_x = data_x[best_idx]
        best_y = fit_stack[:, best_idx].mean()  # average of the three fit values there

        ax.plot(best_x, best_y, marker='o', color='black', markersize=8, zorder=5)

        if data_normalised:
            ax.set_ylabel(r'Normalised $e$-Population')
        else:
            ax.set_ylabel('|IQ|')
        ax.grid(visible=True, which='minor')
        ax.grid(visible=True, which='major', color='k')
        ax.set_xlabel(r'DRAG Quadrature Scaling Factor, $\beta$')
        if qubit_name:
            ax.set_title(fr"{qubit_name}: DRAG scaling ($\beta={best_x}$)")
        elif data.get('qubit_name'):
            ax.set_title(fr"{data['qubit_name']}: DRAG scaling ($\beta={best_x}$)")
        else:
            ax.set_title(fr"DRAG scaling ($\beta={best_x}$)")
        ax.legend()
            

