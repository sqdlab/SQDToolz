import numpy as np
from scipy import signal
from sqdtoolz.HAL.AWGOutputChannel import*
import matplotlib.patches as patches
import matplotlib.pyplot as plt

class WaveformAWG:
    def __init__(self, awg_channel_tuples, sample_rate, global_factor = 1):
        #awg_channel_tuples is given as (instr_AWG, channel_name)
        self._awg_chan_list = []
        self._awg_mark_list = []
        #TODO: Check that awg_channel_tuples is a list!
        for ch_index, cur_ch_tupl in enumerate(awg_channel_tuples):
            assert len(cur_ch_tupl) == 2, "The list awg_channel_tuples must contain tuples of form (instr_AWG, channel_name)."
            cur_awg, cur_ch_name = cur_ch_tupl
            self._awg_chan_list.append(AWGOutputChannel(cur_ch_tupl[0], cur_ch_tupl[1]))
            
            cur_mkrs = []
            num_markers = cur_awg.num_supported_markers(cur_ch_name)
            if num_markers > 0:
                for ind in range(1,num_markers+1):
                    cur_mkrs.append(AWGOutputMarker(self, f'ch{ch_index}_mkr{ind}', ch_index))
            self._awg_mark_list.append(cur_mkrs)
        self._sample_rate = sample_rate
        self._global_factor = global_factor
        self._wfm_segment_list = []
        self._trig_src_objs = [(None,1)]*len(awg_channel_tuples)

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

    def get_marker_output(self, marker_index, output_channel = 0):
        '''
        Returns an AWGOutputMarker object.
        '''
        assert output_channel >= 0 and output_channel < len(self._awg_chan_list), "Channel output index is out of range"
        assert marker_index >= 0 and marker_index < len(self._awg_mark_list[output_channel]), "Marker output index is out of range"
        return self._awg_mark_list[output_channel][marker_index]

    def get_marker_outputs(self):
        return self._awg_mark_list[:]

    def _get_trigger_output_by_id(self, trigID):
        '''
        Some objects may have a hierarchy of trigger outputs - it's best to categorise them via some unique ID which can be referenced easily.

        Inputs:
            - trigID - unique ID of the trigger (e.g. a string)
        
        Returns a TriggerType object representing an output trigger.
        '''
        #Doing it this way as the naming scheme may change in the future - just flatten list and find the marker object...
        cur_obj = None
        for cur_ch in range(len(self._awg_chan_list)):
            cur_obj = next((x for x in self._awg_mark_list[cur_ch] if x.name == trigID), None)
            if cur_obj != None:
                break
        assert cur_obj != None, f"The trigger output of ID {trigID} does not exist."
        return cur_obj

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
        return [final_wfm]*len(self._awg_chan_list)

    def set_trigger_source(self, trig_src_obj, trig_pol = 1, ch_index = -1):
        #TODO: Consider error-checking here
        #TODO: Override this in multi-channel setups to give the flexible option of different triggers for different channels
        if (ch_index == -1):
            for cur_ch in range(len(self._trig_src_objs)):
                self._trig_src_objs[cur_ch] = (trig_src_obj, trig_pol)
        else:
            self._trig_src_objs[ch_index] = (trig_src_obj, trig_pol)

    def get_trigger_source(self, ch_index = 0):
        '''
        Get the Trigger object corresponding to the trigger source.
        '''
        return self._trig_src_objs[ch_index][0]
    def get_trigger_polarity(self, ch_index = 0):
        return self._trig_src_objs[ch_index][1]

    def _get_waveform_plot_segments(self, waveform_index = 0, resolution = 21):
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
            if len(self._awg_mark_list[ind]) > 0:
                mkr_list = [x._assemble_marker_raw() for x in self._awg_mark_list[ind]]
                cur_awg_chan._instr_awg.program_channel(cur_awg_chan._instr_awg_chan.short_name, final_wfms[ind], mkr_list)
            else:
                cur_awg_chan._instr_awg.program_channel(cur_awg_chan._instr_awg_chan.short_name, final_wfms[ind])


