from qcodes import VisaInstrument
from sqdtoolz.Drivers.SW_BJT_RPi import SW_BJT_RPi
import time

class SW_RpiIQBox(SW_BJT_RPi):
    """
    RPi Driver for switch
    P0 is dedicated state for reset, do not overwrite
    """
    def __init__(self, name, address, **kwargs):
        self._GPIO_LED = 16
        super().__init__(name, address, pins={"P0":-1, "Pmix": 26, "Pmeas": 21}, **kwargs)
        
        self.write('GPIO:BUZZ 13,Z1')
        self.write(f'GPIO:SOUR:DIG:IO{self._GPIO_LED} OUT')
        #kwargs['init_instrument_only'] = True

    @property
    def Position(self):
        return self._current_state
    @Position.setter
    def Position(self, pos):
        if pos in self._state_map.keys():
            self._set_state(pos)
        if pos == "Pmix":
            self.write('GPIO:BUZZ 13,Z2')
            self.write(f'GPIO:SOUR:DIG:DATA{self._GPIO_LED} 1')
        else:
            self.write(f'GPIO:SOUR:DIG:DATA{self._GPIO_LED} 0')
        return

    def get_all_switch_contacts(self):
        return ["Pmix", "Pmeas"]
