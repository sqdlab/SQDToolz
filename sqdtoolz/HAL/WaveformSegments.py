import numpy as np

class WaveformSegmentBase:
    def __init__(self, name):
        self._name = name

    @property
    def Name(self):
        return self._name

    def NumPts(self, fs):
        return self.Duration*fs

class WFS_Constant(WaveformSegmentBase):
    def __init__(self, name, time_len, value=0.0):
        super().__init__(name)
        self._duration = time_len
        self._value = value
   
    @property
    def Duration(self):
        return self._duration
    @Duration.setter
    def Duration(self, len_seconds):
        self._duration = len_seconds

    def get_waveform(self, fs):
        return np.zeros(round(self.NumPts(fs))) + self._value

class WFS_Gaussian(WaveformSegmentBase):
    def __init__(self, name, time_len, amplitude, num_sd=1.96):
        super().__init__(name)
        #TODO: Add in a classmethod to use sigma and truncate...
        self._duration = time_len
        self._amplitude = amplitude
        self._num_sd = num_sd
   
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
