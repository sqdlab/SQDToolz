from optparse import AmbiguousOptionError
import numpy as np
from sqdtoolz.HAL.WaveformTransformations import*
from sqdtoolz.HAL.HALbase import LockableProperties

class WaveformSegmentBase(LockableProperties):
    def __init__(self, name, transform_func, duration):
        self._name = name
        if transform_func:
            assert isinstance(transform_func, WaveformTransformationArgs), "Transformation function specified incorrectly - remember to call apply() on the WFMT object..."
            transform_func.Parent = (self, 'wt')
        self._transform_func = transform_func
        self._duration = duration

    @property
    def Name(self):
        return self._name

    def NumPts(self, fs):
        return int(np.round(self.Duration*fs))

    @property
    def Duration(self):
        return self._duration
    @Duration.setter
    def Duration(self, len_seconds):
        self._duration = len_seconds

    def _get_child(self, tuple_name_group):
        cur_name, cur_type = tuple_name_group
        if cur_type == 'wt':
            for cur_wfmt in [self._transform_func]:
                if cur_wfmt.Name == cur_name:
                    return cur_wfmt
        return None

    def get_WFMT(self):
        return self._transform_func

    def reset_waveform_transforms(self, lab):
        if self._transform_func:
            return lab.WFMT(self._transform_func.wfmt_name).initialise_for_new_waveform()

    def get_waveform(self, lab, fs, t0_ind, ch_index):
        '''
        Returns the final waveform; that is, after applying the modification function.

        Inputs:
            - fs - Sample Rate in Hertz
            - t0_ind - Initial time (useful when the actual time in the waveform is important like with the phase of sinusoidal
                   modulation or perhaps a continual ramp/waveform that is to continue rather than resetting back to zero).
                   Note that t0 is given as the point index (0 for t=0 being the first point of the entire waveform).
            - ch_index - Dimension/index of the waveform; useful when the modification function is a function of dimnension
                         in ND waveforms.
        
        Returns a numpy array of points representing the total waveform.
        '''
        cur_wfm = self._get_waveform(lab, fs, t0_ind, ch_index)
        #Transform if necessary:      
        if self._transform_func:
            kwargs = self._transform_func.kwargs
            none_keys = []
            for cur_key in kwargs:
                if kwargs[cur_key] == None:
                    none_keys += [cur_key]
            for cur_none_key in none_keys:
                kwargs.pop(cur_none_key)
            return lab.WFMT(self._transform_func.wfmt_name).modify_waveform(cur_wfm, fs, t0_ind, ch_index, **kwargs)
        else:
            return cur_wfm

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
        raise NotImplementedError()

    def _get_current_config(self):
        '''
        Gets the current JSON-style configuration that can be used to reinstantiate this class. Note that the inherited
        daughter class should override and call this class and should implement the key 'type' along with other keys that
        can be used to reinstantiate the daughter class.
        '''
        cur_dict = {}
        cur_dict['Name'] = self.Name
        cur_dict['Type'] = self.__class__.__name__
        if self._transform_func == None:
            cur_dict['Mod Func'] = {'Name' : '', 'Args' : ''}
        else:
            cur_dict['Mod Func'] = {'Name' : self._transform_func.wfmt_name, 'Args' : self._transform_func.kwargs}
        return cur_dict
    
    def _get_marker_waveform_from_segments(self, segments):
        assert False, "This waveform segment does not have children to index on markers."

