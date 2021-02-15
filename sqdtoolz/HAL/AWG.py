import numpy as np
from scipy import signal
from sqdtoolz.HAL.AWGOutputChannel import*
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from sqdtoolz.HAL.WaveformSegments import*

class WaveformAWG:
    def __init__(self, name, awg_channel_tuples, sample_rate, global_factor = 1.0, **kwargs):
        self._name = name

        #awg_channel_tuples is given as (instr_AWG, channel_name)
        self._awg_chan_list = []
        #TODO: Check that awg_channel_tuples is a list!
        for ch_index, cur_ch_tupl in enumerate(awg_channel_tuples):
            assert len(cur_ch_tupl) == 2, "The list awg_channel_tuples must contain tuples of form (instr_AWG, channel_name)."
            cur_awg, cur_ch_name = cur_ch_tupl
            self._awg_chan_list.append(AWGOutputChannel(cur_ch_tupl[0], cur_ch_tupl[1], ch_index, self))
            
        self._sample_rate = sample_rate
        self._global_factor = global_factor
        self._wfm_segment_list = []

    @property
    def Name(self):
        return self._name

    def clear_segments(self):
        self._wfm_segment_list.clear()

    def set_waveform_segments(self, wfm_segment_list):
        self._wfm_segment_list = wfm_segment_list[:]

    def add_waveform_segment(self, wfm_segment):
        self._wfm_segment_list.append(wfm_segment)
        
    def get_waveform_segment(self, wfm_segment_name):
        the_seg = None
        for cur_seg in self._wfm_segment_list:
            if cur_seg.Name == wfm_segment_name:
                the_seg = cur_seg
                break
        assert the_seg != None, "Waveform Segment of name " + seg_name + " is not present in the current list of added Waveform Segments."
        return the_seg

    def get_output_channel(self, outputIndex = 0):
        '''
        Returns an AWGOutputChannel object.
        '''
        assert outputIndex >= 0 and outputIndex < len(self._awg_chan_list), "Channel output index is out of range"
        return self._awg_chan_list[outputIndex]

    def get_output_channels(self):
        return self._awg_chan_list[:]

    def set_trigger_source_all(self, trig_src_obj, trig_pol = 1):
        for cur_ch in self._awg_chan_list:
            cur_ch.set_trigger_source(trig_src_obj, trig_pol)

    @property
    def Duration(self):
        full_len = 0
        for cur_seg in self._wfm_segment_list:
            full_len += cur_seg.Duration
        return full_len

    @property
    def SampleRate(self):
        return self._sample_rate

    @property
    def NumPts(self):
        return self.Duration * self._sample_rate

    def _get_index_points_for_segment(self, seg_name):
        the_seg = None
        cur_ind = 0
        for cur_seg in self._wfm_segment_list:
            if cur_seg.Name == seg_name:
                the_seg = seg_name
                break
            cur_ind += cur_seg.NumPts(self._sample_rate)
        assert the_seg != None, "Waveform Segment of name " + seg_name + " is not present in the current list of added Waveform Segments."
        return (int(cur_ind), int(cur_ind + cur_seg.NumPts(self._sample_rate) - 1))

    def _assemble_waveform_raw(self):
        num_chnls = len(self._awg_chan_list)
        final_wfms = [np.array([])]*num_chnls
        #Assemble each channel separately
        for cur_ch in range(len(self._awg_chan_list)):
            t0 = 0
            #Concatenate the individual waveform segments
            for cur_wfm_seg in self._wfm_segment_list:
                #TODO: Preallocate - this is a bit inefficient...
                final_wfms[cur_ch] = np.concatenate((final_wfms[cur_ch], cur_wfm_seg.get_waveform(self._sample_rate, t0, cur_ch)))
                t0 += final_wfms[cur_ch].size
            #Scale the waveform via the global scale-factor...
            final_wfms[cur_ch] *= self._global_factor
        return final_wfms

    def _get_trigger_output_by_id(self, trigID, ch_ID):
        '''
        Some objects may have a hierarchy of trigger outputs - it's best to categorise them via some unique ID which can be referenced easily.

        Inputs:
            - trigID - unique ID of the trigger (e.g. a string)
            - ch_ID - auxiliary ID (e.g. channel name)
        
        Returns a TriggerType object representing an output trigger.
        '''
        #Doing it this way as the naming scheme may change in the future - just flatten list and find the marker object...
        cur_obj = None
        assert type(ch_ID) is int, "ch_ID must be the channel index."
        assert ch_ID >= 0 and ch_ID < len(self._awg_chan_list), "ch_ID must be a valid channel index."
        cur_obj = next((x for x in self.get_output_channel(ch_ID)._awg_mark_list if x.name == trigID), None)
        assert cur_obj != None, f"The trigger output of ID {trigID} does not exist."
        return cur_obj

    def _get_current_config(self):
        retDict = {
            'instrument' : [(x._instr_awg.name, x.Name) for x in self._awg_chan_list],
            'type' : 'AWG',
            'Name' : self.Name,
            'waveformType' : type(self).__name__,
            'SampleRate' : self.SampleRate,
            'global_factor' : self._global_factor,
            'OutputChannels' : [x._get_current_config() for x in self._awg_chan_list]
            }
        retDict['WaveformSegments'] = self._get_current_config_waveforms()
        return retDict

    def _get_current_config_waveforms(self):
        #Write down the waveform-segment data - can be overwritten by the daughter class for a different format if required/desired...
        return [x._get_current_config() for x in self._wfm_segment_list]
    
    def _set_current_config(self, dict_config, instr_obj = None):
        assert dict_config['type'] == 'AWG', 'Cannot set configuration to a AWG with a configuration that is of type ' + dict_config['type']
        assert dict_config['waveformType'] == type(self).__name__, 'Waveform type given in the configuration does not match the current waveform object type.'
        
        #TODO: Need to modify this for AWG channel lists?
        if (instr_obj != None):
            self._instr_ddg = instr_obj
        
        self._sample_rate = dict_config['SampleRate']
        self._global_factor = dict_config['global_factor']
        for ind, cur_ch_output in enumerate(dict_config['OutputChannels']):
            self._awg_chan_list[ind]._set_current_config(cur_ch_output)

        self._set_current_config_waveforms(dict_config['WaveformSegments'])

    def _set_current_config_waveforms(self, list_wfm_dict_config):
        '''
        Sets the current waveform AWG waveform segments by clearing the current waveform segments, instantiating new classes by using the
        segment class name (prescribed in the given list of configuration dictionaries) and then finally setting their parameters.

        Input:
            - list_wfm_dict_config - List of waveform configuration dictionaries recognised by the relevant WaveformSegment classes (i.e.
                                     daughters of WaveformSegmentBase). The dictionary has the WaveformSegment class type in its key "type".

        Precondition: The WaveformSegment class given in the key "type" in list_wfm_dict_config must exist in WaveformSegments.py. If it is
                      defined elsewhere, then import said file into this file (AWG.py) to ensure that it is within the current scope.
        '''
        self._wfm_segment_list.clear()
        for cur_wfm in list_wfm_dict_config:
            cur_wfm_type = cur_wfm['type']
            assert cur_wfm_type in globals(), cur_wfm_type + " is not in the current namespace. If the class does not exist in WaveformSegments include wherever it lives by importing it in AWG.py."
            cur_wfm_type = globals()[cur_wfm_type]
            self._wfm_segment_list.append(cur_wfm_type.fromConfigDict(cur_wfm))

    def _get_waveform_plot_segments(self, waveform_index = 0, resolution = 21):
        ret_list = []
        for cur_ch_index, cur_awg_chan in enumerate(self._awg_chan_list):
            seg_dicts = []
            t0 = 0
            for cur_wfm_seg in self._wfm_segment_list:
                cur_dict = {}
                cur_dict['duration'] = cur_wfm_seg.Duration
                #TODO: Use _get_waveform to yield the unmodified waveform (i.e. just envelope) if some flag is set
                cur_y = cur_wfm_seg.get_waveform(self._sample_rate, t0, cur_ch_index)
                t0 += cur_wfm_seg.NumPts(self._sample_rate) / self._sample_rate
                #Skip this segment if it's empty...
                if cur_y.size == 0:
                    continue
                #Stretch the plot to occupy the range: [0,1]
                min_y = np.min(cur_y)
                if (min_y < 0):
                    cur_y -= min_y
                max_y = np.max(cur_y)
                if (max_y > 0):
                    cur_y /= max_y
                #Downsample the points if necessary to speed up plotting...
                cur_dict['yPoints'] = signal.resample(cur_y, resolution)
                seg_dicts.append(cur_dict)
            ret_list.append((cur_awg_chan._instr_awg.name + ":" + cur_awg_chan._channel_name, seg_dicts))
        return ret_list

    def plot_waveforms(self):
        final_wfms = self._assemble_waveform_raw()
        fig = plt.figure()
        fig, axs = plt.subplots(len(final_wfms))
        fig.suptitle('AWG Waveforms')   #TODO: Add a more sensible title...
        t_vals = np.arange(final_wfms[0].size) / self._sample_rate
        for ind, cur_wfm in enumerate(final_wfms):
            axs[ind].plot(t_vals, cur_wfm)
        return fig

    def program_AWG(self):
        #Prepare the waveform
        final_wfms = self._assemble_waveform_raw()
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            cur_awg_chan._instr_awg.SampleRate = self._sample_rate
            if len(cur_awg_chan._awg_mark_list) > 0:
                mkr_list = [x._assemble_marker_raw() for x in cur_awg_chan._awg_mark_list]
                cur_awg_chan._instr_awg.program_channel(cur_awg_chan._instr_awg_chan.short_name, final_wfms[ind], mkr_list)
            else:
                cur_awg_chan._instr_awg.program_channel(cur_awg_chan._instr_awg_chan.short_name, final_wfms[ind])

