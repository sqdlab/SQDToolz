from sqdtoolz.HAL.HALbase import*
from sqdtoolz.HAL.TriggerPulse import*

class GENfuncGen(HALbase):
    def __init__(self, hal_name, lab, instr_fgen_src_name, instr_fgen_src_channel):
        HALbase.__init__(self, hal_name)
        self._instr_fgen_src_name = instr_fgen_src_name
        self._instr_fgen_src_channel = instr_fgen_src_channel
        self._instr_fgen_output = lab._get_instrument(instr_fgen_src_name).get_output(instr_fgen_src_channel)
        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"], config_dict["InstrumentChannel"])

    @property
    def Output(self):
        return self._instr_fgen_output.Output
    @Output.setter
    def Output(self, val):
        self._instr_fgen_output.Output = val

    @property
    def Waveform(self):
        return self._instr_fgen_output.Waveform
    @Waveform.setter
    def Waveform(self, new_Waveform):
        allowed_wfms = ['SINE', 'SQUARE', 'SAWTOOTH', 'TRIANGLE', 'PULSE']
        assert new_Waveform in allowed_wfms, f"Function generator output waveform must either be in: {allowed_wfms}."
        self._instr_fgen_output.Waveform = new_Waveform

    @property
    def Frequency(self):
        return self._instr_fgen_output.Frequency
    @Frequency.setter
    def Frequency(self, val):
        self._instr_fgen_output.Frequency = val

    @property
    def Amplitude(self):
        return self._instr_fgen_output.Amplitude
    @Amplitude.setter
    def Amplitude(self, val):
        self._instr_fgen_output.Amplitude = val

    @property
    def Offset(self):
        return self._instr_fgen_output.Offset
    @Offset.setter
    def Offset(self, val):
        self._instr_fgen_output.Offset = val

    @property
    def DutyCycle(self):
        return self._instr_fgen_output.DutyCycle
    @DutyCycle.setter
    def DutyCycle(self, val):
        self._instr_fgen_output.DutyCycle = val

    def activate(self):
        self.Output = True

    def deactivate(self):
        self.Output = False

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_fgen_src_name,
            'InstrumentChannel' : self._instr_fgen_src_channel,
            'Type' : self.__class__.__name__,
            'ManualActivation' : self.ManualActivation
            }
        self.pack_properties_to_dict(['Waveform', 'Frequency', 'Amplitude', 'Offset', 'DutyCycle', 'Output'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a MW-Source with a configuration that is of type ' + dict_config['Type']
        self._channel_name = dict_config['Name']
        self.Waveform = dict_config['Waveform']
        self.Frequency = dict_config['Frequency']
        self.Amplitude = dict_config['Amplitude']
        self.Offset = dict_config['Offset']
        self.DutyCycle = dict_config['DutyCycle']
        self.Output = dict_config.get('Output', False)
        self.ManualActivation = dict_config.get('ManualActivation', False)
