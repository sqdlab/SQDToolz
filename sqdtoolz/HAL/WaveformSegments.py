import numpy as np

class WaveformSegmentBase:
    def __init__(self, name, mod_func):
        self._name = name
        self._mod_func = mod_func

    @property
    def Name(self):
        return self._name

    def NumPts(self, fs):
        return self.Duration*fs

    def get_waveform(self, fs, t0, ch_index):
        cur_wfm = self._get_waveform(fs, t0, ch_index)
        if self._mod_func:
            return self._mod_func.modify_waveform(cur_wfm, fs, t0, ch_index)
        else:
            return cur_wfm

    def _get_waveform(self, fs, t0, ch_index):
        assert False, "Waveform Segment classes must implement a get_waveform function."

    def _get_current_config(self):
        '''
        Gets the current JSON-style configuration that can be used to reinstantiate this class. Note that the inherited
        daughter class should override and call this class and should implement the key 'type' along with other keys that
        can be used to reinstantiate the daughter class.
        '''
        cur_dict = {}
        cur_dict['Name'] = self.Name
        if self._mod_func == None:
            cur_dict['Mod Func'] = ''
        else:
            cur_dict['Mod Func'] = self._mod_func.Name
        return cur_dict

    def _set_base_config(self, config_dict):
        '''
        Sets the name and modulation function as appropriate. Daughter classes should call this in their @classmethod fromConfigDict.
        '''
        for cur_key in ["Name", "Mod Func"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        

class WFS_Constant(WaveformSegmentBase):
    def __init__(self, name, mod_func, time_len, value=0.0):
        super().__init__(name, mod_func)
        self._duration = time_len
        self._value = value

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['type'] == 'WFS_Constant', "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Value"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        #TODO: Fix the functionality here.
        return cls(config_dict["Name"], config_dict["Duration"], config_dict["Value"])

    @property
    def Duration(self):
        return self._duration
    @Duration.setter
    def Duration(self, len_seconds):
        self._duration = len_seconds

    def _get_waveform(self, fs, t0, ch_index):
        return np.zeros(round(self.NumPts(fs))) + self._value

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['type'] = 'WFS_Constant'
        cur_dict['type'] = 'WFS_Constant'
        cur_dict['Duration'] = self._duration
        cur_dict['Value'] = self._value
        return cur_dict

class WFS_Gaussian(WaveformSegmentBase):
    def __init__(self, name, mod_func, time_len, amplitude, num_sd=1.96):
        super().__init__(name, mod_func)
        #TODO: Add in a classmethod to use sigma and truncate...
        self._duration = time_len
        self._amplitude = amplitude
        self._num_sd = num_sd

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['type'] == 'WFS_Gaussian', "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Amplitude", "Num SD"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key

        return cls(config_dict["Name"], config_dict["Duration"], config_dict["Amplitude"], config_dict["Num SD"])
   
    @property
    def Duration(self):
        return self._duration
    @Duration.setter
    def Duration(self, len_seconds):
        self._duration = len_seconds

    def _gauss(x):
        return np.exp(-x*x / (2*self._sigma*self._sigma))

    def _get_waveform(self, fs, t0, ch_index):
        n = self.NumPts(fs)
        #Generate the sample points on the Gaussian (start and end points are the same)
        sample_points = np.linspace(-self._num_sd, self._num_sd, int(np.round(n)))
        #Now calculate the Gaussian along the sample points
        sample_points = np.exp(-sample_points*sample_points/2)
        #Now shift the end points such that they are at zero
        end_points = sample_points[0]
        sample_points = sample_points - end_points
        #Now normalise the height such that it is unity once more...
        sample_points = sample_points / (1-end_points)
        #Make the height the desired amplitude...
        return self._amplitude * sample_points

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['type'] = 'WFS_Gaussian'
        cur_dict['Duration'] = self._duration
        cur_dict['Amplitude'] = self._amplitude
        cur_dict['Num SD'] = self._num_sd
        return cur_dict
