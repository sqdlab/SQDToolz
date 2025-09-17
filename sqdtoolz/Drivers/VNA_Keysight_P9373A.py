from sqdtoolz.Drivers.VNA_Agilent_N5232A import VNA_Agilent_N5232A

class VNA_Keysight_P9373A(VNA_Agilent_N5232A):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters.pop('elec_delay_time')

    @property
    def ElecDelayTime(self):
        return -1
    @ElecDelayTime.setter
    def ElecDelayTime(self, val):
        pass

    def _set_aux_off(self):
        pass
