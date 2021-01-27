import numpy as np

class WaveformSegment:
    def __init__(self, name):
        self._name = name

    @property
    def Name(self):
        return Name

    @property
    def NumPts(self, fs):
        return self.get_duration()*fs

class WFS_Constant(WaveformSegment):
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
        return np.zeros(round(self.NumPts))    

class WFS_Gaussian(WaveformSegment):
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
        n = self.NumPts
        #Generate the sample points on the Gaussian (start and end points are the same)
        sample_points = np.linspace(-num_sd, num_sd, n)
        #Now calculate the Gaussian along the sample points
        sample_points = np.exp(-sample_points*sample_points/2)
        #Now shift the end points such that they are at zero
        end_points = sample_points[0]
        sample_points = sample_points - end_points
        #Now normalise the height such that it is unity once more...
        sample_points = sample_points / (1-end_points)
        #Make the height the desired amplitude...
        return self._amplitude * sample_points

class WaveformAWG:
    def __init__(self, awg_channel_list, sample_rate, global_factor = 1):
        self._awg_chan_list = awg_channel_list
        self._sample_rate = sample_rate
        self._global_factor = global_factor
        self._wfm_segment_list = []



    def add_waveform_segment(self, wfm_segment):
        self._wfm_segment_list.append(wfm_segment)

    def get_trigger_output(self, outputID = None):
        '''
        Returns a TriggerSource object.
        '''
        return self._MkrTrigger

    @property
    def Duration(self):
        full_len = 0
        for cur_seg in self._wfm_segment_list:
            full_len += cur_seg.Duration
        return full_len

    @property
    def NumPts(self):
        return self.Duration * self._sample_rate

    def _get_index_points_for_segment(self, seg_name):
        the_seg = None
        cur_ind = 0
        for cur_seg in self._wfm_segment_list:
            if cur_seg.name == seg_name:
                the_seg == seg_name
                break
            cur_ind += cur_seg.NumPts
        assert the_seg != None, "Waveform Segment of name " + seg_name + " is not present in the current list of added Waveform Segments."
        return (cur_ind, cur_ind + cur_seg.NumPts - 1)

    def _assemble_waveform_raw(self):
        #Concatenate the individual waveform segments
        final_wfm = np.array([])
        for cur_wfm_seg in self._wfm_segment_list:
            #TODO: Preallocate - this is a bit inefficient...
            final_wfm = np.concatenate(final_wfm, cur_wfm_seg.get_waveform())
        #Scale the waveform via the global scale-factor...
        final_wfm *= self._global_factor
        return final_wfm

    def program_AWG(self):
        #Prepare the waveform
        final_wfm = self._assemble_waveform_raw()
        for cur_awg_chan in self._awg_chan_list:
            cur_awg_chan.Parent.program_channel(cur_awg_chan.name, final_wfm)


        


    