class WaveformAWGIQ(WaveformAWG):
    def __init__(self, awg_channel_tuples, sample_rate, iq_frequency, iq_amplitude = 1.0, global_factor = 1):
        super().__init__(awg_channel_tuples, sample_rate, global_factor)
        self._iq_frequency = iq_frequency
        self._iq_amplitude = iq_amplitude   #Given as the raw output voltage (should usually set the envelopes to unity amplitude in this case)
        self._iq_phase = 0.0                #Added onto both the cosine and sine terms
        self._iq_amplitude_factor = 1.0     #Defined as a = Q/I amplitudes and the factor 'a' is multiplied onto the Q-channel waveform 
        self._iq_phase_offset = 0.0         #Defined as the phase to add to the Q (sine) term
        self._iq_dc_offsets = (0.0, 0.0)
        self._iq_reset_phase = True         #If True, the phases of the cosine and sine waves are reset to zero after every waveform segment.

    @property
    def IQFrequency(self):
        return self._iq_frequency
    @IQFrequency.setter
    def IQFrequency(self, val):
        self._iq_frequency = val

    @property
    def IQPhase(self):
        return self._iq_phase
    @IQPhase.setter
    def IQPhase(self, val):
        self._iq_phase = val

    @property
    def IQAmplitude(self):
        return self._iq_amplitude
    @IQAmplitude.setter
    def IQAmplitude(self, val):
        self._iq_amplitude = val

    @property
    def IQAmplitude(self):
        return self._iq_amplitude
    @IQAmplitude.setter
    def IQAmplitude(self, val):
        self._iq_amplitude = val

    @property
    def IQAmplitudeFactor(self):
        return self._iq_amplitude_factor
    @IQAmplitudeFactor.setter
    def IQAmplitudeFactor(self, val):
        self._iq_amplitude_factor = val

    @property
    def IQPhaseOffset(self):
        return self._iq_phase_offset
    @IQPhaseOffset.setter
    def IQPhaseOffset(self, val):
        self._iq_phase_offset = val

    @property
    def IQdcOffset(self):
        return self._iq_dc_offsets
    @IQdcOffset.setter
    def IQdcOffset(self, val):
        self._iq_dc_offsets = val

    @property
    def IQResetPhase(self):
        return self._iq_reset_phase
    @IQResetPhase.setter
    def IQResetPhase(self, boolVal):
        #TODO: Add type+error checking to all the boolVal, val etc...
        self._iq_reset_phase = boolVal

    def set_IQ_parameters(self, amp = 1.0, phase = 0.0, dc_offset = (0.0, 0.0), amplitude_factor = 1.0, phase_offset = 0.0):
        self.IQAmplitude = amp
        self.IQPhase = phase
        self.IQdcOffset = dc_offset
        self.IQAmplitudeFactor = amplitude_factor
        self.IQPhaseOffset = phase_offset        

    def _assemble_waveform_raw(self):
        #Concatenate the individual waveform segments
        final_wfm_I = np.array([])
        final_wfm_Q = np.array([])
        x_prev = 0
        for cur_wfm_seg in self._wfm_segment_list:
            cur_wfm_seg_data = cur_wfm_seg.get_waveform(self._sample_rate)
            #Run the modulation
            t_vals = (np.arange(cur_wfm_seg_data.size) + x_prev) / self._sample_rate
            i_vals = cur_wfm_seg_data * self.IQAmplitude * np.cos(2 * np.pi * self.IQFrequency * t_vals + self.IQPhase) + self.IQdcOffset[0]
            q_vals = cur_wfm_seg_data * self.IQAmplitude * self.IQAmplitudeFactor * np.sin(2 * np.pi * self.IQFrequency * t_vals + self.IQPhase + self.IQPhaseOffset) + self.IQdcOffset[1]
            
            if self.IQResetPhase:
                x_prev = 0
            else:
                x_prev += cur_wfm_seg_data.size

            #TODO: Preallocate - this is a bit inefficient...
            final_wfm_I = np.concatenate((final_wfm_I, i_vals))
            final_wfm_Q = np.concatenate((final_wfm_Q, q_vals))
        #Scale the waveform via the global scale-factor...
        final_wfm_I *= self._global_factor
        final_wfm_Q *= self._global_factor
        return [final_wfm_I, final_wfm_Q]
