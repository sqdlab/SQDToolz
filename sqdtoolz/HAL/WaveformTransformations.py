import numpy as np
from sqdtoolz.HAL.LockableProperties import LockableProperties
class WaveformTransformationArgs:
    def __init__(self, wfmt_name, kwargs):
        self.wfmt_name = wfmt_name
        self._kwargs = []
        for cur_kwarg in kwargs:
            self._kwargs += [cur_kwarg]
            setattr(self, cur_kwarg, kwargs[cur_kwarg])

    @property
    def Name(self):
        return self.wfmt_name
    
    @property
    def kwargs(self):
        ret_dict = {}
        for cur_kwarg in self._kwargs:
            ret_dict[cur_kwarg] = getattr(self, cur_kwarg)
        return ret_dict

class WaveformTransformation(LockableProperties):
    def __init__(self, name):
        self._name = name

    def __new__(cls, *args, **kwargs):
        if len(args) == 0:
            name = kwargs.get('name', '')
            if name == '':
                name = kwargs.get('Name', '')
        else:
            name = args[0]
        assert isinstance(name, str) and name != '', "Name parameter was not passed or does not exist as the first argument in the variable class initialisation?"
        if len(args) < 2:
            lab = kwargs.get('lab', None)
            if lab == None:
                lab = kwargs.get('Lab', None)
        else:
            lab = args[1]
        assert lab.__class__.__name__ == 'Laboratory' and lab != None, "Lab parameter was not passed or does not exist as the second argument in the variable class initialisation?"

        prev_exists = lab.WFMT(name, True)
        if prev_exists:
            assert isinstance(prev_exists, cls), f"A different WFMT type ({prev_exists.__class__.__name__}) already exists by this name."
            return prev_exists
        else:
            return super(cls.__class__, cls).__new__(cls)
    
    def apply(self, **kwargs):
        self._process_kwargs(kwargs)
        return WaveformTransformationArgs(self.Name, kwargs)

    @property
    def Name(self):
        return self._name

    @property
    def Parent(self):
        return None
    
    def copy_settings(self, otherObj):
        assert otherObj.__class__.__name__ == self.__class__.__name__, f"Other WFMT must be of the same type as the current one (i.e. {self.__class__.__name__}) to copy over the settings."
        other_settings = otherObj._get_current_config()
        other_settings['Name'] = self.Name
        self._set_current_config(other_settings)

    def initialise_for_new_waveform(self):
        raise NotImplementedError()

    def modify_waveform(self, wfm_pts, fs, t0_ind, ch_index, **kwargs):
        raise NotImplementedError()

    def __str__(self):
        cur_dict = self._get_current_config()
        cur_str = ""
        for cur_key in cur_dict:
            cur_str += f"{cur_key}: {cur_dict[cur_key]}\n"
        return cur_str

    def _get_current_config(self):
        raise NotImplementedError()

    def _set_current_config(self, dict_config, instr_obj = None):
        raise NotImplementedError()
    
    def _process_kwargs(self, kwargs):
        raise NotImplementedError()