class WFS_Group(WaveformSegmentBase):
    def __init__(self, name, wfm_segs, time_len=-1, num_repeats = 1, transform_func=None):
        #Check names are unique...
        cur_seg_names = []
        seg_names = [x.Name for x in wfm_segs]
        
        assert isinstance(num_repeats, int) and num_repeats >= 0, "The parameter num_repeats must be a non-negative integer."
        self._num_repeats = num_repeats

        for cur_name in seg_names:
            assert not cur_name in cur_seg_names, f"Waveform segments within a WFS_Group must be unique (more than one segment is named \'{cur_name}\')"
            cur_seg_names += [cur_name]
        
        super().__init__(name, transform_func, time_len)
        self._abs_time = time_len   #_abs_time is the total absolute time (if -1, the duration is the sum of the individual time segment durations)
        self._wfm_segs = wfm_segs
        self._validate_wfm_segs()

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "WaveformSegments"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        #TODO: Fix the functionality here.
        if config_dict['Mod Func']['Name'] == '':
            wfmt_obj = None
        else:
            wfmt_obj = WaveformTransformationArgs(config_dict['Mod Func']['Name'], config_dict['Mod Func']['Args'])
        #Compile inner waveforms
        cur_wfm_segs = []
        for cur_wfm in config_dict['WaveformSegments']:
            cur_wfm_type = cur_wfm['Type']
            assert cur_wfm_type in globals(), cur_wfm_type + " is not in the current namespace. If the class does not exist in WaveformSegments include wherever it lives by importing it in AWG.py."
            cur_wfm_type = globals()[cur_wfm_type]
            new_wfm_seg = cur_wfm_type.fromConfigDict(cur_wfm)
            new_wfm_seg.Parent = (cls, 'w')
            cur_wfm_segs.append(new_wfm_seg)
        num_repeats = config_dict.get('NumRepeats', 1)
        return cls(config_dict["Name"], cur_wfm_segs, config_dict["Duration"], num_repeats, wfmt_obj)

    @property
    def Duration(self):
        if self._abs_time == -1:
            return sum([x.Duration for x in self._wfm_segs]) * self._num_repeats
        else:
            return self._abs_time * self._num_repeats
    @Duration.setter
    def Duration(self, len_seconds):
        self._abs_time = len_seconds
    
    def NumPts(self, fs):
        #Over-riding due to a subtle issue due to sample rates and individual durations... For example:
        #   Duration of one unit = 4.5 => 5 samples
        #   Duration of two units = 9 - i.e. not 10...
        if self._abs_time == -1:
            cur_time_1 = sum([x.Duration for x in self._wfm_segs])
        else:
            cur_time_1 = self._abs_time
        return int(np.round(cur_time_1*fs)) * self._num_repeats

    @property
    def NumRepeats(self):
        return self._num_repeats
    @NumRepeats.setter
    def NumRepeats(self, const_val):
        self._num_repeats = const_val

    def get_waveform_segment(self, wfm_segment_name):
        the_seg = None
        for cur_seg in self._wfm_segs:
            if cur_seg.Name == wfm_segment_name:
                the_seg = cur_seg
                break
        assert the_seg != None, "Waveform Segment of name " + wfm_segment_name + " is not present in the list of Waveform Segments inside this WFS_Group segment."
        return the_seg

    def _get_marker_waveform_from_segments(self, segments, fs):
        #Temporarily set the Duration of Elastic time-segment...
        elas_seg_ind, elastic_time = self._validate_wfm_segs(fs)
        if elas_seg_ind != -1:
            self._wfm_segs[elas_seg_ind].Duration = elastic_time

        const_segs = []
        dict_segs = {}
        for cur_seg in segments:
            if type(cur_seg) == list:
                if len(cur_seg) == 0:
                    const_segs += [cur_seg] #TODO: Check if is an error condition to end up here?
                
                cur_queue = cur_seg[1:]
                if len(cur_queue) == 1:
                    cur_queue = cur_queue[0]
                
                if not cur_seg[0] in dict_segs:
                    dict_segs[cur_seg[0]] = [cur_queue]
                else:
                    dict_segs[cur_seg[0]] += [cur_queue]
            else:
                const_segs += [cur_seg]

        final_wfm = np.zeros(int(np.round(self.NumPts(fs))), dtype=np.ubyte)
        cur_ind = 0
        for m in range(self._num_repeats):
            for cur_seg in self._wfm_segs:
                cur_len = cur_seg.NumPts(fs)
                if cur_len == 0:
                    continue
                if cur_seg.Name in const_segs:
                    final_wfm[cur_ind:cur_ind+cur_len] = 1
                elif cur_seg.Name in dict_segs: #i.e. another segment with children like WFS_Group
                    final_wfm[cur_ind:cur_ind+cur_len] = cur_seg._get_marker_waveform_from_segments(dict_segs[cur_seg.Name], fs)
                cur_ind += cur_len
        
        #Reset segment to be elastic
        if elas_seg_ind != -1:
            self._wfm_segs[elas_seg_ind].Duration = -1
    
        return final_wfm

    def _validate_wfm_segs(self, fs=-1):
        elastic_segs = []
        for ind_wfm, cur_wfm_seg in enumerate(self._wfm_segs):
            if cur_wfm_seg.Duration == -1:
                elastic_segs += [ind_wfm]
        assert len(elastic_segs) <= 1, "There are too many elastic waveform segments (cannot be above 1)."
        if self._abs_time == -1:
            assert len(elastic_segs) == 0, "If the total waveform length is unbound, the number of elastic segments must be zero."
        if self._abs_time > 0 and len(elastic_segs) == 0:
            assert sum([x.Duration for x in self._wfm_segs]) == self._abs_time, "Sum of waveform segment durations do not match the total specified waveform group time. Consider making one of the segments elastic by setting its duration to be -1."
        
        if fs == -1:
            return  #i.e. just for pure validation and no calculation purposes...

        #Return the elastic segment index
        if len(elastic_segs) > 0:
            elas_seg_ind = elastic_segs[0]
            #On the rare case where the segments won't fit the overall size by being too little (e.g. 2.4, 2.4, 4.2 adds up to 9, but rounding
            #the sampled segments yields 2, 2, 4 which adds up to 8) or too large (e.g. 2.6, 2.6, 3.8 adds up to 9, but rounding the sampled
            #segments yields 3, 3, 4 which adds up to 10), the elastic-time must be carefully calculated from the total number of sample points
            #rather than the durations!
            elastic_time = self._abs_time*fs - sum([self._wfm_segs[x].NumPts(fs) for x in range(len(self._wfm_segs)) if x != elas_seg_ind])
            elastic_time = elastic_time / fs

            return (elas_seg_ind, elastic_time)
        else:
            return (-1,-1)

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
        elas_seg_ind, elastic_time = self._validate_wfm_segs(fs)
        
        #Calculate and set the elastic time segment
        if elas_seg_ind != -1:  #Note that self._abs_time > 0
            self._wfm_segs[elas_seg_ind].Duration = elastic_time    #Negate the -1 segment

        #Concatenate the individual waveform segments
        final_wfm = np.array([])
        t0 = 0
        for m in range(self._num_repeats):
            for cur_wfm_seg in self._wfm_segs:
                if cur_wfm_seg.NumPts(fs) == 0:
                    continue
                #TODO: Preallocate - this is a bit inefficient...
                final_wfm = np.concatenate((final_wfm, cur_wfm_seg.get_waveform(lab, fs, t0_ind + t0, ch_index)))
                t0 = final_wfm.size

        #Reset segment to be elastic
        if elas_seg_ind != -1:
            self._wfm_segs[elas_seg_ind].Duration = -1
        
        return final_wfm

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['Duration'] = self._abs_time
        cur_dict['NumRepeats'] = self._num_repeats
        cur_dict['WaveformSegments'] = [x._get_current_config() for x in self._wfm_segs]
        return cur_dict

