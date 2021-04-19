from sqdtoolz.HAL.GEN import GEN
from sqdtoolz.HAL.TriggerPulse import*

class GENmwSource(GEN, TriggerInputCompatible, TriggerInput):
    def __init__(self, instr_gen_freq_src_channel):
        '''
        '''
        super().__init__(instr_gen_freq_src_channel.name)
        self._instr_mw_output = instr_gen_freq_src_channel
        self._trig_src_obj = None

    @property
    def Output(self):
        return self._instr_mw_output.Output
    @Output.setter
    def Output(self, val):
        self._instr_mw_output.Output = val
        
    @property
    def Power(self):
        return self._instr_mw_output.Power
    @Power.setter
    def Power(self, val):
        self._instr_mw_output.Power = val
        
    @property
    def Frequency(self):
        return self._instr_mw_output.Frequency
    @Frequency.setter
    def Frequency(self, val):
        self._instr_mw_output.Frequency = val
        
    @property
    def Phase(self):
        return self._instr_mw_output.Phase
    @Phase.setter
    def Phase(self, val):
        self._instr_mw_output.Phase = val
        
    @property
    def Mode(self):
        return self._instr_mw_output.Mode
    @Mode.setter
    def Mode(self, new_mode):
        assert new_mode == 'Continuous' or new_mode == 'PulseModulated', "MW source output mode must either be Continuous or PulseModulated."
        self._instr_mw_output.Mode = new_mode

    def set_trigger_source(self, trig_src_obj):
        #TODO: Consider error-checking here
        self._trig_src_obj = trig_src_obj

    def get_trigger_source(self):
        return self._trig_src_obj

    def _get_instr_trig_src(self):
        return self.get_trigger_source()
    def _get_instr_input_trig_edge(self):
        return self._instr_mw_output.TriggerInputEdge
    def _get_timing_diagram_info(self):
        if self.Mode == 'PulseModulated':
            return {'Type' : 'BlockShaded', 'TriggerType' : 'Gated'}
        else:
            return {'Type' : 'None'}

    def _get_all_trigger_inputs(self):
        return [self]
