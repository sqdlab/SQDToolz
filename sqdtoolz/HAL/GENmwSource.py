
class GENmwSource:
    def __init__(self, instr_gen_freq_src_channel):
        '''
        '''
        self._instr_freq = instr_gen_freq_src_channel
        self._name = instr_gen_freq_src_channel.name

    @property
    def Name(self):
        return self._name

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
