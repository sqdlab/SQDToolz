from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import DFitExponential
from laboneq_applications.experiments import lifetime_measurement
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous

class ExpZIT1(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False
        self._fit_vals = []
        self._expect_rise = kwargs.pop('expect_rise', False)    #Only for unnormalised fitting
        super().__init__(name, expt_config, lifetime_measurement, hal_QPU, qubit_ids, **kwargs)

    def _post_process(self, data):
        self._fit_vals = []
        for qubit_dataset in self._qubit_ids:          
            leData = self.retrieve_last_dataset(qubit_dataset)
            arr = leData.get_numpy_array()
            data_x = leData.param_vals[0]

            dfit = DFitExponential()
            if self._normalise_data:
                #Get calibration data
                dnorm = ExpZIqubit.normalise_qubit_data(self.retrieve_last_dataset(qubit_dataset+'_calib'), self._transition)
                #
                fig, axs = plt.subplots(ncols=2, gridspec_kw={'width_ratios':[2,1]})
                fig.set_figheight(5); fig.set_figwidth(15)
                data_y = dnorm.normalise_data(arr, ax=axs[1])
                dpkt = dfit.get_fitted_plot(data_x, data_y, rise=False, dontplot=True)
                axs[1].legend([x for x in self._transition])
            else:
                data_y = np.sqrt(arr[:,0]**2 + arr[:,1]**2)
                dpkt = dfit.get_fitted_plot(data_x, data_y, rise=self._expect_rise, dontplot=True)

            dpkt['fit_data'] = {'amplitude': dpkt['fit_data'], 'amplitude_raw': data_y, 'T1': dpkt['decay_time'], 'qubit_name':qubit_dataset, 'transition':self._transition}

            if self._normalise_data:
                ExpZIT1.plot_fitted_results(axs[0], data_x, data_y, dpkt['fit_data'], self._normalise_data)
            else:
                fig, ax = plt.subplots(1)
                ExpZIT1.plot_fitted_results(ax, data_x, data_y, dpkt['fit_data'], self._normalise_data)
                ax.set_title(f"{qubit_dataset} T1: {Miscellaneous.get_units(dpkt['fit_data']['T1'],4)}s")

            fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
            #
            if 'fit_data' in dpkt:
                np.save(self._file_path + f'fitted_data_{qubit_dataset}.npy', dpkt['fit_data'])
            #TODO: Generalise it for EF later
            self._fit_vals.append({'qubit_obj': self._hal_QPU.get_qubit_obj(qubit_dataset), 'T1':dpkt['decay_time']})


    @staticmethod
    def plot_fitted_results(ax, data_x, data_y, fitted_results:dict, data_normalised:bool):
        cur_transition = fitted_results.get('transition','ge')
        if data_normalised:
            if cur_transition == 'ge':
                ax.set_ylabel('Normalised e-Population')
            else:
                ax.set_ylabel('Normalised f-Population')
        else:
            ax.set_ylabel('|IQ|')
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(data_x)
        ax.grid(visible=True, which='minor'); ax.grid(visible=True, which='major', color='k')
        ax.plot(data_x/norm_fac, data_y, 'kx')
        ax.plot(data_x/norm_fac, fitted_results['amplitude'], 'r-')
        ax.set_xlabel(f'Wait Times ({norm_prefix}s)')
        ax.set_title(f"{fitted_results['qubit_name']}: {cur_transition}-$T_1=${Miscellaneous.get_units(fitted_results['T1'],4)}s")

    def update_qubits(self):
        assert len(self._fit_vals) > 0, "Must run T1 Experiment before qubits can be updated."
        while len(self._fit_vals) > 0:
            cur_fit = self._fit_vals.pop(0)
            if self._transition == 'ge':
                cur_fit['qubit_obj'].T1GE = float(cur_fit['T1'])
            else:
                cur_fit['qubit_obj'].T1EF = float(cur_fit['T1'])
