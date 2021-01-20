from qcodes import Instrument

class DummyACQ(Instrument):
    '''
    Dummy driver to emulate an ACQ instrument.
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
            self._trig_sources[ch_name] = Trigger(ch_name, cur_channel)

    def get_trigger_output(self, identifier):
        return self._trig_sources[identifier]

    def get_all_trigger_sources(self):
        return [self._trig_sources[x] for x in self._trig_sources]