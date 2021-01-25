from qcodes import Instrument

class DummyAWGchannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str) -> None:
        super().__init__(parent, name)
        self._parent = parent

    @property
    def Parent(self):
        return self._parent

class DummyAWG(Instrument):
    '''
    Dummy driver to emulate an AWG instrument.
    '''
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs) #No address...

        # #A 10ns output SYNC
        # self.add_submodule('SYNC', SyncTriggerPulse(10e-9, lambda : True, lambda x:x))

        self._num_samples = 10
        self._sample_rate = 10e9
        self._trigger_edge = 1

        # Output channels added to both the module for snapshots and internal Trigger Sources for the DDG HAL...
        self._trig_sources = {}
        for ch_name in ['A', 'B', 'C']:
            cur_channel = DummyDDGchannel(self, ch_name)
            self.add_submodule(ch_name, cur_channel)
            self._trig_sources[ch_name] = Trigger(ch_name, cur_channel)

    @property
    def SampleRate(self):
        return self._sample_rate
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self._sample_rate = frequency_hertz

    @property
    def TriggerInputEdge(self):
        return self._trigger_edge
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self._trigger_edge = pol

    def program_channel(self, chan_id, wfm_data):
        print(wfm_data)
