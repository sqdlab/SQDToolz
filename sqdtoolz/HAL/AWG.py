from sqdtoolz.HAL.HALbase import*
from sqdtoolz.HAL.TriggerPulse import*
import numpy as np
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from sqdtoolz.HAL.WaveformSegments import*
import scipy.signal

class AWGBase:
    def __init__(self, sample_rate, total_time, global_factor):
        self._sample_rate = sample_rate
        self._wfm_segment_list = []
        self._auto_comp = 'None'
        self._auto_comp_linked = False
        self._auto_comp_algos = ['None', 'Basic']
        self._total_time = total_time
        self._global_factor = global_factor        

    @property
    def AutoCompression(self):
        return self._auto_comp
    @AutoCompression.setter
    def AutoCompression(self, algorithm):
        assert algorithm in ['None', 'Basic'], f"Unknown algorithm for auto-compression. Allowed algorithms are: {self._auto_comp_algos}"
        self._auto_comp = algorithm

    @property
    def AutoCompressionLinkChannels(self):
        return self._auto_comp_linked
    @AutoCompressionLinkChannels.setter
    def AutoCompressionLinkChannels(self, boolVal):
        self._auto_comp_linked = boolVal

    @property
    def Duration(self):
        if self._total_time != -1:
            return self._total_time
        full_len = 0
        for cur_seg in self._wfm_segment_list:
            full_len += cur_seg.Duration
        #If there is an elastic time-segment, then negate the -1 and add in the correct elastic time...
        elas_seg_ind, elastic_time = self._get_elastic_time_seg_params()
        if elas_seg_ind != -1:
            full_len = full_len + 1 + elastic_time
        return full_len

    @property
    def SampleRate(self):
        return self._sample_rate

    @property
    def NumPts(self):
        return round(self.Duration * self._sample_rate)

    def set_total_time(self, total_time):
        self._total_time = total_time
    def set_valid_total_time(self, min_time):
        #TODO: Make this more general - e.g. if using a Keysight that requires one set of constraints and
        #a Tektronix on the other channel with a different set of constraints, the valid time must reflect that!!!
        #TODO: May have to change the sample-rate model to be a list of sample-rates? NumPts is a function of sample-rate after all...
        self.set_total_time(self.get_valid_length_from_time(min_time)[0])

    def get_valid_length_from_pts(self, num_pts):
        ret_vals = []
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            mem_params = cur_awg_chan._instr_awg.MemoryRequirements
            resid = num_pts % mem_params['Multiple']
            if resid > 0:
                num_pts = num_pts + mem_params['Multiple'] - resid
            if num_pts < mem_params['MinSize']:
                num_pts = mem_params['MinSize']
            ret_vals += [ num_pts / self.SampleRate ]
        return ret_vals
    def get_valid_length_from_time(self, time_length):
        ret_vals = []
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            mem_params = cur_awg_chan._instr_awg.MemoryRequirements
            num_pts = time_length * self.SampleRate
            resid = num_pts % mem_params['Multiple']
            if resid > 0:
                num_pts = num_pts + mem_params['Multiple'] - resid
            if num_pts < mem_params['MinSize']:
                num_pts = mem_params['MinSize']
            ret_vals += [ num_pts / self.SampleRate ]
        return ret_vals

    def _get_marker_waveform_from_segments(self, segments):
        #Temporarily set the Duration of Elastic time-segment...
        elas_seg_ind, elastic_time = self._get_elastic_time_seg_params()
        if elas_seg_ind != -1:
            self._wfm_segment_list[elas_seg_ind].Duration = elastic_time

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

        final_wfm = np.zeros(int(np.round(self.NumPts)), dtype=np.ubyte)
        cur_ind = 0
        for cur_seg in self._wfm_segment_list:
            cur_len = cur_seg.NumPts(self._sample_rate)
            if cur_len == 0:
                continue
            if cur_seg.Name in const_segs:
                final_wfm[cur_ind:cur_ind+cur_len] = 1
            elif cur_seg.Name in dict_segs: #i.e. another segment with children like WFS_Group
                final_wfm[cur_ind:cur_ind+cur_len] = cur_seg._get_marker_waveform_from_segments(dict_segs[cur_seg.Name], self._sample_rate)
            cur_ind += cur_len
        
        #Reset segment to be elastic
        if elas_seg_ind != -1:
            self._wfm_segment_list[elas_seg_ind].Duration = -1
    
        return final_wfm

    def _get_elastic_time_seg_params(self):
        elastic_segs = []
        for ind_wfm, cur_wfm_seg in enumerate(self._wfm_segment_list):
            if cur_wfm_seg.Duration == -1:
                elastic_segs += [ind_wfm]
        assert len(elastic_segs) <= 1, "There are too many elastic waveform segments (cannot be above 1)."
        if self._total_time == -1:
            assert len(elastic_segs) == 0, f"If the total waveform length for \"{self.Name}\" is unbound, the number of elastic segments must be zero."
        if self._total_time > 0 and len(elastic_segs) == 0:
            assert np.abs(sum([x.Duration for x in self._wfm_segment_list])-self._total_time) < 5e-15, "Sum of waveform segment durations do not match the total specified waveform group time. Consider making one of the segments elastic by setting its duration to be -1."
        #Get the elastic segment index
        if len(elastic_segs) > 0:
            elas_seg_ind = elastic_segs[0]
            fs = self.SampleRate
            #On the rare case where the segments won't fit the overall size by being too little (e.g. 2.4, 2.4, 4.2 adds up to 9, but rounding
            #the sampled segments yields 2, 2, 4 which adds up to 8) or too large (e.g. 2.6, 2.6, 3.8 adds up to 9, but rounding the sampled
            #segments yields 3, 3, 4 which adds up to 10), the elastic-time must be carefully calculated from the total number of sample points
            #rather than the durations!
            elastic_time = self._total_time*fs - (sum([self._wfm_segment_list[x].NumPts(fs) for x in range(len(self._wfm_segment_list)) if x != elas_seg_ind]))
            elastic_time = elastic_time / fs
        else:
            elas_seg_ind = -1
            elastic_time = -1

        return (elas_seg_ind, elastic_time)

    def _assemble_waveform_raw(self):
        #Temporarily set the Duration of Elastic time-segment...
        elas_seg_ind, elastic_time = self._get_elastic_time_seg_params()
        if elas_seg_ind != -1:
            self._wfm_segment_list[elas_seg_ind].Duration = elastic_time

        num_chnls = len(self._awg_chan_list)
        final_wfms = [np.array([])]*num_chnls
        #Assemble each channel separately
        for cur_ch in range(len(self._awg_chan_list)):
            #Reset any waveform modulation commands for a new sequence construction...
            for cur_wfm_seg in self._wfm_segment_list:
                cur_wfm_seg.reset_waveform_transforms(self._lab)
            t0 = 0
            #Concatenate the individual waveform segments
            for cur_wfm_seg in self._wfm_segment_list:
                if cur_wfm_seg.NumPts(self.SampleRate) == 0:
                    continue
                #TODO: Preallocate - this is a bit inefficient...
                final_wfms[cur_ch] = np.concatenate((final_wfms[cur_ch], cur_wfm_seg.get_waveform(self._lab, self._sample_rate, t0, cur_ch)))
                t0 = final_wfms[cur_ch].size
            #Scale the waveform via the global scale-factor...
            final_wfms[cur_ch] *= self._global_factor
            assert self.NumPts == final_wfms[cur_ch].size, "The sample-rate and segment-lengths yield segment points that exceed the total waveform size. Ensure that there is sufficient freedom in the elastic segment size to compensate."
        
        #Reset segment to be elastic
        if elas_seg_ind != -1:
            self._wfm_segment_list[elas_seg_ind].Duration = -1
    
        return (final_wfms, elas_seg_ind)

    def _check_changes_wfm_data(self, dict_wfm_data, final_wfm, final_mkrs):
        #Check waveform equality (works for sequenced/autocompressed version as well)
        prog_wfm = np.concatenate([dict_wfm_data['waveforms'][x] for x in dict_wfm_data['seq_ids']])
        if not np.array_equal(prog_wfm, final_wfm):
            return False
        #Check markers...
        for m in range(len(final_mkrs)):
            prog_mkrs = np.concatenate([dict_wfm_data['markers'][x][m] for x in dict_wfm_data['seq_ids']])
            if not np.array_equal(prog_mkrs, final_mkrs[m]):
                return False
        return True
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
        #TODO: Improve algorithm (a winter research project for a Winter Student!)
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

    def _program_auto_comp_basic_linked(self, minSize, final_wfms, final_mkrs):
        #TODO: Add flags for changed/requires-update to ensure that segments in sequence are not unnecessary programmed repeatedly...
        #TODO: Improve algorithm (a winter research project for a Winter Student!)
        num_channels = len(final_wfms)
        dS = minSize
        num_main_secs = int(np.floor(final_wfms[0].size / dS))
        #The following variables are representative across all channels.
        seq_segs = [[final_wfm_for_chan[0:dS]] for final_wfm_for_chan in final_wfms]                #Slice: channel, waveform-segment, waveform-pts
        seq_mkrs = [[self._extract_marker_segments(mkr_list, 0, dS)] for mkr_list in final_mkrs]    #Slice: channel, marker-segment, marker-index, marker-pts
        seq_ids  = [0]
        for m in range(1,num_main_secs):
            #Extract current dS slice of the final waveforms and markers across all channels
            cur_seg = [final_wfm_for_chan[(m*dS):((m+1)*dS)] for final_wfm_for_chan in final_wfms]
            cur_mkrs = [self._extract_marker_segments(mkr_list, m*dS, (m+1)*dS) for mkr_list in final_mkrs]
            #Check for a match in a previous segment
            for seg_ind in range(len(seq_segs[0])):     #Loop through all previous segments
                found_match = True
                for cur_ch in range(num_channels):   #For each segment to check, check across all channels
                    #Check main waveform array
                    if np.array_equal(cur_seg[cur_ch], seq_segs[cur_ch][seg_ind]):
                        #Check the sub-markers
                        mkrs_match = True
                        for mkr in range(len(cur_mkrs[cur_ch])):
                            if not np.array_equal(seq_mkrs[cur_ch][seg_ind][mkr], cur_mkrs[cur_ch][mkr]):
                                mkrs_match = False
                                break
                        #If for the current channel, the markers do not match, move onto the next segment...
                        if not mkrs_match:
                            found_match = False
                            break
                    else:
                        found_match = False
                        break
                if found_match:
                    seq_ids += [seg_ind]
                    break
            if not found_match:
                seq_ids += [len(seq_segs[0])]
                for cur_ch in range(num_channels):
                    seq_segs[cur_ch] += [cur_seg[cur_ch]]
                    seq_mkrs[cur_ch] += [cur_mkrs[cur_ch]]
        if (m+1)*dS < final_wfms[0].size:
            #Reverse it if it was matched against some other segment previously...
            cur_mkrs = [self._extract_marker_segments(mkr_list, m*dS, mkr_list[0].size) for mkr_list in final_mkrs]
            if found_match:
                seq_ids[-1] = len(seq_segs)
                for cur_ch in range(num_channels):
                    seq_segs[cur_ch] += [final_wfms[cur_ch][(m*dS):]]
                    seq_mkrs[cur_ch] += [cur_mkrs[cur_ch]]
            else:
                for cur_ch in range(num_channels):
                    seq_segs[cur_ch][-1] = final_wfms[cur_ch][(m*dS):]
                    seq_mkrs[cur_ch][-1] = cur_mkrs[cur_ch]

        return [{'waveforms' : seq_segs[cur_ch], 'markers' : seq_mkrs[cur_ch], 'seq_ids' : seq_ids} for cur_ch in range(num_channels)]



