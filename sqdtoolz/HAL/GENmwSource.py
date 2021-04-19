from sqdtoolz.HAL.HALbase import*
from sqdtoolz.HAL.TriggerPulse import*

class GENmwSource(HALbase, TriggerInputCompatible, TriggerInput):
    def __init__(self, hal_name, lab, instr_mw_src_name, instr_mw_src_channel):
        HALbase.__init__(self, hal_name)
        if lab._register_HAL(self):
            #
            self._instr_mw_src_name = instr_mw_src_name
            self._instr_mw_src_channel = instr_mw_src_channel
            self._instr_mw_output = lab._get_instrument(instr_mw_src_name).get_output(instr_mw_src_channel)
            self._trig_src_obj = None
        else:
            assert self._instr_mw_src_name == instr_mw_src_name, "Cannot reinstantiate a waveform by the same name, but different instrument configurations." 
            assert self._instr_mw_src_channel == instr_mw_src_channel, "Cannot reinstantiate a waveform by the same name, but different channel configurations." 

    def __new__(cls, hal_name, lab, instr_mw_src_name, instr_mw_src_channel):
        prev_exists = lab.get_HAL(hal_name)
        if prev_exists:
            assert isinstance(prev_exists, GENmwSource), "A different HAL type already exists by this name."
            return prev_exists
        else:
            return super(GENmwSource, cls).__new__(cls)

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

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_mw_output.name,
            'type' : 'GENmwSource',
            'TriggerSource' : self._get_trig_src_params_dict(),
            'InputTriggerEdge' : self._instr_mw_output.TriggerInputEdge
            }
        self.pack_properties_to_dict(['Power', 'Frequency', 'Phase', 'Mode'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['type'] == 'GENmwSource', 'Cannot set configuration to a MW-Source with a configuration that is of type ' + dict_config['type']
        self._channel_name = dict_config['Name']
        self.Power = dict_config['Power']
        self.Frequency = dict_config['Frequency']
        self.Phase = dict_config['Phase']
        self.Mode = dict_config['Mode']       
        #
        trig_src_obj = TriggerInput.process_trigger_source(dict_config['TriggerSource'], lab)
        self.set_trigger_source(trig_src_obj)
        self._instr_mw_output.TriggerInputEdge = dict_config['InputTriggerEdge']
