from sqdtoolz.HAL.GEN import GEN

class GENmwSource(GEN):
    def __init__(self, instr_gen_freq_src_channel):
        '''
        '''
        super().__init__(instr_gen_freq_src_channel.name)
        self._instr_freq = instr_gen_freq_src_channel


    @property
    def Output(self):
        return self._instr_freq.Output
    @Output.setter
    def Output(self, val):
        self._instr_freq.Output = val
        
    @property
    def Power(self):
        return self._instr_freq.Power
    @Power.setter
    def Power(self, val):
        self._instr_freq.Power = val
        
    @property
    def Frequency(self):
        return self._instr_freq.Frequency
    @Frequency.setter
    def Frequency(self, val):
        self._instr_freq.Frequency = val
        
    @property
    def Phase(self):
        return self._instr_freq.Phase
    @Phase.setter
    def Phase(self, val):
        self._instr_freq.Phase = val
        
    @property
    def Mode(self):
        return self._instr_freq.Phase
    @Mode.setter
    def Mode(self, new_mode):
        assert new_mode == 'Continuous' or new_mode == 'PulseModulated', "MW source output mode must either be Continuous or PulseModulated."
        self._instr_freq.Mode = new_mode
