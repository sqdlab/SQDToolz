from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import lifetime_measurement

class ExpZIT1(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)

        self._expect_rise = kwargs.pop('expect_rise', False)    #Only for unnormalised fitting

        super().__init__(name, expt_config, lifetime_measurement, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        for qubit_dataset in self._qubit_datasets:          
            leData = self.retrieve_last_dataset(qubit_dataset)
            arr = leData.get_numpy_array()
            data_x = leData.param_vals[0]

            dfit = DFitExponential()
            if self._normalise_data:
                #Get calibration data
                calib_file = qubit_dataset + '_calib'
                leDataCalib = self.retrieve_last_dataset(calib_file)
                arrCalib = leDataCalib.get_numpy_array()
                cur_state_inds0 = [m for m,x in enumerate(leDataCalib.dep_params) if x.startswith(self._transition[0])]
                cur_state_inds1 = [m for m,x in enumerate(leDataCalib.dep_params) if x.startswith(self._transition[1])]
                dnorm = DataIQNormalise(arrCalib[:,cur_state_inds0], arrCalib[:,cur_state_inds1])
                #
                fig, axs = plt.subplots(ncols=2, gridspec_kw={'width_ratios':[2,1]})
                fig.set_figheight(5); fig.set_figwidth(15)
                data_y = dnorm.normalise_data(arr, ax=axs[1])
                dpkt = dfit.get_fitted_plot(data_x, data_y, rise=False, dontplot=True)
            else:
                data_y = np.sqrt(arr[:,0]**2 + arr[:,1]**2)
                dpkt = dfit.get_fitted_plot(data_x, data_y, rise=self._expect_rise, dontplot=True)

            dpkt['fit_data'] = {'amplitude': dpkt['fit_data'], 'amplitude_raw': data_y, 'T1': dpkt['decay_time']}

            if self._normalise_data:
                ExpZIT1.plot_fitted_results(axs[0], data_x, data_y, dpkt['fit_data'], self._normalise_data)
            else:
                fig, ax = plt.subplots(1)
                ExpZIT1.plot_fitted_results(ax, data_x, data_y, dpkt['fit_data'], self._normalise_data)

            fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
            #
            if 'fit_data' in dpkt:
                np.save(self._file_path + f'fitted_data_{qubit_dataset}.npy', dpkt['fit_data'])

    @staticmethod
    def plot_fitted_results(ax, data_x, data_y, fitted_results:dict, data_normalised:bool):
        if data_normalised:
            ax.set_ylabel('Normalised Population')
        else:
            ax.set_ylabel('|IQ|')
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(data_x)
        ax.grid(visible=True, which='minor'); ax.grid(visible=True, which='major', color='k')
        ax.plot(data_x/norm_fac, data_y, 'kx')
        ax.plot(data_x/norm_fac, fitted_results['amplitude'], 'r-')
        ax.set_xlabel(f'Wait Times ({norm_prefix}s)')