class WFS_Constant(WaveformSegmentBase):
    def __init__(self, name, transform_func, time_len, value=0.0):
        super().__init__(name, transform_func, time_len)
        self._value = value

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Value"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        if config_dict['Mod Func']['Name'] == '':
            wfmt_obj = None
        else:
            wfmt_obj = WaveformTransformationArgs(config_dict['Mod Func']['Name'], config_dict['Mod Func']['Args'])
        return cls(config_dict["Name"], wfmt_obj, config_dict["Duration"], config_dict["Value"])

    @property
    def Value(self):
        return self._value
    @Value.setter
    def Value(self, const_val):
        self._value = const_val

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
        return np.zeros(round(self.NumPts(fs))) + self._value

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['Duration'] = self.Duration
        cur_dict['Value'] = self._value
        return cur_dict

class WFS_Gaussian(WaveformSegmentBase):
    def __init__(self, name, transform_func, time_len, amplitude, num_sd=1.96):
        super().__init__(name, transform_func, time_len)
        #TODO: Add in a classmethod to use sigma and truncate...
        self._amplitude = amplitude
        self._num_sd = num_sd

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Amplitude", "Num SD"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        #TODO: Fix the functionality here.
        if config_dict['Mod Func']['Name'] == '':
            wfmt_obj = None
        else:
            wfmt_obj = WaveformTransformationArgs(config_dict['Mod Func']['Name'], config_dict['Mod Func']['Args'])
        return cls(config_dict["Name"], wfmt_obj, config_dict["Duration"], config_dict["Amplitude"], config_dict["Num SD"])

    @property
    def Amplitude(self):
        return self._amplitude
    @Amplitude.setter
    def Amplitude(self, ampl_val):
        self._amplitude = ampl_val

    @property
    def NumStdDev(self):
        return self._num_sd
    @NumStdDev.setter
    def NumStdDev(self, num_sd):
        self._num_sd = num_sd

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
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
        cur_dict['Duration'] = self.Duration
        cur_dict['Amplitude'] = self._amplitude
        cur_dict['Num SD'] = self._num_sd
        return cur_dict

