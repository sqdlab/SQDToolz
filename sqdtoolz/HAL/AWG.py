from sqdtoolz.HAL.HALbase import*
from sqdtoolz.HAL.TriggerPulse import*
import numpy as np
from sqdtoolz.HAL.AWGOutputChannel import*
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from sqdtoolz.HAL.WaveformSegments import*

class WaveformAWG(HALbase, TriggerOutputCompatible, TriggerInputCompatible):
    def __init__(self, hal_name, lab, awg_channel_tuples, sample_rate, global_factor = 1.0, **kwargs):
        HALbase.__init__(self, hal_name)
        if lab._register_HAL(self):
            #
            #awg_channel_tuples is given as (instr_AWG_name, channel_name)
            self._awg_chan_list = []
            #TODO: Check that awg_channel_tuples is a list!
            for ch_index, cur_ch_tupl in enumerate(awg_channel_tuples):
                assert len(cur_ch_tupl) == 2, "The list awg_channel_tuples must contain tuples of form (instr_AWG_name, channel_name)."
                cur_awg_name, cur_ch_name = cur_ch_tupl            
                self._awg_chan_list.append(AWGOutputChannel(lab._get_instrument(cur_awg_name), cur_ch_name, ch_index, self))
                
            self._sample_rate = sample_rate
            self._global_factor = global_factor
            self._wfm_segment_list = []
            self._auto_comp = 'None'
            self._auto_comp_algos = ['None', 'Basic']
        else:
            assert len(awg_channel_tuples) == len(self._awg_chan_list), "Cannot reinstantiate a waveform by the same name, but different channel configurations."
            for ch_index, cur_ch_tupl in enumerate(awg_channel_tuples):
                assert cur_ch_tupl[0] == self._awg_chan_list[ch_index]._instr_awg.name, "Cannot reinstantiate a waveform by the same name, but different channel configurations."
                assert cur_ch_tupl[1] == self._awg_chan_list[ch_index]._channel_name, "Cannot reinstantiate a waveform by the same name, but different channel configurations."
            self._sample_rate = sample_rate
            self._global_factor = global_factor
            self._wfm_segment_list = []

    def __new__(cls, hal_name, lab, awg_channel_tuples, sample_rate, global_factor = 1.0, **kwargs):
        prev_exists = lab.get_HAL(hal_name)
        if prev_exists:
            assert isinstance(prev_exists, WaveformAWG), "A different HAL type already exists by this name."
            return prev_exists
        else:
            return super(WaveformAWG, cls).__new__(cls)

    @property
    def AutoCompression(self):
        return self._auto_comp
    @AutoCompression.setter
    def AutoCompression(self, algorithm):
        assert algorithm in ['None', 'Basic'], f"Unknown algorithm for auto-compression. Allowed algorithms are: {self._auto_comp_algos}"
        self._auto_comp = algorithm

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

    def _get_trigger_output_by_id(self, outputID):
        #Doing it this way as the naming scheme may change in the future - just flatten list and find the marker object...
        cur_obj = None
        assert type(outputID) is list or type(outputID) is tuple, "ch_ID must be a list/tuple of 2 elements (channel index and marker index)."
        assert len(outputID) == 2, "ch_ID must be a list/tuple of 2 elements (channel index and marker index)."
        ch_ID = outputID[0]
        mkr_ID = outputID[1]
        assert ch_ID >= 0 and ch_ID < len(self._awg_chan_list), "ch_ID must be a valid channel index."
        cur_obj = next((x for x in self.get_output_channel(ch_ID)._awg_mark_list if x._ch_index == mkr_ID), None)
        assert cur_obj != None, f"The trigger output of ID {mkr_ID} does not exist."
        return cur_obj
    def _get_all_trigger_outputs(self):
        mkr_output_ids = []
        for chan_ind, cur_chan in enumerate(self._awg_chan_list):
            mkr_output_ids += [(chan_ind, cur_chan.num_markers)]
        return mkr_output_ids
        #TODO: Consider additional trigger outputs (e.g. AUX)?

    def _get_all_trigger_inputs(self):
        trig_inp_objs = []
        for cur_chan in self._awg_chan_list:
            trig_inp_objs += [cur_chan]
            trig_inp_objs += cur_chan.get_all_markers()
        return trig_inp_objs


    def _get_current_config(self):
        retDict = {
            'Name' : self.Name,
            'instrument' : [(x._instr_awg.name, x.Name) for x in self._awg_chan_list],
            'type' : 'AWG',
            'SampleRate' : self.SampleRate,
            'global_factor' : self._global_factor,
            'OutputChannels' : [x._get_current_config() for x in self._awg_chan_list]
            }
        retDict['WaveformSegments'] = self._get_current_config_waveforms()
        return retDict

    def _get_current_config_waveforms(self):
        #Write down the waveform-segment data - can be overwritten by the daughter class for a different format if required/desired...
        return [x._get_current_config() for x in self._wfm_segment_list]
    
    def _set_current_config(self, dict_config, lab):
        assert dict_config['type'] == 'AWG', 'Cannot set configuration to a AWG with a configuration that is of type ' + dict_config['type']
        
        self._sample_rate = dict_config['SampleRate']
        self._global_factor = dict_config['global_factor']
        for ind, cur_ch_output in enumerate(dict_config['OutputChannels']):
            self._awg_chan_list[ind]._set_current_config(cur_ch_output, lab)

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

    def plot_waveforms(self, overlap=False):
        final_wfms = self._assemble_waveform_raw()
        fig = plt.figure()
        if overlap:
            fig, axs = plt.subplots(1)
            t_vals = np.arange(final_wfms[0].size) / self._sample_rate      
            for ind, cur_wfm in enumerate(final_wfms):
                axs.plot(t_vals, cur_wfm)
        else:
            fig, axs = plt.subplots(len(final_wfms))
            fig.suptitle('AWG Waveforms')   #TODO: Add a more sensible title...
            t_vals = np.arange(final_wfms[0].size) / self._sample_rate
            for ind, cur_wfm in enumerate(final_wfms):
                axs[ind].plot(t_vals, cur_wfm)
        return fig

    def prepare_initial(self):
        #Prepare the waveform
        final_wfms = self._assemble_waveform_raw()

        self.cur_wfms_to_commit = []
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            if len(cur_awg_chan._awg_mark_list) > 0:
                mkr_list = [x._assemble_marker_raw() for x in cur_awg_chan._awg_mark_list]
            else:
                mkr_list = [np.array([])]
                
            dict_auto_comp = cur_awg_chan._instr_awg.AutoCompressionSupport
            if self.AutoCompression == 'None' or not dict_auto_comp['Supported'] or final_wfms[0].size < dict_auto_comp['MinSize']*2:
                #UNCOMPRESSED
                #Just program the AWG via over a single waveform    
                #Don't compress if disabled, unsupported or if the waveform size is too small to compress
                dict_wfm_data = {'waveforms' : [final_wfms[ind]], 'markers' : [mkr_list], 'seq_ids' : [0]}
            elif self.AutoCompression == 'Basic':
                #BASIC COMPRESSION
                #The basic compression algorithm is to chop up the waveform into its minimum set of bite-sized pieces and to find repetitive aspects
                dict_wfm_data = self._program_auto_comp_basic(cur_awg_chan, final_wfms[ind], mkr_list)
                
            seg_lens = [x.size for x in dict_wfm_data['waveforms']]
            cur_awg_chan._instr_awg.prepare_waveform_memory(cur_awg_chan._instr_awg_chan.short_name, seg_lens, raw_data=dict_wfm_data)
            self.cur_wfms_to_commit.append(dict_wfm_data)

    def prepare_final(self):
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            cur_awg_chan._instr_awg.program_channel(cur_awg_chan._instr_awg_chan.short_name, self.cur_wfms_to_commit[ind])                

    def _extract_marker_segments(self, mkr_list_overall, slice_start, slice_end):
        cur_mkrs = []
        for sub_mkr in range(len(mkr_list_overall)):
            if mkr_list_overall[sub_mkr].size > 0:
                cur_mkrs += [ mkr_list_overall[sub_mkr][slice_start:slice_end] ]
            else:
                cur_mkrs += [ mkr_list_overall[sub_mkr][:] ]    #Copy over the empty array...
        return cur_mkrs

    def _program_auto_comp_basic(self, cur_awg_chan, final_wfm_for_chan, mkr_list):
        #TODO: Add flags for changed/requires-update to ensure that segments in sequence are not unnecessary programmed repeatedly...
        #TODO: Improve algorithm
        dict_auto_comp = cur_awg_chan._instr_awg.AutoCompressionSupport
        dS = dict_auto_comp['MinSize']
        num_main_secs = int(np.floor(final_wfm_for_chan.size / dS))
        seq_segs = [final_wfm_for_chan[0:dS]]
        seq_mkrs = [self._extract_marker_segments(mkr_list, 0, dS)]
        seq_ids  = [0]
        for m in range(1,num_main_secs):
            cur_seg = final_wfm_for_chan[(m*dS):((m+1)*dS)]
            cur_mkrs = self._extract_marker_segments(mkr_list, m*dS, (m+1)*dS)
            found_match = False
            for ind, cur_seq_seg in enumerate(seq_segs):
                #Check main waveform array
                if np.array_equal(cur_seg, cur_seq_seg):
                    #Check the sub-markers
                    mkrs_match = True
                    for mkr in range(len(cur_mkrs)):
                        if not np.array_equal(seq_mkrs[ind][mkr], cur_mkrs[mkr]):
                            mkrs_match = False
                            break
                    if mkrs_match:
                        seq_ids += [ind]
                        found_match = True
                        break
            if not found_match:
                seq_ids += [len(seq_segs)]
                seq_segs += [cur_seg]
                seq_mkrs += [cur_mkrs]
        if (m+1)*dS < final_wfm_for_chan.size:
            #Reverse it if it was matched against some other segment previously...
            cur_mkrs = self._extract_marker_segments(mkr_list, m*dS, mkr_list[0].size)
            if found_match:
                seq_ids[-1] = len(seq_segs)
                seq_segs += [final_wfm_for_chan[(m*dS):]]
                seq_mkrs += [cur_mkrs]
            else:
                seq_segs[-1] = final_wfm_for_chan[(m*dS):]
                seq_mkrs[-1] = cur_mkrs

        return {'waveforms' : seq_segs, 'markers' : seq_mkrs, 'seq_ids' : seq_ids}
        