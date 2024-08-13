from sqdtoolz.HAL.AWG import AWGBase, AWGOutputChannel
from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.HAL.TriggerPulse import TriggerInput, TriggerInputCompatible, TriggerOutput
import numpy as np

class GENmwSrcAWGchannel(TriggerInput):
    def __init__(self, parent, name):
        self._frequency = 100e9
        self._power = 0
        self._parent = parent
        self._trig_src_pol = 1
        self._trig_src_obj = None
        self._name = name
    
    @property
    def Name(self):
        return self._name

    @property
    def Frequency(self):
        return self._frequency
    @Frequency.setter
    def Frequency(self, val):
        self._frequency = val

    @property
    def Power(self):
        return self._power
    @Power.setter
    def Power(self, val):
        self._power = val

    @property
    def InputTriggerEdge(self):
        return self._trig_src_pol
    @InputTriggerEdge.setter
    def InputTriggerEdge(self, pol):
        self._trig_src_pol = pol

    def get_trigger_source(self):
        '''
        Get the Trigger object corresponding to the trigger source.
        '''
        return self._trig_src_obj

    def _get_instr_trig_src(self):
        return self.get_trigger_source()

    def _get_instr_input_trig_edge(self):
        return self.InputTriggerEdge
    
    def _get_timing_diagram_info(self):
        return {'Type' : 'BlockShaded', 'TriggerType' : 'Gated'}

    def _get_current_config(self):
        retDict = {
            'Frequency' : self.Frequency,
            'Power' : self.Power,
            'InputTriggerEdge' : self.InputTriggerEdge
            }
        if self._trig_src_obj:
            retDict['TriggerSource'] = self._get_trig_src_params_dict()
        return retDict
  
    def _set_current_config(self, dict_config, lab):
        self.Frequency = dict_config['Frequency']
        self.Power = dict_config['Power']
        self.InputTriggerEdge = dict_config['InputTriggerEdge']
        if 'TriggerSource' in dict_config:
            trig_src_obj = TriggerInput.process_trigger_source(dict_config['TriggerSource'], lab)
            self.set_trigger_source(trig_src_obj, dict_config['InputTriggerEdge'])

    def set_trigger_source(self, trig_src_obj, trig_pol = -1):
        assert isinstance(trig_src_obj, TriggerOutput) or trig_src_obj == None, "Must supply a valid Trigger Output object (i.e. digital trigger output like a marker or a software trigger)."
        self._trig_src_obj = trig_src_obj
        if trig_pol != -1:
            self.InputTriggerEdge = trig_pol

class GENmwSrcAWG(AWGBase, TriggerInputCompatible):
    def __init__(self, hal_name, lab, awg_channel_tuple, num_tones, sample_rate, total_time=0):
        AWGBase.__init__(self, hal_name, sample_rate, total_time, global_factor=1.0)
        assert len(awg_channel_tuple) == 2, "The argument awg_channel_tuple must be a tuple of form (instr_AWG_name, channel_name)."
        cur_awg_name, cur_ch_name = awg_channel_tuple            
        self._awg_chan_list.append(AWGOutputChannel(lab, cur_awg_name, cur_ch_name, 0, self, sample_rate))

        assert num_tones > 0, "The argument num_tones must be greater than 0."
        self._rf_channels = [GENmwSrcAWGchannel(self, f'Tone{x}') for x in range(num_tones)]

        lab._register_HAL(self)
    
    def get_rf_channel(self, chan_id):
        assert chan_id >= 0 and chan_id < len(self._rf_channels), f"chan_id must be a valid zero-based index for the number of RF channels ({len(self._rf_channels)} in this case)."
        return self._rf_channels[chan_id]

    def _get_all_trigger_inputs(self):
        return self._rf_channels[:]

    @property
    def Duration(self):
        return self._total_time

    def _check_triggers_same_source(self):
        prev_trig_src = None
        for m, cur_rf_tone in enumerate(self._rf_channels):
            cur_trig_src = cur_rf_tone._get_instr_trig_src()
            assert cur_trig_src != None, "The trigger sources must be set for all RF channels in a GENmwSrcAWG HAL."
            if m == 0:
                prev_trig_src = cur_trig_src._get_instr_trig_src()
            assert prev_trig_src == cur_trig_src._get_instr_trig_src(), "The trigger sources for the trigger pulses driving the RF channels must be the same in a GENmwSrcAWG HAL."

    def _assemble_waveform_raw(self):
        total_pts = self.NumPts
        final_wfm_raw = np.zeros(total_pts)
        
        for cur_rf_ch in self._rf_channels:
            volt_amplitude = np.sqrt(0.001 * 10**(cur_rf_ch.Power/10) * 50 * 2) #sqrt(2) for RMS...
            edges, gates = cur_rf_ch.get_trigger_source().get_trigger_times()
            for cur_gate in gates:
                start_ind, end_ind = cur_gate
                start_ind, end_ind = int(start_ind*self.SampleRate), int(end_ind*self.SampleRate)
                end_ind = min(end_ind, total_pts-1)
                final_wfm_raw[start_ind:end_ind+1] += volt_amplitude * np.cos(2*np.pi*cur_rf_ch.Frequency * np.arange(end_ind - start_ind + 1)/self.SampleRate)

        return np.array([final_wfm_raw])        

    def _get_current_config(self):
        retDict = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__,
            'SampleRate' : self.SampleRate,
            'TotalTime' : self._total_time,
            'AutoCompression' : self.AutoCompression,
            'AutoCompressionLinkChannels' : self.AutoCompressionLinkChannels,
            'OutputChannels' : [x._get_current_config() for x in self._awg_chan_list],
            'ManualActivation' : self.ManualActivation
            }
        retDict['RFTones'] = [x._get_current_config() for x in self._rf_channels]
        return retDict
  
    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a AWG with a configuration that is of type ' + dict_config['Type']
        
        self._sample_rate = dict_config['SampleRate']
        self._total_time = dict_config['TotalTime']
        self.AutoCompression = dict_config['AutoCompression']
        self.AutoCompressionLinkChannels = dict_config['AutoCompressionLinkChannels']
        self.ManualActivation = dict_config.get('ManualActivation', False)
        for ind, cur_ch_output in enumerate(dict_config['OutputChannels']):
            self._awg_chan_list[ind]._set_current_config(cur_ch_output, lab)

        for m, x in enumerate(dict_config['RFTones']):
            self._rf_channels[m]._set_current_config(x, lab)

        #This function is called via init_instruments in the ExperimentConfiguration class right at the BEGINNING of an Experiment
        #run - it's dangerous to assume concurrence with previous waveforms here...
        self._cur_prog_waveforms = [None]*len(self._awg_chan_list)

