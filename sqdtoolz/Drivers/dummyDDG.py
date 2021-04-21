from qcodes import Instrument, InstrumentChannel

class DummyDDGchannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str) -> None:
        super().__init__(parent, name)
        self._outputEnable = True
        self._trigpol = 0
        self._triglen = 10.0e-9
        self._trigdly = 0.0

        self.add_parameter(
                'trigPulseLength', label='Trigger Pulse Duration', unit='s',
                get_cmd=lambda : self._triglen,
                set_cmd=self._set_trigLen)
        self.add_parameter('trigPolarity', label='Pulse Polarity', 
                           docstring='Polarity of the output',
                           get_cmd=lambda : self._trigpol,
                           set_cmd=self._set_trigPol)
        self.add_parameter(
            'trigPulseDelay', label='Trigger Pulse Delay', unit='s',
            get_cmd=lambda : self._trigdly,
            set_cmd=self._set_trigDly)

    def _set_trigLen(self, val):
        self._triglen = val
    def _set_trigPol(self, val):
        self._trigpol = val
    def _set_trigDly(self, val):
        self._trigdly = val
        
    @property
    def TrigEnable(self):
        return self._outputEnable
    @TrigEnable.setter
    def TrigEnable(self, val):
        self._outputEnable = val
        
    @property
    def TrigPulseLength(self):
        return self.trigPulseLength()
    @TrigPulseLength.setter
    def TrigPulseLength(self, val):
        self.trigPulseLength(val)
        
    @property
    def TrigPolarity(self):
        return self.trigPolarity()
    @TrigPolarity.setter
    def TrigPolarity(self, val):
        self.trigPolarity(val)
        
    @property
    def TrigPulseDelay(self):
        return self.trigPulseDelay()
    @TrigPulseDelay.setter
    def TrigPulseDelay(self, val):
        self.trigPulseDelay(val)

        


  
class DummyDDG(Instrument):
    '''
    Dummy driver to emulate a DDG instrument.
    '''
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs) #No address...

        # #A 10ns output SYNC
        # self.add_submodule('SYNC', SyncTriggerPulse(10e-9, lambda : True, lambda x:x))

        # Output channels added to both the module for snapshots and internal Trigger Sources for the DDG HAL...
        self._trig_sources = {}
        for ch_name in ['A', 'B', 'C']:
            cur_channel = DummyDDGchannel(self, ch_name)
            self.add_submodule(ch_name, cur_channel)
            self._trig_sources[ch_name] = cur_channel

        self._rep_time = 100e-9

    @property
    def RepetitionTime(self):
        return self._rep_time
    @RepetitionTime.setter
    def RepetitionTime(self, val):
        self._rep_time = val

    def get_trigger_output(self, identifier):
        return self._trig_sources[identifier]

    def get_all_trigger_sources(self):
        return [(x,self._trig_sources[x]) for x in self._trig_sources]