class WFS_Cosine(WaveformSegmentBase):
    def __init__(self, name, transform_func, time_len, amplitude=0.0, frequency=0.0, phase=0.0):
        super().__init__(name, transform_func, time_len)
        self._amplitude = amplitude
        self._frequency = frequency
        self._phase = phase

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Amplitude", "Frequency", "Phase"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        if config_dict['Mod Func']['Name'] == '':
            wfmt_obj = None
        else:
            wfmt_obj = WaveformTransformationArgs(config_dict['Mod Func']['Name'], config_dict['Mod Func']['Args'])
        return cls(config_dict["Name"], wfmt_obj, config_dict["Duration"], config_dict["Amplitude"], config_dict["Frequency"], config_dict["Phase"])

    @property
    def Amplitude(self):
        return self._amplitude
    @Amplitude.setter
    def Amplitude(self, ampl_val):
        self._amplitude = ampl_val

    @property
    def Frequency(self):
        return self._frequency
    @Frequency.setter
    def Frequency(self, freq_val):
        self._frequency = freq_val

    @property
    def Phase(self):
        return self._phase
    @Phase.setter
    def Phase(self, phase_val):
        self._phase = phase_val

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
        t_vals = np.arange(self.NumPts(fs)) / fs
        return self.Amplitude * np.cos(2*np.pi*self.Frequency * t_vals + self.Phase)

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['Duration'] = self.Duration
        cur_dict['Amplitude'] = self._amplitude
        cur_dict['Frequency'] = self._frequency
        cur_dict['Phase'] = self._phase
        return cur_dict


class WFS_Multiplex(WaveformSegmentBase):
    """
    Class that creates a frequency multiplexed waveform
    """
    def __init__(self, name, transform_func, time_len, amplitudes = None, frequencies = [0.0], phases = None):
        """
        Class Constructor

        """
        super().__init__(name, transform_func, time_len)
        # Setup Attributes
        self._frequencies = frequencies

        if (phases is None or len(phases) != len(frequencies)) :
            # Phase parameter passed in is not to spec
            print("Input phases do not match waveform specification, setting all to 0")
            phases = np.zeros(len(frequencies))
            self._phases = phases
        else :
            self._phases = phases

        if (amplitudes is None or len(amplitudes) != len(frequencies)) :
            # Phase parameter passed in is not to spec
            print("Input amplitudes do not match waveform specification, setting all to 0")
            amplitudes = np.zeros(len(frequencies))
            self._amplitudes = amplitudes
        else :
            self._amplitudes = amplitudes


    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Amplitude", "Frequency", "Phase"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        if config_dict['Mod Func']['Name'] == '':
            wfmt_obj = None
        else:
            wfmt_obj = WaveformTransformationArgs(config_dict['Mod Func']['Name'], config_dict['Mod Func']['Args'])
        return cls(config_dict["Name"], wfmt_obj, config_dict["Duration"], config_dict["Amplitude"], config_dict["Frequency"], config_dict["Phase"])

    @property
    def Amplitudes(self) :
        return self._amplitudes
    @Amplitudes.setter
    def Amplitudes(self, ampl_vals):
        self._amplitudes = ampl_vals

    @property
    def Frequencies(self) :
        return self._frequencies
    @Frequencies.setter
    def Frequencies(self, freq_vals):
        self._frequencies = freq_vals

    @property
    def Phases(self):
        return self._phases
    @Phases.setter
    def Phases(self, phase_val):
        self._phases = phase_val

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
        t_vals = np.arange(self.NumPts(fs)) / fs
        # Iterate through frequencies and generate a series of sine waves, then sum them for the final waveform
        finalWaveform = np.zeros(len(t_vals))
        for i in range(0, len(self.Frequencies)) :
            finalWaveform += self.Amplitudes[i] * np.cos(2*np.pi*self.Frequencies[i] * t_vals + self.Phases[i])

        return finalWaveform

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['Duration'] = self.Duration
        cur_dict['Amplitude'] = self._amplitude
        cur_dict['Frequency'] = self._frequency
        cur_dict['Phase'] = self._phase
        return cur_dict

