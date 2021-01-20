
class ACQ:
    def __init__(self, inst_acq):
        self._inst_acq = inst_acq

    @property
    def Repetitions(self):
        return self._instrTrig.TrigPulseDelay
    @Repetitions.setter
    def Repetitions(self, len_seconds):
        self._instrTrig.TrigPulseDelay = len_seconds



    # def set_trigger_source(self, trig_obj):

