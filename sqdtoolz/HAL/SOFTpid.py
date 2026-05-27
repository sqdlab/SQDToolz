from sqdtoolz.HAL.HALbase import*
from sqdtoolz.Variable import VariableInternalTransient
from sqdtoolz.Utilities.FileIO import FileIODatalogger, FileIOReader
import time
import scipy.signal
import numpy as np

class SOFTpid(HALbase):
    def __init__(self, hal_name, lab, VAR_Measure, VAR_OutputSet, Kp, Ki, Kd, **kwargs):
        HALbase.__init__(self, hal_name)

        #These are transient properties that shouldn't be stored in the laboratory configurations - can be foudn in last experiment however...
        self._VAR_Measure = VAR_Measure
        self._VAR_OutputSet = VAR_OutputSet
        self._VAR_integral = VariableInternalTransient('integral_term', 0)
        self._VAR_deriv = VariableInternalTransient('deriv_term', 0)

        self._VAR_setpoint = VariableInternalTransient('SetPoint', Kp)
        self._VAR_Kp = VariableInternalTransient('Kp', Kp)
        self._VAR_Ki = VariableInternalTransient('Ki', Ki)
        self._VAR_Kd = VariableInternalTransient('Kd', Kd)

        self._output_min = kwargs.get('output_min', 0)
        self._output_max = kwargs.get('output_max', 1)
        self._filt_deriv_cutoff = kwargs.get('filt_deriv_cutoff', 0.1)
        self._filt_deriv_taps = kwargs.get('filt_deriv_taps', 50)

        self._data_file = None

        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        #TODO: This is severely wrong - it won't properly load/save configurations - fix this...
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def SetPoint(self):
        return self._VAR_setpoint.Value
    @SetPoint.setter
    def SetPoint(self, val):
        self._VAR_setpoint.Value = val

    @property
    def Kp(self):
        return self._VAR_Kp.Value
    @Kp.setter
    def Kp(self, val):
        self._VAR_Kp.Value = val

    @property
    def Ki(self):
        return self._VAR_Ki.Value
    @Ki.setter
    def Ki(self, val):
        self._VAR_Ki.Value = val

    @property
    def Kd(self):
        return self._VAR_Kd.Value
    @Kd.setter
    def Kd(self, val):
        self._VAR_Kd.Value = val

    @property
    def OutputMin(self):
        return self._output_min
    @OutputMin.setter
    def OutputMin(self, val):
        self._output_min = val

    @property
    def OutputMax(self):
        return self._output_max
    @OutputMax.setter
    def OutputMax(self, val):
        self._output_max = val

    @property
    def FilterDerivCutoff(self):
        return self._filt_deriv_cutoff
    @FilterDerivCutoff.setter
    def FilterDerivCutoff(self, val):
        self._filt_deriv_cutoff = val

    @property
    def FilterDerivTaps(self):
        return self._filt_deriv_taps
    @FilterDerivTaps.setter
    def FilterDerivTaps(self, val):
        self._filt_deriv_taps = val

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__
            }
        self.pack_properties_to_dict(['SetPoint', 'Kp', 'Ki', 'Kd', 'OutputMin', 'OutputMax', 'FilterDerivCutoff', 'FilterDerivTaps'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a SoPID with a configuration that is of type ' + dict_config['Type']
        # self.SetPoint = dict_config['SetPoint']
        self.Kp = dict_config['Kp']
        self.Ki = dict_config['Ki']
        self.Kd = dict_config['Kd']
        self.OutputMin = dict_config['OutputMin']
        self.OutputMax = dict_config['OutputMax']
        self.FilterDerivCutoff = dict_config['FilterDerivCutoff']
        self.FilterDerivTaps = dict_config['FilterDerivTaps']
        
        if 'data_file_path' in dict_config:
            #Setup PID data file
            data_file_index = dict_config.get('data_file_index', -1)
            if data_file_index >= 0:
                data_file_name = f'PID{self.Name}{data_file_index}.h5'
            else:
                data_file_name = f'PID{self.Name}.h5'
            self._data_file_name = dict_config['data_file_path'] + data_file_name
            self._data_file = FileIODatalogger(self._data_file_name, [self._VAR_setpoint, self._VAR_Measure, self._VAR_OutputSet, self._VAR_Kp, self._VAR_Ki, self._VAR_Kd, self._VAR_integral, self._VAR_deriv])
            self._integral = 0
            self._tempsMeas = []
            self.last_time = time.time()

    def activate(self):
        assert self._data_file != None, "Check the Experiment class or its derived class. It should run init_instruments to initialise the Software PID controller."

        cur_value = self._VAR_Measure.Value
        err = self.SetPoint - cur_value
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

    def deactivate(self):
        self._data_file.close()
        self._data_file = None
        self.last_pid_data = FileIOReader(self._data_file_name)