class WFS_Arbitrary(WaveformSegmentBase):
    """
    Waveform segment class for constructing arbitrary waveforms
    """
    def __init__(self, name, transform_func, time_len, amplitudes):
        """
        Class Initialialiser
        """
        super().__init__(name, transform_func, time_len)
        #TODO: Add in a classmethod to use sigma and truncate...
        self._amplitudes = amplitudes


    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Amplitudes"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        #TODO: Fix the functionality here.
        if config_dict['Mod Func']['Name'] == '':
            wfmt_obj = None
        else:
            wfmt_obj = WaveformTransformationArgs(config_dict['Mod Func']['Name'], config_dict['Mod Func']['Args'])
        return cls(config_dict["Name"], wfmt_obj, config_dict["Duration"], config_dict["Amplitude"], config_dict["Num SD"])

    @property
    def Amplitudes(self):
        return self._amplitudes
    @Amplitudes.setter
    def Amplitudes(self, ampl_vals):
        self._amplitudes = ampl_vals

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
        """
        Create Arbitrary waveform from provided amplitude envelope
        Upsamples/downsamples waveform to align with sampling frequency 
        """
        n = self.NumPts(fs)

        if (n > len(self._amplitudes)) :
            # Need to upsample amplitudes to match n
            pass
        elif (n < len(self._amplitudes)) :
            # Need to downsample amplitudes to match n
            pass
        else :
            # n match len of amplitudes
            sample_points = self._amplitudes

        return sample_points

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['Duration'] = self.Duration
        cur_dict['Amplitudes'] = self._amplitudes
        return cur_dict
    
class WFS_RandomGaussian(WaveformSegmentBase):
    def __init__(self, name, transform_func, time_len, sd=1.96, mean=0, seed=42):
        super().__init__(name, transform_func, time_len)
        #TODO: Add in a classmethod to use sigma and truncate...
        self._mean = mean
        self._sd = sd
        self._seed = seed

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Name", "Duration", "Mean", "StdDev", "Seed"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        if config_dict['Mod Func']['Name'] == '':
            wfmt_obj = None
        else:
            wfmt_obj = WaveformTransformationArgs(config_dict['Mod Func']['Name'], config_dict['Mod Func']['Args'])
        return cls(config_dict["Name"], wfmt_obj, config_dict["Duration"], config_dict["StdDev"], config_dict["Mean"], config_dict["Seed"])

    @property
    def Mean(self):
        return self._mean
    @Mean.setter
    def Mean(self, mean):
        self._mean = mean

    @property
    def StdDev(self):
        return self._sd
    @StdDev.setter
    def StdDev(self, sd):
        self._sd = sd
    
    @property
    def Seed(self):
        return self._seed
    @Seed.setter
    def Seed(self, val):
        self._seed = val

    def _get_waveform(self, lab, fs, t0_ind, ch_index):
        return np.random.default_rng(seed=self.Seed).normal(self.Mean, self.StdDev, size=self.NumPts(fs))

    def _get_current_config(self):
        cur_dict = WaveformSegmentBase._get_current_config(self)
        cur_dict['Duration'] = self.Duration
        cur_dict['Mean'] = self.Mean
        cur_dict['StdDev'] = self.StdDev
        cur_dict['Seed'] = self.Seed
        return cur_dict
