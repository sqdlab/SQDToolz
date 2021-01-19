
from qcodes import Instrument, InstrumentChannel as vals
import TriggerPulse

class DummyDDGchannel(InstrumentChannel):
    '''
    DG645 per-output settings
    '''
    def __init__(self, parent:Instrument, name:str, channel:int) -> None:
        super().__init__(parent, name)
        self.channel = channel

        self._trigpol = 0
        self._triglen = 0.0
        self._trigdly = 0.0

        self.add_parameter('TrigPolarity', label='Pulse Polarity', 
                           docstring='Polarity of the output',
                           get_cmd=lambda : self._trigpol,
                           set_cmd=lambda x : self._trigpol = x)
        self.add_parameter(
                'TrigPulseLength', label='Trigger Pulse Duration', unit='s',
                get_cmd=lambda : self._triglen,
                set_cmd=lambda x : self._triglen = x)
        self.add_parameter(
            'TrigPulseDelay', label='Trigger Pulse Delay', unit='s',
            get_cmd=lambda : self._trigdly,
            set_cmd=lambda x : self._trigdly = x)

    @property
    def TrigEnable(self):
        return True     #Not implementing any output enable/disable...

  
class DummyDDG(Instrument):
    '''
    Dummy driver to emulate a DDG instrument.
    '''
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        #A 10ns output SYNC
        self.add_submodule('SYNC', SyncTriggerPulse(10e-9, lambda : True, lambda x:x))

        # Output channels
        for ch_id, ch_name in [(0, 'A'), (1, 'B'), (2, 'C')]:
            self.add_submodule(ch_name, DummyDDGchannel(self, ch_name, ch_id))
