from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import amplitude_rabi

class ExpZIRabi(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.get('dont_show_plot', False)

        super().__init__(name, expt_config, amplitude_rabi, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        for qubit_dataset in self._qubit_datasets:
            #Get calibration data
            calib_file = qubit_dataset + '_calib'
            arr = self.retrieve_last_dataset(calib_file).get_numpy_array()
            cur_state_inds0 = [m for m,x in enumerate(self.retrieve_last_dataset(calib_file).dep_params) if x.startswith(self._transition[0])]
            cur_state_inds1 = [m for m,x in enumerate(self.retrieve_last_dataset(calib_file).dep_params) if x.startswith(self._transition[1])]
            dnorm = DataIQNormalise(arr[:,cur_state_inds0], arr[:,cur_state_inds1])

            
            arr = self.retrieve_last_dataset(qubit_dataset).get_numpy_array()
            data_x = self.retrieve_last_dataset(qubit_dataset).param_vals[0]

            dfit = DFitSinusoid()
            if self._normalise_data:
                fig, axs = plt.subplots(ncols=2, gridspec_kw={'width_ratios':[2,1]})
                fig.set_figheight(5); fig.set_figwidth(15)
                data_y = dnorm.normalise_data(arr, ax=axs[1])

                dpkt = dfit.get_fitted_plot(data_x, data_y, 'Drive Amplitude', 'IQ Amplitude', axs[0])
                axs[0].set_xlabel('Amplitude'); axs[0].set_ylabel('Normalised Population')
                axs[0].grid(visible=True, which='minor'); axs[0].grid(visible=True, which='major', color='k');
            else:
                data_y = np.sqrt(arr[:,0]**2 + arr[:,1]**2)
                dpkt = dfit.get_fitted_plot(data_x, data_y, 'Drive Amplitude', 'IQ Amplitude')

            if self._update_params:
                if self._transition == 'ge':
                    if self._normalise_data:
                        #Find X and X/2 amplitudes...
                        n = np.ceil( dpkt['phase']/(2*np.pi) )
                        amp_X = ( 2*n*np.pi - dpkt['phase'] ) / ( 2*np.pi * dpkt['frequency'] )
                        amp_Xon2 = amp_X - 0.25 / dpkt['frequency']

                        #Plot X and X/2 points on plot...
                        axs[0].plot([amp_Xon2, amp_Xon2], [0,1], '-b')
                        axs[0].plot([amp_X, amp_X], [0,1], '-b')
                        axs[0].text(amp_Xon2, 0.5, '$\pi/2$')
                        axs[0].text(amp_X, 0.5, '$\pi$')

                        cur_qubit = self._hal_QPU.get_qubit_obj(qubit_dataset)
                        cur_qubit.DriveGEAmplitudeX = amp_X
                        cur_qubit.DriveGEAmplitudeXon2 = amp_Xon2
                    else:
                        cur_qubit.DriveGEAmplitudeX = 0.5/dpkt['frequency']
                        cur_qubit.DriveGEAmplitudeXon2 = 0.25/dpkt['frequency']
                else:
                    assert False, 'Ask Developer about the EF :P'
                    self._SPEC_qubit['EF X-Gate Amplitude'].Value = 0.5/dpkt['frequency']
                    self._SPEC_qubit['EF X-Gate Time'].Value = self.drive_time
                    self._SPEC_qubit['EF X-Gate Amplitude'].Value = 0.25/dpkt['frequency']
                    self._SPEC_qubit['EF X-Gate Time'].Value = self.drive_time

            if self._normalise_data:
                if not self._dont_show_plot:
                    fig.show()
                fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            else:
                if not self._dont_show_plot:
                    dpkt['fig'].show()
                    dpkt['fig'].savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
