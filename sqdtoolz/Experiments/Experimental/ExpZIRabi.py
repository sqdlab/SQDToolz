from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import amplitude_rabi

class ExpZIRabi(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)

        for q in np.asarray(qubit_ids):
            transition = kwargs.get('transition', 'ge')
            if transition=='ef' and hal_QPU.get_qubit_obj(q).DriveEFAmplitudeX > 1:
                print(f"Warning: Magnitude of 'DriveEFAmplitudeX' > 1 ({hal_QPU.get_qubit_obj(q).DriveEFAmplitudeX}), setting to 1.")
                hal_QPU.get_qubit_obj(q).DriveEFAmplitudeX = 1
                hal_QPU.get_qubit_obj(q).DriveEFAmplitudeXon2 = 0.5
            elif hal_QPU.get_qubit_obj(q).DriveGEAmplitudeX > 1:
                print(f"Warning: Magnitude of 'DriveGEAmplitudeX' > 1 ({hal_QPU.get_qubit_obj(q).DriveGEAmplitudeX}), setting to 1.")
                hal_QPU.get_qubit_obj(q).DriveGEAmplitudeX = 1
                hal_QPU.get_qubit_obj(q).DriveGEAmplitudeXon2 = 0.5

        super().__init__(name, expt_config, amplitude_rabi, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        for qubit_dataset in self._qubit_ids:          
            leData = self.retrieve_last_dataset(qubit_dataset)
            arr = leData.get_numpy_array()
            data_x = leData.param_vals[0]

            dfit = DFitSinusoid()
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
                dpkt = dfit.get_fitted_plot(data_x, data_y, 'Drive Amplitude', 'IQ Amplitude', dontplot=True)
                axs[1].legend([x for x in self._transition])
            else:
                data_y = np.sqrt(arr[:,0]**2 + arr[:,1]**2)
                dpkt = dfit.get_fitted_plot(data_x, data_y, 'Drive Amplitude', 'IQ Amplitude', dontplot=True)

            dpkt['fit_data'] = {'amplitude': dpkt['fit_data'], 'amplitude_raw': data_y}

            if self._update_params:
                if self._normalise_data:
                    #Find X and X/2 amplitudes...
                    n = np.ceil( dpkt['phase']/(2*np.pi) )
                    amp_X = ( 2*n*np.pi - dpkt['phase'] ) / ( 2*np.pi * dpkt['frequency'] )
                    amp_Xon2 = amp_X - 0.25 / dpkt['frequency']
                    dpkt['fit_data']['amp_X'] = amp_X
                    dpkt['fit_data']['amp_Xon2'] = amp_Xon2
                    dpkt['fit_data']['transition'] = self._transition
                cur_qubit = self._hal_QPU.get_qubit_obj(qubit_dataset)
                if self._transition == 'ge':
                    if self._normalise_data:
                        cur_qubit.DriveGEAmplitudeX = amp_X
                        cur_qubit.DriveGEAmplitudeXon2 = amp_Xon2
                    else:
                        cur_qubit.DriveGEAmplitudeX = 0.5/dpkt['frequency']
                        cur_qubit.DriveGEAmplitudeXon2 = 0.25/dpkt['frequency']
                else:
                    if self._normalise_data:
                        cur_qubit.DriveEFAmplitudeX = amp_X
                        cur_qubit.DriveEFAmplitudeXon2 = amp_Xon2
                    else:
                        cur_qubit.DriveEFAmplitudeX = 0.5/dpkt['frequency']
                        cur_qubit.DriveEFAmplitudeXon2 = 0.25/dpkt['frequency']

            if self._normalise_data:
                ExpZIRabi.plot_fitted_results(axs[0], data_x, data_y, dpkt['fit_data'], self._normalise_data)
            else:
                fig, ax = plt.subplots(1)
                ExpZIRabi.plot_fitted_results(ax, data_x, data_y, dpkt['fit_data'], self._normalise_data)

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
        ax.set_xlabel('Amplitude')
        if data_normalised:
            if fitted_results.get('transition','ge') == 'ge':
                ax.set_ylabel('Normalised e-Population')
            else:
                ax.set_ylabel('Normalised f-Population')
        else:
            ax.set_ylabel('|IQ|')
        ax.grid(visible=True, which='minor'); ax.grid(visible=True, which='major', color='k')
        ax.plot(data_x, data_y, 'kx')
        ax.plot(data_x, fitted_results['amplitude'], 'r-')

        #Plot X and X/2 points on plot...
        if 'amp_Xon2' in fitted_results:
            ax.plot([fitted_results['amp_Xon2'], fitted_results['amp_Xon2']], [0,1], '-b')
            ax.text(fitted_results['amp_Xon2'], 0.5, '$\pi/2$')
        if 'amp_X' in fitted_results:
            ax.plot([fitted_results['amp_X'], fitted_results['amp_X']], [0,1], '-b')
            ax.text(fitted_results['amp_X'], 0.5, '$\pi$')
