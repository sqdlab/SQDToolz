
class ACQ:
    def __init__(self, instr_acq):
        self._instr_acq = instr_acq
        self._trig_src_obj = None
        self._name = instr_acq.name

    @property
    def name(self):
        return self._name

    @property
    def NumSamples(self):
        return self._instr_acq.NumSamples
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self._instr_acq.NumSamples = num_samples

    @property
    def NumSegments(self):
        return self._instr_acq.NumSegments
    @NumSegments.setter
    def NumSegments(self, num_segs):
        self._instr_acq.NumSegments = num_segs

    @property
    def NumRepetitions(self):
        return self._instr_acq.NumRepetitions
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps):
        self._instr_acq.NumRepetitions = num_reps

    @property
    def SampleRate(self):
        return self._instr_acq.SampleRate
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self._instr_acq.SampleRate = frequency_hertz

    @property
    def InputTriggerEdge(self):
        return self._instr_acq.TriggerInputEdge
    @InputTriggerEdge.setter
    def InputTriggerEdge(self, pol):
        self._instr_acq.TriggerInputEdge = pol

    def get_data(self):
        return self._instr_acq.get_data()

    def set_trigger_source(self, trig_src_obj):
        #TODO: Consider error-checking here
        self._trig_src_obj = trig_src_obj

    def get_trigger_source(self):
        '''
        Get the Trigger object corresponding to the trigger source.
        '''
        return self._trig_src_obj

    def _get_trigger_sources(self):
        return [self._trig_src_obj]

    def _get_acq_window_len(self, segment_index = 0):
        return self.NumSamples / self.SampleRate

    def _get_current_config(self):
        return {
            'instrument' : self.name,
            'type' : 'ACQ',
            'NumSamples' : self.NumSamples,
            'SampleRate' : self.SampleRate,
            'InputTriggerEdge' : self.InputTriggerEdge,
            'TriggerSource' : self._trig_src_obj.get_trigger_params()
            }

    def _set_current_config(self, dict_config, instr_obj = None):
        assert dict_config['type'] == 'ACQ', 'Cannot set configuration to a ACQ with a configuration that is of type ' + dict_config['type']
        if (instr_obj != None):
            self._instr_acq = instr_obj
        self.NumSamples = dict_config['NumSamples']
        self.SampleRate = dict_config['SampleRate']
        self.InputTriggerEdge = dict_config['InputTriggerEdge']

    
