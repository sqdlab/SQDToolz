
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

    def set_trigger_source(self, trig_obj):
        self._trig_src_obj = trig_obj

    def get_trigger_source(self):
        return self._trig_src_obj

