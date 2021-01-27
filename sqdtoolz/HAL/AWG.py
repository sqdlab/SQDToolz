import numpy as np
from scipy import signal
from sqdtoolz.HAL.AWGOutputChannel import*

class WaveformAWG:
    def __init__(self, awg_channel_tuples, sample_rate, global_factor = 1):
        #awg_channel_tuples is given as (instr_AWG, channel_name)
        self._awg_chan_list = []
        self._awg_mark_list = []
        #TODO: Check that awg_channel_tuples is a list!
        for cur_ch_tupl in awg_channel_tuples:
            assert len(cur_ch_tupl) == 2, "The list awg_channel_tuples must contain tuples of form (instr_AWG, channel_name)."
            cur_awg, cur_ch_name = cur_ch_tupl
            self._awg_chan_list.append(AWGOutputChannel(cur_ch_tupl[0], cur_ch_tupl[1]))
            if cur_awg.supports_markers(cur_ch_name):
                self._awg_mark_list.append(AWGOutputMarker(self))
            else:
                self._awg_mark_list.append(None)
        self._sample_rate = sample_rate
        self._global_factor = global_factor
        self._wfm_segment_list = []

    def add_waveform_segment(self, wfm_segment):
        self._wfm_segment_list.append(wfm_segment)

    def get_output_channel(self, outputIndex = 0):
        '''
        Returns an AWGOutputChannel object.
        '''
        assert outputIndex >= 0 and outputIndex < len(self._awg_chan_list), "Channel output index is out of range"
        return self._awg_chan_list[outputIndex]

    def get_output_channels(self):
        return self._awg_chan_list[:]

    def get_trigger_output(self, outputIndex = 0):
        '''
        Returns an AWGOutputMarker object.
        '''
        assert outputIndex >= 0 and outputIndex < len(self._awg_chan_list), "Channel output index is out of range"
        return self._awg_mark_list[outputIndex]

    def get_trigger_outputs(self):
        return self._awg_mark_list[:]

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
            if cur_seg.Name == seg_name:
                the_seg = seg_name
                break
            cur_ind += cur_seg.NumPts(self._sample_rate)
        assert the_seg != None, "Waveform Segment of name " + seg_name + " is not present in the current list of added Waveform Segments."
        return (int(cur_ind), int(cur_ind + cur_seg.NumPts(self._sample_rate) - 1))

    def _assemble_waveform_raw(self):
        #Concatenate the individual waveform segments
        final_wfm = np.array([])
        for cur_wfm_seg in self._wfm_segment_list:
            #TODO: Preallocate - this is a bit inefficient...
            final_wfm = np.concatenate((final_wfm, cur_wfm_seg.get_waveform(self._sample_rate)))
        #Scale the waveform via the global scale-factor...
        final_wfm *= self._global_factor
        return final_wfm

    def _get_waveform_plot_segments(self, resolution = 21):
        ret_list = []
        for cur_awg_chan in self._awg_chan_list:
            seg_dicts = []
            for cur_wfm_seg in self._wfm_segment_list:
                cur_dict = {}
                cur_dict['duration'] = cur_wfm_seg.Duration
                cur_y = cur_wfm_seg.get_waveform(self._sample_rate)
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

    def program_AWG(self):
        #Prepare the waveform
        final_wfm = self._assemble_waveform_raw()
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            if self._awg_mark_list[ind] != None:
                cur_awg_chan._instr_awg.program_channel(cur_awg_chan._instr_awg_chan.name, final_wfm, self._awg_mark_list[ind]._assemble_marker_raw())
            else:
                cur_awg_chan.Parent.program_channel(cur_awg_chan.name, final_wfm)
