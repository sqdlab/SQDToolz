from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import DFitSinusoid
from laboneq_applications.experiments import ramsey
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import numpy as np

class ExpZIRamsey(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False
        self._fit_vals = []
        self._detunings = np.array(kwargs['detunings'])
        super().__init__(name, expt_config, ramsey, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        self._fit_vals = []
        for ind_qubit, qubit_dataset in enumerate(self._qubit_ids):          
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

            dpkt['fit_data'] = {'amplitude': dpkt['fit_data'], 'amplitude_raw': data_y, 'T2*': 1.0/dpkt['decay_rate'], 'frequency': dpkt['frequency'], 'transition':self._transition}

            if self._normalise_data:
                ExpZIRamsey.plot_fitted_results(axs[0], data_x, data_y, qubit_dataset, dpkt['fit_data'], self._normalise_data)
            else:
                fig, ax = plt.subplots(1)
                ExpZIRamsey.plot_fitted_results(ax, data_x, data_y, qubit_dataset, dpkt['fit_data'], self._normalise_data)

            fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
            #
            if 'fit_data' in dpkt:
                np.save(self._file_path + f'fitted_data_{qubit_dataset}.npy', dpkt['fit_data'])
        
            #TODO: Generalise it for EF later
            self._fit_vals.append({'qubit_obj': self._hal_QPU.get_qubit_obj(qubit_dataset), 'Detuning':self._detunings[ind_qubit], 'GE_frequency_fit': dpkt['frequency'], 'T2star': 1.0/dpkt['decay_rate']})

    @staticmethod
    def plot_fitted_results(ax, data_x, data_y, q, fitted_results:dict, data_normalised:bool):
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
        ax.set_title(f"{q}: {cur_transition}-$T_2^*=${Miscellaneous.get_units(fitted_results['T2*'],4)}s")

    def update_qubits(self, assume_detuned_above=True, t2_only=False):
        assert len(self._fit_vals) > 0, "Must run Ramsey Experiment before qubits can be updated."
        while len(self._fit_vals) > 0:
            cur_fit = self._fit_vals.pop(0)
            if not t2_only:
                if assume_detuned_above:
                    if self._transition == 'ge':
                        cur_fit['qubit_obj'].DriveGE += cur_fit['Detuning']-cur_fit['GE_frequency_fit']
                    else:
                        cur_fit['qubit_obj'].DriveEF += cur_fit['Detuning']-cur_fit['GE_frequency_fit']
                else:
                    if self._transition == 'ge':
                        cur_fit['qubit_obj'].DriveGE += cur_fit['Detuning']+cur_fit['GE_frequency_fit']
                    else:
                        cur_fit['qubit_obj'].DriveEF += cur_fit['Detuning']+cur_fit['GE_frequency_fit']                        
                cur_fit['qubit_obj'].DriveGE = float(cur_fit['qubit_obj'].DriveGE)                        
                cur_fit['qubit_obj'].DriveEF = float(cur_fit['qubit_obj'].DriveEF)
            if self._transition == 'ge':
                cur_fit['qubit_obj'].T2GE_star = cur_fit['T2star']
            else:
                cur_fit['qubit_obj'].T2EF_star = cur_fit['T2star']
                