class WaveformAWG(HALbase, TriggerOutputCompatible, TriggerInputCompatible, AWGBase):
    def __init__(self, hal_name, lab, awg_channel_tuples, sample_rate, total_time=-1, global_factor = 1.0):
        HALbase.__init__(self, hal_name)
        AWGBase.__init__(self, sample_rate, total_time, global_factor)
        if not lab._HAL_exists(hal_name):
            #awg_channel_tuples is given as (instr_AWG_name, channel_name)
            self._awg_chan_list = []
            assert isinstance(awg_channel_tuples, list), "The parameter awg_channel_tuples must be a LIST of TUPLEs of form (instr_AWG_name, channel_name)."
            for ch_index, cur_ch_tupl in enumerate(awg_channel_tuples):
                assert len(cur_ch_tupl) == 2, "The list awg_channel_tuples must contain tuples of form (instr_AWG_name, channel_name)."
                cur_awg_name, cur_ch_name = cur_ch_tupl            
                self._awg_chan_list.append(AWGOutputChannel(lab, cur_awg_name, cur_ch_name, ch_index, self, sample_rate))
        else:
            assert len(awg_channel_tuples) == len(self._awg_chan_list), "Cannot reinstantiate a waveform by the same name, but different channel configurations."
            for ch_index, cur_ch_tupl in enumerate(awg_channel_tuples):
                assert lab._get_instrument(cur_ch_tupl[0]) == self._awg_chan_list[ch_index]._instr_awg, "Cannot reinstantiate a waveform by the same name, but different channel configurations."
                assert cur_ch_tupl[1] == self._awg_chan_list[ch_index]._channel_name, "Cannot reinstantiate a waveform by the same name, but different channel configurations."
                self._awg_chan_list[ch_index].update_sample_rate(sample_rate)
        self._trig_src_pol = 1
        self._lab = lab
        self._cur_prog_waveforms = [None]*len(awg_channel_tuples)
        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        awg_channel_tuples = []
        for cur_ch_dict in config_dict['OutputChannels']:
            awg_channel_tuples += [(cur_ch_dict['InstrumentAWG'], cur_ch_dict['InstrumentChannel'])]
        return cls(config_dict["Name"], lab,
                    awg_channel_tuples,
                    config_dict["SampleRate"],
                    config_dict["TotalTime"],
                    config_dict["global_factor"])

    def _get_child(self, tuple_name_group):
        cur_name, cur_type = tuple_name_group
        if cur_type == 'w':
            for cur_wfm in self._wfm_segment_list:
                if cur_wfm.Name == cur_name:
                    return cur_wfm
            return None
        elif cur_type == 'c':
            for cur_ch in self._awg_chan_list:
                if cur_ch.Name == cur_name:
                    return cur_ch
            return None
        return None

    def clear_segments(self):
        self._wfm_segment_list.clear()

    def set_waveform_segments(self, wfm_segment_list):
        self._wfm_segment_list = wfm_segment_list[:]
        #NOTE: THIS WORKS BECAUSE WAVEFORM SEGMENTS CANNOT BE SHARED ACROSS WAVEFORM HALS - THIS IS WHY IT'S a COPY [:] OPERATION!
        for cur_wfm in self._wfm_segment_list:
            cur_wfm.Parent = (self, 'w')
            cur_wfm._lab = self._lab

    def add_waveform_segment(self, wfm_segment):
        self._wfm_segment_list.append(wfm_segment)
        wfm_segment.Parent = (self, 'w')
        wfm_segment._lab = self._lab
        
    def get_waveform_segment(self, wfm_segment_name):
        the_seg = None
        for cur_seg in self._wfm_segment_list:
            if cur_seg.Name == wfm_segment_name:
                the_seg = cur_seg
                break
        assert the_seg != None, "Waveform Segment of name " + wfm_segment_name + " is not present in the current list of added Waveform Segments."
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
        assert isinstance(trig_src_obj, TriggerOutput) or trig_src_obj == None, "Must supply a valid Trigger Output object (i.e. digital trigger output like a marker)."
        for cur_ch in self._awg_chan_list:
            cur_ch.set_trigger_source(trig_src_obj, trig_pol)

    def null_all_markers(self):
        for cur_output in self._awg_chan_list:
            cur_output.null_all_markers()

    def _get_trigger_output_by_id(self, outputID):
        #Doing it this way as the naming scheme may change in the future - just flatten list and find the marker object...
        cur_obj = None
        assert type(outputID) is list or type(outputID) is tuple, "ch_ID must be a list/tuple of 2 elements (channel index and marker index)."
        if len(outputID) == 3:  #For backwards compatibility with old format. Now triplet format should cover any new changes hopefully...
            assert isinstance(outputID[2], str), "The outputID must be (channel index, trigger index, trigger type) where the type is a string like 'v'."
            #Process software trigger
            ch_ID = outputID[0]
            trg_ID = outputID[1]
            assert ch_ID >= 0 and ch_ID < len(self._awg_chan_list), "ch_ID must be a valid channel index."
            assert trg_ID >= 0 and trg_ID < len(self.get_output_channel(ch_ID)._software_triggers), "Trigger index must be a valid software trigger index (check number of initialised software triggers)."
            cur_obj = self.get_output_channel(ch_ID)._software_triggers[trg_ID]
        else:
            assert len(outputID) == 2, "ch_ID must be a list/tuple of 2 elements (channel index and marker index)."
            #Process hardware channel marker
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
            for m in range(len(cur_chan._software_triggers)):
                mkr_output_ids.append((chan_ind, m, 'v'))
        return mkr_output_ids
        #TODO: Consider additional trigger outputs (e.g. AUX)?

    def _get_all_trigger_inputs(self):
        trig_inp_objs = []
        for cur_chan in self._awg_chan_list:
            trig_inp_objs += [cur_chan]
            trig_inp_objs += cur_chan.get_all_markers()
            trig_inp_objs += cur_chan.get_all_software_triggers()
        return trig_inp_objs

    def __str__(self):
        ret_str = ""
        ret_str += f'Name: {self.Name}\n'
        ret_str += f'Type: {self.__class__.__name__}\n'
        ret_str += f'SampleRate: {self.SampleRate}\n'
        ret_str += f'TotalTime: {self._total_time}\n'
        ret_str += f'global_factor: {self._global_factor}\n'
        ret_str += f'Waveform Segments:\n'
        seg_data = self._get_current_config_waveforms()
        for cur_seg in seg_data:
            cur_name = cur_seg.pop('Name')
            cur_type = cur_seg.pop('Type')
            cur_seg.pop('Mod Func')
            ret_str += f'\t{cur_type}, {cur_name}, {cur_seg}\n'
        return ret_str

    def _get_current_config(self):
        retDict = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__,
            'SampleRate' : self.SampleRate,
            'TotalTime' : self._total_time,
            'global_factor' : self._global_factor,
            'AutoCompression' : self.AutoCompression,
            'AutoCompressionLinkChannels' : self.AutoCompressionLinkChannels,
            'OutputChannels' : [x._get_current_config() for x in self._awg_chan_list],
            'ManualActivation' : self.ManualActivation
            }
        retDict['WaveformSegments'] = self._get_current_config_waveforms()
        return retDict

    def _get_current_config_waveforms(self):
        #Write down the waveform-segment data - can be overwritten by the daughter class for a different format if required/desired...
        return [x._get_current_config() for x in self._wfm_segment_list]
    
    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a AWG with a configuration that is of type ' + dict_config['Type']
        
        self._sample_rate = dict_config['SampleRate']
        self._total_time = dict_config['TotalTime']
        self._global_factor = dict_config['global_factor']
        self.AutoCompression = dict_config['AutoCompression']
        self.AutoCompressionLinkChannels = dict_config['AutoCompressionLinkChannels']
        self.ManualActivation = dict_config.get('ManualActivation', False)
        for ind, cur_ch_output in enumerate(dict_config['OutputChannels']):
            self._awg_chan_list[ind]._set_current_config(cur_ch_output, lab)

        self._set_current_config_waveforms(dict_config['WaveformSegments'])

        #This function is called via init_instruments in the ExperimentConfiguration class right at the BEGINNING of an Experiment
        #run - it's dangerous to assume concurrence with previous waveforms here...
        self._cur_prog_waveforms = [None]*len(self._awg_chan_list)

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
            cur_wfm_type = cur_wfm['Type']
            assert cur_wfm_type in globals(), cur_wfm_type + " is not in the current namespace. If the class does not exist in WaveformSegments include wherever it lives by importing it in AWG.py."
            cur_wfm_type = globals()[cur_wfm_type]
            new_wfm_seg = cur_wfm_type.fromConfigDict(cur_wfm)
            new_wfm_seg.Parent = (self, 'w')
            self._wfm_segment_list.append(new_wfm_seg)

    def plot_waveforms(self, overlap=False):
        final_wfms = self._assemble_waveform_raw()[0]
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

    def activate(self):
        for cur_awg_chan in self._awg_chan_list:
            cur_awg_chan.Output = True

    def deactivate(self):
        for cur_awg_chan in self._awg_chan_list:
            cur_awg_chan.Output = False

    def get_raw_waveforms(self):
        return self._assemble_waveform_raw()[0]

    def prepare_initial(self):
        """
        Method to prepare waveforms and load them into memory of AWG intsrument
        """
        #Prepare the waveform
        final_wfms, elastic_ind = self._assemble_waveform_raw()

        #Ensure that the number of points in the waveform satisfies the AWG memory requirements...
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            mem_params = cur_awg_chan._instr_awg.MemoryRequirements
            num_pts = final_wfms[ind].size
            assert num_pts >= mem_params['MinSize'], f"Waveform too short; needs to have at least {mem_params['MinSize']} points."
            assert num_pts % mem_params['Multiple'] == 0, f"Number of points in waveform needs to be a multiple of {mem_params['Multiple']}."

        #Assemble markers
        final_mkrs = []
        for ind, cur_awg_chan in enumerate(self._awg_chan_list):
            if len(cur_awg_chan._awg_mark_list) > 0:
                mkr_list = [x._assemble_marker_raw() for x in cur_awg_chan._awg_mark_list]
            else:
                mkr_list = [np.array([])]
            final_mkrs += [mkr_list]

        #Check if there are any changes in the waveforms - if not, then there's no need to reprogram...
        self._dont_reprogram = True
        for m in range(len(self._cur_prog_waveforms)):
            if self._cur_prog_waveforms[m] is not None:
                if not self._check_changes_wfm_data(self._cur_prog_waveforms[m], final_wfms[m], final_mkrs[m]):
                    self._dont_reprogram = False
                    break
            else:
                self._dont_reprogram = False
                break
        if self._dont_reprogram:
            return

        #For the case where the sequencing table must be the same for all channels (e.g. channels on the Agilent N8241A), the sequencing is
        #done on all the waveforms across all channels
        if self.AutoCompressionLinkChannels and self.AutoCompression != 'None':
            assert self.AutoCompression == 'Basic', "Only the \'Basic\' algorithm is currently supported for linked-channel auto-compression."
            self.cur_wfms_to_commit = []
            #Check that the memory requirements are the same across all channels (i.e. typically the same AWG)
            dict_auto_comps = [cur_awg_chan._instr_awg.AutoCompressionSupport for cur_awg_chan in self._awg_chan_list]
            for cur_key in dict_auto_comps[0]:
                for cur_dict in dict_auto_comps:
                    assert cur_dict[cur_key] == dict_auto_comps[0][cur_key], f"Linked-channel auto-compression requires all channels to have the same {cur_key}."
            #Perform BASIC compression on all the channels simultaneously...
            dict_wfm_datas = self._program_auto_comp_basic_linked(dict_auto_comps[0]['MinSize'], final_wfms, final_mkrs)
            for ind, cur_awg_chan in enumerate(self._awg_chan_list):
                dict_wfm_data = dict_wfm_datas[ind]
                seg_lens = [x.size for x in dict_wfm_data['waveforms']]
                cur_awg_chan._instr_awg.prepare_waveform_memory(cur_awg_chan._instr_awg_chan.short_name, seg_lens, raw_data=dict_wfm_data)
                self.cur_wfms_to_commit.append(dict_wfm_data)
        else:
            self.cur_wfms_to_commit = []
            for ind, cur_awg_chan in enumerate(self._awg_chan_list):
                mkr_list = final_mkrs[ind]
                    
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
        """
        Method that programs waveform onto channel
        """
        if not self._dont_reprogram:
            for ind, cur_awg_chan in enumerate(self._awg_chan_list):
                cur_awg_chan._instr_awg.program_channel(cur_awg_chan._instr_awg_chan.short_name, self.cur_wfms_to_commit[ind])
                #Set it AFTER the programming in case there is an error etc...
                self._cur_prog_waveforms[ind] = self.cur_wfms_to_commit[ind]

