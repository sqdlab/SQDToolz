from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time

from sqdtoolz.Utilities.DataFitting import*
import scipy.optimize
from sqdtoolz.Utilities.FileIO import*

class ExpMixerCalibrationSB(Experiment):
    def __init__(self, name, expt_config, var_down_conv_freq, freq_SB_minimise, var_amp, range_amps, var_phs, range_phs, optimise=False, **kwargs):
        super().__init__(name, expt_config)
        self._var_down_conv_freq = var_down_conv_freq
        self._freq_SB_minimise = freq_SB_minimise
        self._var_amp = var_amp
        self._range_amps = range_amps
        self._var_phs = var_phs
        self._range_phs = range_phs
        self._iters = kwargs.get('iterations', 1)

        self._optimise = optimise
        self._opt_data = []
        self._accuracy = kwargs.get('accuracy', 0.0005)

    def _cost_func(self, amp_phs_vals):
        self._var_amp.Value = amp_phs_vals[0]
        self._var_phs.Value = amp_phs_vals[1]
        self._expt_config.prepare_instruments()
        smpl_data = self._expt_config.get_data()

        i_val, q_val = smpl_data['data']['ch0_I'], smpl_data['data']['ch0_Q']

        ampl = np.sqrt(i_val**2 + q_val**2)
        self._opt_data += [[amp_phs_vals[0], amp_phs_vals[1], ampl]]
        return ampl

    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot include sweeping variables in this experiment."
        self._expt_config.init_instruments()
        self._var_down_conv_freq.Value = self._freq_SB_minimise
        kwargs['skip_init_instruments'] = True

        if self._optimise:
            self._file_path = file_path
            #
            self._opt_ind = 0
            self._opt_data = []
            #
            #Due to a bug in Scipy...
            fprime = lambda x: scipy.optimize.approx_fprime(x, self._cost_func, self._accuracy)
            sol = scipy.optimize.minimize(self._cost_func, [self._var_amp.Value, self._var_phs.Value], jac=fprime, method='Newton-CG',
                                                    options={'xtol': self._accuracy, 'maxiter' : self._iters, 'eps' : self._accuracy})
            self._var_amp.Value, self._var_phs.Value = sol.x
            #
            data_opt = np.array(self._opt_data)
            final_data = {
                'data' : {
                    'ch_I' : data_opt[:,0],
                    'ch_Q' : data_opt[:,1],
                    'ch_ampl' : data_opt[:,2]
                },
                'parameters' : ['step']
            }
            data_file = FileIOWriter(file_path + 'data.h5')
            data_file.push_datapkt(final_data, [])
            data_file.close()
            return FileIOReader(file_path + 'data.h5')
        else:
            return super()._run(file_path, [(self._var_amp, np.linspace(self._range_amps[0], self._range_amps[1], 5)),
                                            (self._var_phs, np.linspace(self._range_phs[0], self._range_phs[1], 5))], **kwargs)

    def _post_process(self, data):
        if self._optimise:
            data_opt = data.get_numpy_array()
            #
            fig, ax = plt.subplots(1)
            ax.scatter(data_opt[:,0], data_opt[:,1], c=data_opt[:,2])
            ax.set_xlabel('Amplitude-Factor Q/I'); ax.set_ylabel('Phase-Difference')
            ax.grid(b=True, which='minor'); ax.grid(b=True, which='major', color='k')
            #
            fig.show()
            fig.savefig(self._file_path + 'fitted_plot.png')
        else:
            arr = data.get_numpy_array()
            data_amp = np.sqrt(arr[:,:,0]**2+arr[:,:,1]**2)

            dfit = DFitMinMax2D()
            dpkt = dfit.get_fitted_plot(data.param_vals[0], data.param_vals[1], data_amp, isMin=True, xLabel='Amplitude-Factor Q/I', yLabel='Phase-Difference')
            
            #Set the DC offsets to the minimum
            self._var_amp.Value, self._var_phs.Value = dpkt['extremum']

            return dpkt['fig']
