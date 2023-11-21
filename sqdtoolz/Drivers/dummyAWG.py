from qcodes import Instrument, InstrumentChannel
import numpy as np

class DummyAWGchannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str) -> None:
        super().__init__(parent, name)
        self._parent = parent
        self._outputEnable = True
        self._amp = 1.0
        self._off = 0.0

        self.add_parameter(
            'amplitude', label='Amplitude', unit='V',
            get_cmd=lambda : self._amp,
            set_cmd=self._set_amp)
        self.add_parameter(
            'offset', label='Offset', unit='V',
            get_cmd=lambda : self._off,
            set_cmd=self._set_off)
        self.add_parameter(
            'output', label='Output Enable',
            get_cmd=lambda : self._outputEnable,
            set_cmd=self._set_outputEnable)

    def _set_amp(self, val):
        self._amp = val
    def _set_off(self, val):
        self._off = val
    def _set_outputEnable(self, val):
        self._outputEnable = val

    @property
    def Parent(self):
        return self._parent
        
    @property
    def Amplitude(self):
        return self.amplitude()
    @Amplitude.setter
    def Amplitude(self, val):
        self.amplitude(val)
        
    @property
    def Offset(self):
        return self.offset()
    @Offset.setter
    def Offset(self, val):
        self.offset(val)
        
    @property
    def Output(self):
        return self.output()
    @Output.setter
    def Output(self, boolVal):
        self.output(boolVal)

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
        for ch_name in ['CH1', 'CH2', 'CH3', 'CH4']:
            cur_channel = DummyAWGchannel(self, ch_name)
            self.add_submodule(ch_name, cur_channel)

    @property
    def SampleRate(self):
        return self._sample_rate
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self._sample_rate = frequency_hertz

    @property
    def AutoCompressionSupport(self):
        return {'Supported' : True, 'MinSize' : 8, 'Multiple' : 8}

    @property
    def MemoryRequirements(self):
        return {'MinSize' : 8, 'Multiple' : 8}

    @property
    def TriggerInputEdge(self):
        return self._trigger_edge
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self._trigger_edge = pol

    def num_supported_markers(self, channel_name):
        return 2

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]
        else:
            return None
    
    def prepare_waveform_memory(self, chan_id, seg_lens, **kwargs):
        pass

    def program_channel(self, chan_id, dict_wfm_data):
        # print(dict_wfm_data['waveforms'][0])
        print("Programmed Dummy AWG!")
        pass

    def get_idn(self):
        return {
            "vendor": "QCoDeS",
            "model": str(self.__class__),
            "seral": "NA",
            "firmware": "NA",
        }
