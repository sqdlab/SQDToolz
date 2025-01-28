from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
  
class DummySMU(Instrument):
    '''
    Dummy driver to emulate a SMU instrument.
    '''
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.increment_voltage = kwargs.get('increment_voltage', True)
        self.increment_voltage_step = kwargs.get('increment_voltage_step', 1)
        self._voltage = kwargs.get('increment_voltage_start', 0) - self.increment_voltage_step
        self._current = 0
        self._output = True
        self._comp_current = 1
        self._comp_voltage = 1
        self._mode = 'SrcI_MeasV'

    @property
    def Voltage(self):
        self._voltage += self.increment_voltage_step
        return self._voltage
    @Voltage.setter
    def Voltage(self, val):
        self._voltage = val

    @property
    def Current(self):
        return self._current
    @Current.setter
    def Current(self, val):
        self._current = val

    @property
    def SenseVoltage(self):
        return self._voltage

    @property
    def SenseCurrent(self):
        return self._current

    @property
    def Output(self):
        return self._output
    @Output.setter
    def Output(self, val):
        self._output = val

    @property
    def ComplianceCurrent(self):
        return self._comp_current
    @ComplianceCurrent.setter
    def ComplianceCurrent(self, val):
        self._comp_current = val
    
    @property
    def ComplianceVoltage(self):
        return self._comp_voltage
    @ComplianceVoltage.setter
    def ComplianceVoltage(self, val):
        self._comp_voltage = val
    
    @property
    def Mode(self):
        return self._mode
    @Mode.setter
    def Mode(self, val):
        self._mode = val

    @property
    def SupportsSweeping(self):
        return False
    
    @property
    def RampRateVoltage(self):
        return 1
    @RampRateVoltage.setter
    def RampRateVoltage(self, val):
        pass

    @property
    def RampRateCurrent(self):
        return 1
    @RampRateCurrent.setter
    def RampRateCurrent(self, val):
        pass

    @property
    def ProbeType(self):
        return 'TwoWire'
    @ProbeType.setter
    def ProbeType(self, val):
        pass    #Can't set this one...

    def get_idn(self):
        return {
            "vendor": "QCoDeS",
            "model": str(self.__class__),
            "seral": "NA",
            "firmware": "NA",
        }
