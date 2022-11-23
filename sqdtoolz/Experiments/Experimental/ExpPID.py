from sqdtoolz.Experiment import*
from sqdtoolz.ExperimentConfiguration import*
import numpy as np
import time
import scipy.signal

class ExpPID(Experiment):
    def __init__(self, expt, VAR_setpt, VAR_Measure, VAR_OutputSet, Kp, Ki, Kd, **kwargs):
        super().__init__('pid', expt._expt_config)

        if expt != None:
            self._expt = expt
        else:
            name = kwargs.get('Name', 'PID')
            assert 'expt_config' in kwargs, "Must provide an ExperimentConfiguration if expt is None."
            config = kwargs.get('expt_config')
            self._expt = Experiment(name, config)

        self._VAR_setpt = VAR_setpt
        self._VAR_Measure = VAR_Measure
        self._VAR_OutputSet = VAR_OutputSet

        self._VAR_Kp = VariableInternalTransient('Kp', Kp)
        self._VAR_Ki = VariableInternalTransient('Ki', Ki)
        self._VAR_Kd = VariableInternalTransient('Kd', Kd)
        self._VAR_integral = VariableInternalTransient('integral_term', 0)
        self._VAR_deriv = VariableInternalTransient('deriv_term', 0)

        self._output_min = kwargs.get('output_min', 0)
        self._output_max = kwargs.get('output_max', 1)
        self._filt_deriv_cutoff = kwargs.get('filt_deriv_cutoff', 0.1)
        self._filt_deriv_taps = kwargs.get('filt_deriv_taps', 50)

    def _run_PID(self):
        cur_value = self._VAR_Measure.Value
        err = self._VAR_setpt.Value - cur_value
        self._tempsMeas += [cur_value]

        #Calculate Integral
        dt = time.time() - self.last_time
        self.last_time = time.time()
        self._integral += self._VAR_Ki.Value * err * dt
        self._integral = np.clip(self._integral, self._output_min, self._output_max)
        self._VAR_integral.Value = self._integral

        #Calculate Derivative
        if len(self._tempsMeas) <= 1:
            deriv = 0
        else:
            cutoff = self._filt_deriv_cutoff
            sample_rate = 1.0 / dt
            taps = self._filt_deriv_taps
            #
            nyq_rate = sample_rate*0.5
            freq_cutoff_norm = cutoff/nyq_rate
            fir_coeffs = np.array(scipy.signal.firwin(taps, freq_cutoff_norm))
            #
            filtData = scipy.ndimage.convolve1d(self._tempsMeas[::], fir_coeffs)

            if filtData.size <= 1:
                deriv = 0
            else:
                deriv = self._VAR_Kd.Value * (filtData[-1]-filtData[-2]) / dt
        self._VAR_deriv.Value = deriv

        #Actuate PID
        set_val = np.clip(self._VAR_Kp.Value*(err) + self._integral + deriv, self._output_min, self._output_max)
        self._VAR_OutputSet.Value = set_val
        # print(set_val)

        self._data_file.push_data()


    def _run(self, file_path, sweep_vars=[], **kwargs):
        #Setup PID data file
        data_file_index = kwargs.get('data_file_index', -1)
        if data_file_index >= 0:
            data_file_name = f'pid{data_file_index}.h5'
        else:
            data_file_name = 'pid.h5'
        self._data_file = FileIODatalogger(file_path + data_file_name, [self._VAR_setpt, self._VAR_Measure, self._VAR_OutputSet, self._VAR_Kp, self._VAR_Ki, self._VAR_Kd, self._VAR_integral, self._VAR_deriv])

        kwargs['callback_iteration'] = lambda : self._run_PID()

        #Run main experiment - the configuration file should not contain the setting instrumentation!
        self._integral = 0
        self._tempsMeas = []
        self.last_time = time.time()
        res = self._expt._run(file_path, sweep_vars, **kwargs)

        self._data_file.close()
        self.last_pid_data = FileIOReader(file_path + data_file_name)

        return res
