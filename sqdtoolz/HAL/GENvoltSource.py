from sqdtoolz.HAL.GEN import GEN

class GENvoltSource(GEN):
    def __init__(self, instr_gen_volt_src_channel):
        '''
        '''
        super().__init__(instr_gen_volt_src_channel.name)
        self._instr_volt = instr_gen_volt_src_channel


    @property
    def Output(self):
        return self._instr_volt.Output
    @Output.setter
    def Output(self, val):
        self._instr_volt.Output = val
        
    @property
    def Voltage(self):
        return self._instr_volt.Voltage
    @Voltage.setter
    def Voltage(self, val):
        self._instr_volt.Voltage = val
        
    @property
    def RampRate(self):
        return self._instr_volt.RampRate
    @RampRate.setter
    def RampRate(self, val):
        self._instr_volt.RampRate = val
