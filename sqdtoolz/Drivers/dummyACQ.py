from qcodes import Instrument

class DummyACQ(Instrument):
    '''
    Dummy driver to emulate an ACQ instrument.
    '''
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs) #No address...

        # #A 10ns output SYNC
        # self.add_submodule('SYNC', SyncTriggerPulse(10e-9, lambda : True, lambda x:x))

        self._num_samples = 10
        self._sample_rate = 10e9
        self._trigger_edge = 1

    @property
    def NumSamples(self):
        return self._num_samples
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self._num_samples = num_samples

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