class WFMT_ModulationIQ(WaveformTransformation):
    def __init__(self, name, lab, iq_frequency, **kwargs):
        super().__init__(name)
        if lab._register_WFMT(self):
            self._iq_frequency = iq_frequency
            self._iq_amplitude = kwargs.get('iq_amplitude', 1.0)   #Given as the raw output voltage (should usually set the envelopes to unity amplitude in this case)
            self._iq_amplitude_factor = kwargs.get('iq_amplitude_factor', 1.0)    #Defined as a = Q/I amplitudes and the factor 'a' is multiplied onto the Q-channel waveform 
            self._iq_phase_offset = kwargs.get('iq_phase_offset', 0.0)            #Defined as the phase to add to the Q (sine) term
            self._iq_dc_offsets = kwargs.get('iq_dc_offsets', (0.0, 0.0))       
            self._iq_upper_sb = kwargs.get('iq_upper_sb', True)
            self._cur_t0 = 0.0
        else:
            self._iq_frequency = iq_frequency
            self._iq_amplitude = kwargs.get('iq_amplitude', self._iq_amplitude)   #Given as the raw output voltage (should usually set the envelopes to unity amplitude in this case)
            self._iq_amplitude_factor = kwargs.get('iq_amplitude_factor', self._iq_amplitude_factor)    #Defined as a = Q/I amplitudes and the factor 'a' is multiplied onto the Q-channel waveform 
            self._iq_phase_offset = kwargs.get('iq_phase_offset', self._iq_phase_offset)            #Defined as the phase to add to the Q (sine) term
            self._iq_dc_offsets = kwargs.get('iq_dc_offsets', self._iq_dc_offsets)       
            self._iq_upper_sb = kwargs.get('iq_upper_sb', self._iq_upper_sb)
            self._cur_t0 = 0.0

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["IQ Frequency"], iq_amplitude = config_dict["IQ Amplitude"], iq_amplitude_factor = config_dict["IQ Amplitude Factor"],
                              iq_phase_offset = config_dict["IQ Phase Offset"], iq_dc_offsets = tuple(config_dict["IQ DC Offset"]), iq_upper_sb = config_dict["IQ using Upper Sideband"])

    @property
    def IQFrequency(self):
        return self._iq_frequency
    @IQFrequency.setter
    def IQFrequency(self, val: float):
        self._iq_frequency = val

    @property
    def IQAmplitude(self):
        return self._iq_amplitude
    @IQAmplitude.setter
    def IQAmplitude(self, val: float):
        self._iq_amplitude = val

    @property
    def IQAmplitudeFactor(self):
        return self._iq_amplitude_factor
    @IQAmplitudeFactor.setter
    def IQAmplitudeFactor(self, val: float):
        self._iq_amplitude_factor = val

    @property
    def IQPhaseOffset(self):
        return self._iq_phase_offset
    @IQPhaseOffset.setter
    def IQPhaseOffset(self, val: float):
        self._iq_phase_offset = val

    @property
    def IQdcOffset(self):
        return self._iq_dc_offsets
    @IQdcOffset.setter
    def IQdcOffset(self, val: float):
        assert type(val) is tuple, "IQ DC offset must be given as a tuple."
        self._iq_dc_offsets = val

    @property
    def IQUpperSideband(self):
        return self._iq_upper_sb
    @IQUpperSideband.setter
    def IQUpperSideband(self, boolVal: bool):
        self._iq_upper_sb = boolVal

    def set_IQ_parameters(self, amp = 1.0, dc_offset = (0.0, 0.0), amplitude_factor = 1.0, phase_offset = 0.0):
        self.IQAmplitude = amp
        self.IQdcOffset = dc_offset
        self.IQAmplitudeFactor = amplitude_factor
        self.IQPhaseOffset = phase_offset        

    def initialise_for_new_waveform(self):
        self._cur_t0 = 0.0

    def modify_waveform(self, wfm_pts: np.ndarray, fs: float, t0_ind: float, ch_index: int, **kwargs):
        t0 = t0_ind / fs

        cur_t_off = 0.0
        if 'phase' in kwargs:
            if self.IQUpperSideband:
                self._cur_t0 = t0 + kwargs.get('phase') / (2*np.pi*self.IQFrequency)
            else:
                self._cur_t0 = t0 - kwargs.get('phase') / (2*np.pi*self.IQFrequency)
        elif 'phase_offset' in kwargs:
            if self.IQUpperSideband:
                self._cur_t0 += kwargs.get('phase_offset') / (2*np.pi*self.IQFrequency)
            else:
                self._cur_t0 -= kwargs.get('phase_offset') / (2*np.pi*self.IQFrequency)
        if 'phase_segment' in kwargs:
            if self.IQUpperSideband:
                cur_t_off = kwargs.get('phase_segment') / (2*np.pi*self.IQFrequency)
            else:
                cur_t_off = -kwargs.get('phase_segment') / (2*np.pi*self.IQFrequency)

        t_vals = np.arange(wfm_pts.size) / fs + t0 - self._cur_t0 - cur_t_off
        if ch_index == 0:   #I-Channel
            return wfm_pts * self.IQAmplitude * np.cos(2 * np.pi * self.IQFrequency * t_vals) + self.IQdcOffset[0]
        elif ch_index == 1: #Q-Channel
            return wfm_pts * self.IQAmplitude * self.IQAmplitudeFactor * np.sin(2 * np.pi * self.IQFrequency * t_vals + self.IQPhaseOffset) + self.IQdcOffset[1]
        else:
            assert False, "Channel Index must be 0 or 1 for I or Q respectively."

    def _get_current_config(self):
        ret_dict = {}
        ret_dict["Name"] = self.Name
        ret_dict["Type"] = self.__class__.__name__
        ret_dict["IQ Frequency"] = self._iq_frequency
        ret_dict["IQ Amplitude"] = self._iq_amplitude
        ret_dict["IQ Amplitude Factor"] = self._iq_amplitude_factor
        ret_dict["IQ Phase Offset"] = self._iq_phase_offset
        ret_dict["IQ DC Offset"] = self._iq_dc_offsets
        ret_dict["IQ using Upper Sideband"] = self._iq_upper_sb
        return ret_dict

    def _set_current_config(self, dict_config, instr_obj = None):
        assert dict_config['Type'] == self.__class__.__name__
        for cur_key in ["IQ Frequency", "IQ Amplitude", "IQ Amplitude Factor", "IQ Phase Offset", "IQ DC Offset", "IQ using Upper Sideband"]:
            assert cur_key in dict_config, "Configuration dictionary does not have the key: " + cur_key
        
        self._iq_frequency = dict_config["IQ Frequency"]
        self._iq_amplitude = dict_config["IQ Amplitude"]
        self._iq_amplitude_factor = dict_config["IQ Amplitude Factor"]
        self._iq_phase_offset = dict_config["IQ Phase Offset"]
        self._iq_dc_offsets = dict_config["IQ DC Offset"]
        self._iq_upper_sb  = dict_config["IQ using Upper Sideband"]
    
    def _process_kwargs(self, kwargs):
        kwargs['phase'] = kwargs.get('phase', None)
        kwargs['phase_offset'] = kwargs.get('phase_offset', None)
        kwargs['phase_segment'] = kwargs.get('phase_segment', None)
