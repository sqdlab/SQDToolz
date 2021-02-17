from sqdtoolz.HAL.GEN import GEN

class GENmwSource(GEN):
    def __init__(self, instr_gen_freq_src_channel):
        '''
        '''
        super().__init__(instr_gen_freq_src_channel.name)
        self._instr_freq = instr_gen_freq_src_channel


    @property
    def OutputEnable(self):
        return self._instr_freq.OutputEnable
    @OutputEnable.setter
    def OutputEnable(self, val):
        self._instr_freq.OutputEnable = val
        
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
        self._instr_freq.Frequency
