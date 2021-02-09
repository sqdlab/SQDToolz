import numpy as np

class WaveformSegmentBase:
    def __init__(self, name):
        self._name = name

    @property
    def Name(self):
        return self._name

    def NumPts(self, fs):
        return self.Duration*fs

    def _get_current_config(self):
        assert False, "Waveform Segment classes must implement a _get_current_config function."

class WFS_Constant(WaveformSegmentBase):
    def __init__(self, name, time_len, value=0.0):
        super().__init__(name)
        self._duration = time_len
        self._value = value

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['type'] == 'WFS_Constant', "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Value"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key

        return cls(config_dict["Name"], config_dict["Duration"], config_dict["Value"])

    @property
    def Duration(self):
        return self._duration
    @Duration.setter
    def Duration(self, len_seconds):
        self._duration = len_seconds

    def get_waveform(self, fs):
        return np.zeros(round(self.NumPts(fs))) + self._value

    def _get_current_config(self):
        return {
            'type' : 'WFS_Constant',
            'Name' : self.Name,
            'Duration' : self._duration,
            'Value' : self._value
            }

class WFS_Gaussian(WaveformSegmentBase):
    def __init__(self, name, time_len, amplitude, num_sd=1.96):
        super().__init__(name)
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

    def get_waveform(self, fs):
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
        return {
            'type' : 'WFS_Gaussian',
            'Name' : self.Name,
            'Duration' : self._duration,
            'Amplitude' : self._amplitude,
            'Num SD' : self._num_sd
            }