class AWGOutputChannel(TriggerInput, LockableProperties):
    def __init__(self, lab, instr_awg_name, channel_name, ch_index, parent_awg_waveform, sample_rate):
        self._instr_awg_name = instr_awg_name
        self._channel_name = channel_name
        self._ch_index = ch_index

        instr_awg = lab._get_instrument(instr_awg_name)
        self._instr_awg = instr_awg
        self._instr_awg_chan = instr_awg._get_channel_output(channel_name)
        assert self._instr_awg_chan != None, "The channel name " + channel_name + " does not exist in the AWG instrument " + self._instr_awg.name

        #TODO: Think about whether sample-rate is a AWG-channel-level or AWG-level property - e.g. most AWGs probably enforce all output channels
        #must synchronise sample rates... Here it's treated as an AWG-level property.
        instr_awg.SampleRate = sample_rate

        self._trig_src_obj = None
        self._trig_src_pol = 1

        self._awg_mark_list = []
        self.num_markers = self._instr_awg.num_supported_markers(channel_name)
        if self.num_markers > 0:
            for ind in range(1, self.num_markers+1):
                self._awg_mark_list.append(AWGOutputTrigger(parent_awg_waveform, self, f'{channel_name}_mkr{ind}', ind-1))
        self._software_triggers = []
        self._parent_waveform_obj = parent_awg_waveform

    @property
    def Name(self):
        return self._channel_name

    @property
    def Parent(self):
        return (self._parent_waveform_obj, 'c')

    def _get_child(self, tuple_name_group):
        cur_name = tuple_name_group[0]
        for cur_mkr in self._awg_mark_list:
            if cur_mkr.Name == cur_name:
                return cur_mkr
        return None

    @property
    def Amplitude(self):
        return self._instr_awg_chan.Amplitude
    @Amplitude.setter
    def Amplitude(self, val):
        self._instr_awg_chan.Amplitude = val
        
    @property
    def Offset(self):
        return self._instr_awg_chan.Offset
    @Offset.setter
    def Offset(self, val):
        self._instr_awg_chan.Offset = val
        
    @property
    def Output(self):
        return self._instr_awg_chan.Output
    @Output.setter
    def Output(self, boolVal):
        self._instr_awg_chan.Output = boolVal

    @property
    def InputTriggerEdge(self):
        return self._trig_src_pol
    @InputTriggerEdge.setter
    def InputTriggerEdge(self, pol):
        self._trig_src_pol = pol

    def _get_instr_trig_src(self):
        return self.get_trigger_source()
    def _get_instr_input_trig_edge(self):
        return self.InputTriggerEdge
    def _get_timing_diagram_info(self):
        resolution = 21
        sample_rate = self._parent_waveform_obj.SampleRate
        seg_dicts = []
        t0 = 0
        elas_seg_ind, elastic_time = self._parent_waveform_obj._get_elastic_time_seg_params()
        for m, cur_wfm_seg in enumerate(self._parent_waveform_obj._wfm_segment_list):
            cur_dict = {}
            if elas_seg_ind == m:
                cur_dict['Duration'] = elastic_time
                cur_wfm_seg.Duration = elastic_time
            else:
                cur_dict['Duration'] = cur_wfm_seg.Duration
            #TODO: Use _get_waveform to yield the unmodified waveform (i.e. just envelope) if some flag is set
            cur_y = cur_wfm_seg.get_waveform(self._parent_waveform_obj._lab, sample_rate, t0, self._ch_index)
            t0 += cur_wfm_seg.NumPts(sample_rate) / sample_rate
            if elas_seg_ind == m:
                cur_wfm_seg.Duration = -1
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
            cur_dict['yPoints'] = scipy.signal.resample(cur_y, resolution)
            seg_dicts.append(cur_dict)

        if len(seg_dicts) == 0:
            return {'Type' : 'None'}    #Inactive waveform without any non-zero segments...
        return {'Type' : 'AnalogueSampled', 'Period' : self._parent_waveform_obj.Duration, 'Data' : seg_dicts}

    def update_sample_rate(self, sample_rate):
        self._instr_awg.SampleRate = sample_rate

    def set_trigger_source(self, trig_src_obj, trig_pol = -1):
        assert isinstance(trig_src_obj, TriggerOutput) or trig_src_obj == None, "Must supply a valid Trigger Output object (i.e. digital trigger output like a marker)."
        self._trig_src_obj = trig_src_obj
        if trig_pol != -1:
            self.InputTriggerEdge = trig_pol

    def get_trigger_source(self):
        '''
        Get the Trigger object corresponding to the trigger source.
        '''
        return self._trig_src_obj

    def null_all_markers(self):
        for cur_mark in self._awg_mark_list:
            cur_mark.set_markers_to_none()

    def marker(self, marker_index):
        '''
        Returns an AWGOutputTrigger object for a hardware marker.
        '''
        assert marker_index >= 0 and marker_index < len(self._awg_mark_list), "Marker output index is out of range"
        return self._awg_mark_list[marker_index]

    def reset_software_triggers(self, num_triggers=0):
        while len(self._software_triggers) > 0:
            obj = self._software_triggers.pop()
            del obj
        for m in range(num_triggers):
            self._software_triggers.append(AWGOutputTrigger(self._parent_waveform_obj, self, f'soft_trig_{m}', m))

    def software_trigger(self, soft_trig_index):
        '''
        Returns an AWGOutputTrigger object for a software trigger.
        '''
        assert soft_trig_index >= 0 and soft_trig_index < len(self._software_triggers), "Software trigger output index is out of range. Perhaps reset_software_triggers has not been run?"
        return self._software_triggers[soft_trig_index]

    def get_all_markers(self):
        return self._awg_mark_list[:]
    
    def get_all_software_triggers(self):
        return self._software_triggers[:]

    def _get_current_config(self):
        retDict = {
            'Name' : self.Name,
            'InstrumentAWG' : self._instr_awg_name,
            'InstrumentChannel' : self._channel_name,
            'Amplitude' : self.Amplitude,
            'Offset' : self.Offset,
            'Output' : self.Output,
            'InputTriggerEdge' : self.InputTriggerEdge,
            'Markers' : [x._get_current_config() for x in self._awg_mark_list],
            'SoftwareTriggers' : [x._get_current_config() for x in self._software_triggers]
            }
        if self._trig_src_obj:
            retDict['TriggerSource'] = self._get_trig_src_params_dict()
        return retDict

    def _set_current_config(self, dict_config, lab):
        assert self._instr_awg_name == dict_config['InstrumentAWG'], "Instrument names do not match for this output-channel definition."
        assert self._channel_name == dict_config['InstrumentChannel'], "Instrument channel names do not match for this output-channel definition."
        self._channel_name = dict_config['Name']
        self.Amplitude = dict_config['Amplitude']
        self.Offset = dict_config['Offset']
        self.Output = dict_config['Output']       
        #
        if 'TriggerSource' in dict_config:
            trig_src_obj = TriggerInput.process_trigger_source(dict_config['TriggerSource'], lab)
            self.set_trigger_source(trig_src_obj, dict_config['InputTriggerEdge'])
        #
        for ind, cur_mark_dict in enumerate(dict_config['Markers']):
            self._awg_mark_list[ind]._set_current_config(cur_mark_dict)
        soft_trigs = dict_config.get('SoftwareTriggers', [])
        self.reset_software_triggers(len(soft_trigs))
        for ind, cur_mark_dict in enumerate(soft_trigs):
            self._software_triggers[ind]._set_current_config(cur_mark_dict)

