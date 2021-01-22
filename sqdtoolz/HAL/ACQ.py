
class ACQ:
    def __init__(self, instr_acq):
        self._instr_acq = instr_acq
        self._trig_src_module = None
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
    def SampleRate(self):
        return self._instr_acq.SampleRate
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self._instr_acq.SampleRate = frequency_hertz

    @property
    def TriggerEdge(self):
        return self._instr_acq.TriggerInputEdge
    @TriggerEdge.setter
    def TriggerEdge(self, pol):
        self._instr_acq.TriggerInputEdge = pol

    def set_trigger_source(self, hal_module, trig_id):
        '''
        Sets the trigger source.

        Inputs:
            - hal_module - Must be a DDG or AWG module (i.e. the digital SYNC, clock or marker outputs that can be used as an instrument trigger)
            - trig_obj - ID with which to reference the trigger output from the hal_module (to be fed into this instrument)
        '''
        self._trig_src_module = hal_module
        self._trig_src_id = trig_id
        self._trig_src_obj = hal_module.get_trigger_output(trig_id)

    def get_trigger_source(self):
        '''
        Get the Trigger object corresponding to the trigger source.
        '''
        return self._trig_src_obj

    def _get_current_config(self):
        return {
            'instrument' : self.name,
            'type' : 'ACQ',
            'NumSamples' : self.NumSamples,
            'SampleRate' : self.SampleRate,
            'TriggerEdge' : self.TriggerEdge,
            'TriggerSource' : {
                'TriggerSourceHAL' : self._trig_src_module.name,
                'TriggerSourceID' : self._trig_src_id
                }
            }

    def _set_current_config(self, dict_config, instr_obj = None):
        assert dict_config['type'] == 'ACQ', 'Cannot set configuration to a ACQ with a configuration that is of type ' + dict_config['type']
        if (instr_obj != None):
            self._instr_acq = instr_obj
        self.NumSamples = dict_config['NumSamples']
        self.SampleRate = dict_config['SampleRate']
        self.TriggerEdge = dict_config['TriggerEdge']
