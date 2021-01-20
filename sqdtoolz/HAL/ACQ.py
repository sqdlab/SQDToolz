
class ACQ:
    def __init__(self, inst_acq):
        self._inst_acq = inst_acq

    @property
    def TrigEnable(self):
        return self._enableGet()
    @TrigEnable.setter
    def TrigEnable(self, boolVal):
        self._enableSet(boolVal)