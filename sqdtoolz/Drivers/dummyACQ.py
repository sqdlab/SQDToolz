from qcodes import Instrument
import numpy as np

class DummyACQ(Instrument):
    '''
    Dummy driver to emulate an ACQ instrument.
    '''
    def __init__(self, name, blow_up_path='', **kwargs):
        super().__init__(name, **kwargs) #No address...

        # #A 10ns output SYNC
        # self.add_submodule('SYNC', SyncTriggerPulse(10e-9, lambda : True, lambda x:x))

        if blow_up_path != '':
            f = open(blow_up_path, "r")
            f.read()
            f.close()
            f = open(blow_up_path, "a")
            f.write("bar")
            f.close()

        self._num_samples = 10
        self._num_segs = 1
        self._num_reps = 1
        self._sample_rate = 1e9
        self._trigger_edge = 1

        self.ch_states = (True, True)

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
    def NumRepetitions(self):
        return self._num_reps
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps):
        self._num_reps = num_reps

    @property
    def NumSegments(self):
        return self._num_segs
    @NumSegments.setter
    def NumSegments(self, num_reps):
        self._num_segs = num_reps

    @property
    def TriggerInputEdge(self):
        return self._trigger_edge
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self._trigger_edge = pol

    @property
    def ChannelStates(self):
        return self.ch_states
    @ChannelStates.setter
    def ChannelStates(self, ch_states):
        assert len(ch_states) == 2, "There are 2 channel states that must be specified."
        self.ch_states = ch_states

    @property
    def AvailableChannels(self):
        return 2
    
    @property
    def SupportedDecisionBlocks(self):
        return []   #TODO: Add in some support to unit-test DecisionBlocks

    def get_data(self, **kwargs):
        cur_processor = kwargs.get('data_processor', None)

        #channels, segments, samples
        wav1 = np.array([[np.random.rand(self.NumSamples)]*self.NumSegments]*self.NumRepetitions)
        wav2 = np.array([[np.random.rand(self.NumSamples)]*self.NumSegments]*self.NumRepetitions)
        ret_val = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {
                        'ch1' : wav1.reshape(self.NumRepetitions, self.NumSegments, self.NumSamples),
                        'ch2' : wav2.reshape(self.NumRepetitions, self.NumSegments, self.NumSamples),
                        },
            'misc' : {'SampleRates' : [self.SampleRate]*2}
        }
        if cur_processor:
            cur_processor.push_data(ret_val)
            return {'data': cur_processor.get_all_data()}
        else:
            return {'data': ret_val}

        return np.array([[np.random.rand(self.NumSamples)]*self.NumSegments])
