from sqdtoolz.HAL.TriggerPulse import*
import numpy as np
from scipy import signal

class AWGOutputChannel(TriggerInput):
    def __init__(self, lab, instr_awg_name, channel_name, ch_index, parent_awg_waveform):
        self._instr_awg_name = instr_awg_name
        self._channel_name = channel_name
        self._ch_index = ch_index

        instr_awg = lab._get_instrument(instr_awg_name)
        self._instr_awg = instr_awg
        self._instr_awg_chan = instr_awg._get_channel_output(channel_name)
        assert self._instr_awg_chan != None, "The channel name " + channel_name + " does not exist in the AWG instrument " + self._instr_awg.name

        self._trig_src_obj = None
        self._trig_src_pol = 1

        self._awg_mark_list = []
        self.num_markers = self._instr_awg.num_supported_markers(channel_name)
        if self.num_markers > 0:
            for ind in range(1, self.num_markers+1):
                self._awg_mark_list.append(AWGOutputMarker(parent_awg_waveform, self, f'{channel_name}_mkr{ind}', ind-1))
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
            cur_y = cur_wfm_seg.get_waveform(sample_rate, t0, self._ch_index)
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
            cur_dict['yPoints'] = signal.resample(cur_y, resolution)
            seg_dicts.append(cur_dict)

        if len(seg_dicts) == 0:
            return {'Type' : 'None'}    #Inactive waveform without any non-zero segments...
        return {'Type' : 'AnalogueSampled', 'Period' : self._parent_waveform_obj.Duration, 'Data' : seg_dicts}

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
        Returns an AWGOutputMarker object.
        '''
        assert marker_index >= 0 and marker_index < len(self._awg_mark_list), "Marker output index is out of range"
        return self._awg_mark_list[marker_index]

    def get_all_markers(self):
        return self._awg_mark_list[:]

    def _get_current_config(self):
        retDict = {
            'Name' : self.Name,
            'InstrumentAWG' : self._instr_awg_name,
            'InstrumentChannel' : self._channel_name,
            'Amplitude' : self.Amplitude,
            'Offset' : self.Offset,
            'Output' : self.Output,
            'InputTriggerEdge' : self.InputTriggerEdge,
            'Markers' : [x._get_current_config() for x in self._awg_mark_list]
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

class AWGOutputMarker(TriggerOutput, TriggerInput):
    def __init__(self, parent_waveform_obj, awg_output_ch, name, ch_index):
        self._parent_waveform_obj = parent_waveform_obj
        self._awg_output_ch = awg_output_ch
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

    def set_markers_to_segments(self, list_seg_names):
        self._marker_status = 'Segments'
        #Check the listed segments actually exist in the current list of WaveformSegment objects
        for cur_seg_name in list_seg_names:
            found_seg = None
            for cur_seg_chk in self._parent_waveform_obj._wfm_segment_list:
                if cur_seg_chk.Name == cur_seg_name:
                    found_seg = cur_seg_chk
                    break
            assert found_seg != None, "WaveformSegment " + cur_seg_name + " has not been added to this Waveform sequence."
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

    def get_raw_marker_waveform(self):
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
        sample_rate = self._awg_output_ch._parent_waveform_obj.SampleRate
        return {'Type' : 'DigitalSampled', 'Period' : mkr_array.size / sample_rate, 'Data' : (mkr_array, sample_rate), 'TriggerType' : 'Edge'}

    def get_trigger_times(self, input_trig_pol=1):
        if self._marker_status == 'None':
            return []

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