class AWGOutputTrigger(TriggerOutput, TriggerInput, LockableProperties):
    def __init__(self, parent_waveform_obj, awg_output_ch, name, ch_index):
        self._parent_waveform_obj = parent_waveform_obj
        self._awg_output_ch = awg_output_ch
        assert isinstance(self._awg_output_ch, (AWGOutputChannel, WaveformAWG)), "The awg_output_ch argument must be an AWGOutputChannel type if hardware marker or WaveformAWG itself if software trigger."

        #Marker status can be Arbitrary, Segments, None, Trigger
        self._marker_status = 'Arbitrary'
        self._marker_pol = 1
        self._marker_arb_array = np.array([], dtype=np.ubyte)
        self._marker_seg_list = []
        self._marker_trig_delay = 0.0
        self._marker_trig_length = 1e-9
        self._ch_index = ch_index
        self._name = name

    @property
    def Name(self):
        return self._name

    @property
    def Parent(self):
        return (self._awg_output_ch, None)
    
    @property
    def IsVirtual(self):
        return self._parent_waveform_obj == self._awg_output_ch

    def set_markers_to_segments(self, list_seg_names):
        self._marker_status = 'Segments'
        #Check the listed segments actually exist in the current list of WaveformSegment objects
        assert len(self._parent_waveform_obj._wfm_segment_list) > 0, "Must add segments to the waveform before setting markers to segments."
        for cur_seg_name in list_seg_names:
            found_seg = None
            for cur_seg_chk in self._parent_waveform_obj._wfm_segment_list:
                if type(cur_seg_name) == list:
                    cur_check = cur_seg_name[0]
                else:
                    cur_check = cur_seg_name
                if cur_seg_chk.Name == cur_check:
                    found_seg = cur_seg_chk
                    break
            assert found_seg != None, "WaveformSegment " + cur_check + " has not been added to this Waveform sequence."
        self._marker_seg_list = list_seg_names[:] #Copy over the list

    def set_markers_to_arbitrary(self, arb_mkr_list):
        self._marker_arb_array = arb_mkr_list[:]
        self._marker_status = 'Arbitrary'
    
    def set_markers_to_trigger(self):
        '''
        Enables one to set the markers via its associated Trigger object attributes.
        '''
        self._marker_status = 'Trigger'
    
    def set_markers_to_none(self):
        self._marker_status = 'None'

    @property
    def TrigPulseDelay(self):
        self._validate_trigger_parameters()
        return self._marker_trig_delay
    @TrigPulseDelay.setter
    def TrigPulseDelay(self, len_seconds):
        assert self._marker_status == 'Trigger', "Cannot manipulate the marker waveforms on an AWG channel like a Trigger pulse without being in Trigger mode (i.e. call set_markers_to_trigger)"
        self._marker_trig_delay = len_seconds

    @property
    def TrigPulseLength(self):
        self._validate_trigger_parameters()
        return self._marker_trig_length
    @TrigPulseLength.setter
    def TrigPulseLength(self, len_seconds):
        assert self._marker_status == 'Trigger', "Cannot manipulate the marker waveforms on an AWG channel like a Trigger pulse without being in Trigger mode (i.e. call set_markers_to_trigger)"
        self._marker_trig_length = len_seconds

    @property
    def TrigPolarity(self):
        '''
        Returns the Trigger Polarity (positive or negative - 1 or 0). Only relevant if in Trigger and Segment modes.
        '''
        return self._marker_pol
    @TrigPolarity.setter
    def TrigPolarity(self, pol):
        '''
        Sets the Trigger Polarity (positive or negative - 1 or 0). Only relevant if in Trigger and Segment modes.
        '''
        self._marker_pol = pol

    @property
    def TrigEnable(self):
        return self._instrTrig.TrigEnable
    @TrigEnable.setter
    def TrigEnable(self, boolVal):
        self._instrTrig.TrigEnable = boolVal

    def _validate_trigger_parameters(self):
        #Validation need not occur if in Trigger mode. But the other modes need to be checked if the marker
        #waveform satisfies a proper trigger waveform...
        if self._marker_status == 'Segments' or self._marker_status == 'Arbitrary':
            mkr_array = self._assemble_marker_raw()
            prev_val = mkr_array[0]
            changes = []
            for ind, cur_val in enumerate(mkr_array):
                if (cur_val != prev_val):
                    changes += [ind]
                    prev_val = cur_val
            assert len(changes) <= 2, "The marker waveform has too many changing edges to constitute a valid trigger"
            #Set the trigger parameters
            if mkr_array[0] == 0:
                self._marker_pol = 1
            else:
                self._marker_pol = 0
            if len(changes) == 0:
                self._marker_trig_delay = 0
                self._marker_trig_length = 0
            elif len(changes) == 1:
                self._marker_trig_delay = changes[0] * self._parent_waveform_obj._sample_rate
                self._marker_trig_length = self.Duration - self._marker_trig_delay
            else:
                self._marker_trig_delay = changes[0] * self._parent_waveform_obj._sample_rate
                self._marker_trig_length = changes[1] * self._parent_waveform_obj._sample_rate - self._marker_trig_delay
        elif self._marker_status == 'None':
            self._marker_trig_delay = 0
            self._marker_trig_length = 0

    def _assemble_marker_raw(self):
        if self._marker_status == 'None':
            return np.array([], dtype=np.ubyte)

        if self._marker_status == 'Trigger':
            final_wfm = np.zeros(int(np.round(self._parent_waveform_obj.NumPts)), dtype=np.ubyte) + 1 - self._marker_pol
            start_pt = int(np.round(self._marker_trig_delay * self._parent_waveform_obj._sample_rate))
            end_pt = int(np.round((self._marker_trig_delay + self._marker_trig_length) * self._parent_waveform_obj._sample_rate))
            final_wfm[start_pt:end_pt+1] = self._marker_pol
            return final_wfm
        elif self._marker_status == 'Arbitrary':
            return self._marker_arb_array
        elif self._marker_status == 'Segments':
            return self._parent_waveform_obj._get_marker_waveform_from_segments(self._marker_seg_list)

    def get_raw_trigger_waveform(self):
        return self._assemble_marker_raw()

    def get_trigger_id(self):
        return [self._awg_output_ch._ch_index, self._ch_index]
    def _get_instr_trig_src(self):
        '''
        Used by TimingConfiguration to backtrack through all interdependent trigger sources (i.e. traversing up the tree)
        '''
        #Channel index is used in the cases where the trigger sources may be different (e.g. IQ waveform with I and Q from different AWGs)
        return self._awg_output_ch.get_trigger_source()
    def _get_instr_input_trig_edge(self):
        return self._awg_output_ch.InputTriggerEdge
    def _get_timing_diagram_info(self):
        mkr_array = self._assemble_marker_raw()
        if mkr_array.size == 0:
            return {'Type' : 'None'}
        sample_rate = self._parent_waveform_obj.SampleRate
        return {'Type' : 'DigitalSampled', 'Period' : mkr_array.size / sample_rate, 'Data' : (mkr_array, sample_rate), 'TriggerType' : 'Edge'}

    def get_trigger_times(self, input_trig_pol=1):
        if self._marker_status == 'None':
            return ([],[])

        assert input_trig_pol == 0 or input_trig_pol == 1, "Trigger polarity must be 0 or 1 for negative or positive edge/polarity."

        if self._marker_status == 'Trigger':
            if input_trig_pol == 0:
                if self.TrigPolarity == 0:
                    return ([self.TrigPulseDelay], np.array([[self.TrigPulseDelay, self.TrigPulseDelay+self.TrigPulseLength]]) )
                else:
                    return ([self.TrigPulseDelay + self.TrigPulseLength], np.array([[0.0, self.TrigPulseDelay]]) )
            elif input_trig_pol == 1:
                if self.TrigPolarity == 0:
                    return ([self.TrigPulseDelay + self.TrigPulseLength], np.array([[0.0, self.TrigPulseDelay]]) )
                else:
                    return ([self.TrigPulseDelay], np.array([[self.TrigPulseDelay, self.TrigPulseDelay+self.TrigPulseLength]]) )
        elif self._marker_status == 'Arbitrary' or self._marker_status == 'Segments':
            #TODO: Consider handling Segments by itself without assembling whole array - a small optimisation...
            cur_fs = self._parent_waveform_obj._sample_rate
            mark_arr = self._assemble_marker_raw()
            edges = mark_arr-np.roll(mark_arr,1)    #It's 1 if it's a positive edge, -1 if negative edge
            edges = edges.astype(np.ubyte)  #Just to be sure as marker is a ubyte array and -1 is 255 in ubytes; in case it changes in the future...
            posedges = np.where(edges==1)[0] / cur_fs
            negedges = np.where(edges==255)[0] / cur_fs
            if input_trig_pol == 1:
                times = posedges
                if times.size == 0:
                    segs = np.array([])
                elif posedges[0] < negedges[0]:
                    segs = np.vstack([posedges,negedges]).T
                else:
                    segs = np.vstack([np.append(0.0, posedges),np.append(negedges, mark_arr.size/cur_fs)]).T
            else:
                times = negedges
                if times.size == 0:
                    segs = np.array([])
                elif posedges[0] > negedges[0]:
                    segs = np.vstack([negedges,posedges]).T
                else:
                    segs = np.vstack([np.append(0.0, negedges),np.append(posedges, mark_arr.size/cur_fs)]).T
            if segs.size > 0 and np.abs(segs[0,0] - segs[0,1]) < 1e-16:
                segs = segs[1:,:]
            return (times.tolist(), segs)

    def _get_parent_HAL(self):
        return self._parent_waveform_obj
    
    def _get_current_config(self):
        retDict = {
            'Name' : self._name,
            'Channel Index' : self._ch_index,
            'Status' : self._marker_status,
            'Polarity' : self._marker_pol,
            'Arbitrary Array' : self._marker_arb_array.tolist(),
            'Segment List' : self._marker_seg_list,
            'Trigger Delay' : self._marker_trig_delay,
            'Trigger Length' : self._marker_trig_length
            }
        return retDict

    def _set_current_config(self, dict_config):
        errMsg = "The order of the markers for the given output channel has changed in the configuration. The marker configuration list must match the order of the markers in the channel to be updated."
        assert self._name == dict_config['Name'], errMsg
        assert self._ch_index == dict_config['Channel Index'], errMsg

        self._marker_status = dict_config['Status']
        self._marker_pol = dict_config['Polarity']
        self._marker_arb_array = np.array(dict_config['Arbitrary Array'], dtype=np.ubyte)
        self._marker_seg_list = dict_config['Segment List']
        self._marker_trig_delay = dict_config['Trigger Delay']
        self._marker_trig_length = dict_config['Trigger Length']
