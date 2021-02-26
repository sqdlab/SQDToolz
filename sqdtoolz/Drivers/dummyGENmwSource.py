from qcodes import Instrument, InstrumentChannel

class DummyGENmwSrcChannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str) -> None:
        super().__init__(parent, name)
        self._outputEnable = True
        self._power = 1.0
        self._frequency = 1.0e9
        self._phase = 0.0
        self._mode = 'Continuous'   #Can be: Continuous, PulseModulated

        self.add_parameter(
                'power', label='Output Power', unit='dBm',
                get_cmd=lambda : self._power,
                set_cmd=self._set_power)
        self.add_parameter('frequency', label='Output Frequency', unit='Hz',
                           get_cmd=lambda : self._frequency,
                           set_cmd=self._set_frequency)
        self.add_parameter('phase', label='Output Phase', unit='deg',
                           get_cmd=lambda : self._phase,
                           set_cmd=self._set_phase)

    def _set_power(self, val):
        self._power = val
    def _set_frequency(self, val):
        self._frequency = val
    def _set_phase(self, val):
        self._phase = val
        
    @property
    def Output(self):
        return self._outputEnable
    @Output.setter
    def Output(self, val):
        self._outputEnable = val
        
    @property
    def Power(self):
        return self.power()
    @Power.setter
    def Power(self, val):
        self.power(val)
        
    @property
    def Frequency(self):
        return self.frequency()
    @Frequency.setter
    def Frequency(self, val):
        self.frequency(val)
        
    @property
    def Phase(self):
        return self.phase()
    @Phase.setter
    def Phase(self, val):
        self.phase(val)

    @property
    def Mode(self):
        return self._mode
    @Mode.setter
    def Mode(self, new_mode):
        assert new_mode == 'Continuous' or new_mode == 'PulseModulated', "MW source output mode must either be Continuous or PulseModulated."
        self._mode = new_mode
        #Perform mode settings


class DummyGENmwSrc(Instrument):
    '''
    Dummy driver to emulate a Generic Microwave Source instrument.
    '''
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs) #No address...

        # Output channels added to both the module for snapshots and internal output sources for use in queries
        self._source_outputs = {}
        for ch_name in ['CH1', 'CH2']:
            cur_channel = DummyGENmwSrcChannel(self, ch_name)
            self.add_submodule(ch_name, cur_channel)
            self._source_outputs[ch_name] = cur_channel

    def get_output(self, identifier):
        return self._source_outputs[identifier]

    def get_all_outputs(self):
        return [(x,self._source_outputs[x]) for x in self._source_outputs]

