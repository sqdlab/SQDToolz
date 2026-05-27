from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from sqdtoolz.Experiments.Experimental.ZI import single_qubit_gates_sweep
import scipy.optimize

class ExpZICalibX(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, calib_denominator=1, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False

        self._fit_vals = []

        assert calib_denominator in [1,2], "Either supply 'calib_denominator' with 1 or 2 for X or X/2 gate calibration"
        self._calib_denominator = calib_denominator

        num_gates = kwargs.pop('num_gates', 20)
        if calib_denominator == 2:
            kwargs['gate_lists']=[[['X/2']*n]*len(qubit_ids) for n in range(1,num_gates+1)]
        else:
            kwargs['gate_lists']=[[['X']*n]*len(qubit_ids) for n in range(1,num_gates+1)]
        self._n_vals = np.arange(1,num_gates+1)

        super().__init__(name, expt_config, single_qubit_gates_sweep, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        self._fit_vals = []
        for ind_qubit, qubit_dataset in enumerate(self._qubit_datasets):          
            leData = self.retrieve_last_dataset(qubit_dataset)
            arr = leData.get_numpy_array()
            data_x = leData.param_vals[0]

            assert self._normalise_data, "No point analysing this without normalised data..."
            #Get calibration data
            calib_file = qubit_dataset + '_calib'
            leDataCalib = self.retrieve_last_dataset(calib_file)
            dnorm = ExpZIqubit.normalise_qubit_data(leDataCalib, self._transition)
            pop_probs = dnorm.normalise_data(arr)

            n_vals = self._n_vals
            if self._calib_denominator == 2:
                def func(x):
                    return ( 1-(np.cos(n_vals * (1+x[0]/100)*np.pi/2 / 2))**2 -0.5 )*np.exp(-n_vals/(x[1]*100))+0.5
                fit_data = {'Gate': 'X/2'}
            elif self._calib_denominator == 1:
                def func(x):
                    return ( 1-(np.cos(n_vals * (1+x[0]/100)*np.pi / 2))**2 -0.5 )*np.exp(-n_vals/(x[1]*100))+0.5
                fit_data = {'Gate': 'X'}
            def cost_func(x):
                resid = pop_probs - func(x)
                return np.sum(resid**2)

            sol = scipy.optimize.minimize(cost_func, [0.0,2], bounds=((-10,10),(0.1,5)), method='Nelder-Mead')
            fit_data['Corr_Fac_Pct'] = sol.x[0]
            fit_data['Gate_Decay_per_100'] = sol.x[1]
            fit_data['Gate_Corr_Fac'] = float(1/(1+sol.x[0]/100))

            fig, ax = plt.subplots(1)
            ax.plot(data_x, pop_probs, 'o-')
            ax.plot(data_x, func(sol.x), 'ro')
            if self._calib_denominator == 2:
                ax.set_title(f"Actual X/2 angle: {(1+sol.x[0]/100) * 90}")
            else:
                ax.set_title(f"Actual X angle: {(1+sol.x[0]/100) * 180}")                
            ax.legend(['Raw', 'Fit'])

            fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
            #
            np.save(self._file_path + f'fitted_data_{qubit_dataset}.npy', fit_data)
        
            #TODO: Generalise it for EF later?
            self._fit_vals.append({'qubit_obj': self._hal_QPU.get_qubit_obj(qubit_dataset), 'Gate_Corr_Fac':fit_data['Gate_Corr_Fac']})

    def update_qubits(self):
        assert len(self._fit_vals) > 0, "Must run Ramsey Experiment before qubits can be updated."
        while len(self._fit_vals) > 0:
            cur_fit = self._fit_vals.pop(0)
            if self._calib_denominator == 2:
                cur_fit['qubit_obj'].DriveGEAmplitudeXon2 *= cur_fit['Gate_Corr_Fac']
            elif self._calib_denominator == 1:
                cur_fit['qubit_obj'].DriveGEAmplitudeX *= cur_fit['Gate_Corr_Fac']
