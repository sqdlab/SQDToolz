from sqdtoolz.HAL.AWG import AWGBase, AWGOutputChannel
from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.HAL.TriggerPulse import TriggerInput, TriggerInputCompatible
import numpy as np

class GENmwSrcAWGchannel(TriggerInput):
    def __init__(self, parent):
        self._frequency = 100e9
        self._power = 0
        self._parent = parent
        self._trig_src_pol = 1
    
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
        raise self.InputTriggerEdge
    
    def _get_timing_diagram_info(self):
        if self.Mode == 'PulseModulated':
            return {'Type' : 'BlockShaded', 'TriggerType' : 'Gated'}
        else:
            return {'Type' : 'None'}



class GENmwSrcAWG(AWGBase, TriggerInputCompatible):
    def __init__(self, hal_name, lab, awg_channel_tuple, num_tones, sample_rate, total_time=0):
        AWGBase.__init__(self, hal_name, sample_rate, total_time, global_factor=1.0)
        assert len(awg_channel_tuple) == 2, "The argument awg_channel_tuple must be a tuple of form (instr_AWG_name, channel_name)."
        cur_awg_name, cur_ch_name = awg_channel_tuple            
        self._awg_chan_list.append(AWGOutputChannel(lab, cur_awg_name, cur_ch_name, 0, self, sample_rate))

        assert num_tones > 0, "The argument num_tones must be greater than 0."
        self._rf_channels = [GENmwSrcAWGchannel(self) for x in range(num_tones)]
    
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
        final_wfm_raw = np.zeros(self.NumPts)
        
        for cur_rf_ch in self._rf_channels:
            volt_amplitude = np.sqrt(0.001 * 10**(cur_rf_ch.Power/10) * 50 * 2) #sqrt(2) for RMS...
            edges, gates = cur_rf_ch.get_trigger_source().get_trigger_times()
            for cur_gate in gates:
                start_ind, end_ind = cur_gate
                final_wfm_raw[start_ind:end_ind+1] += volt_amplitude * np.cos(2*np.pi*cur_rf_ch.Frequency * np.arange(end_ind - start_ind + 1)/self.SampleRate)

        return np.array([final_wfm_raw])        


