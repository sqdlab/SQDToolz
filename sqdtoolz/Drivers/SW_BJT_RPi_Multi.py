from qcodes import Instrument, InstrumentChannel, VisaInstrument
from qcodes.utils import validators as vals
import time

class SW_BJT_RPi_Multi_Channel(InstrumentChannel):
    def __init__(self, parent:Instrument, sw_num, leName, pins) -> None:
        super().__init__(parent, leName)
        self._parent = parent
        self.sw_num = sw_num

        self._state_map = pins

        self._delay_time = 0.1

        self.add_parameter('pulse_delay_time', unit='s',
                label="Output voltage pulse time",
                initial_value=0.1,
                vals=vals.Numbers(0.001, 10),
                get_cmd=lambda : self._delay_time,
                set_cmd=self._set_delay)

        #Set the prescribed pins to outputs
        for cur_key in self._state_map:
            self._parent.write(f'GPIO:SOUR:DIG:IO{self._state_map[cur_key]} OUT')
            self._parent.write(f'GPIO:SOUR:DIG:DATA{self._state_map[cur_key]} 0')

        self._set_state('P0')
        self.Position = self._current_state

    def _set_gpio(self, pin, state) :
        """
        """
        f = lambda x: ",1" if x else ",0"
        cmd = str(pin) + f(state)
        self._set_cmd(cmd) 

    def _wait_till_ready(self):
        for m in range(10):
            time.sleep(1)
            if (int(self._parent.ask('*OPC?')) == 1):
                return
        assert False, "Timed out waiting for RPi-Switch to get ready..."


    def _set_delay(self, delay):
        self._delay_time = delay


    def _set_state(self, state) :
        """
        Wrapper method to handle setting of state
        @param state <String> : Switch position e.g. "P1"
        """
        # RESET SWITCH with a 1s pulse
        if self._state_map["P0"] > 0:
            self._parent.write(f'GPIO:SOUR:DIG:PULS{self._state_map["P0"]} 1, {self._delay_time}')
            self._wait_till_ready()        

        # SET NEW STATE with a 1s pulse
        if (state != "P0"):
            self._parent.write(f'GPIO:SOUR:DIG:PULS{self._state_map[state]} 1, {self._delay_time}')
            self._wait_till_ready()
        self._current_state = state # update state tracking variable

    @property
    def Position(self):
        return self._current_state
        return self.cur_switch.get('route')
    @Position.setter
    def Position(self, pos):
        if pos in self._state_map.keys() :
            self._set_state(pos)
        return
        if pos in self._cur_contacts:
            self.cur_switch.set('route', pos)

    def get_all_switch_contacts(self):
        return list(self._state_map.keys())

class SW_BJT_RPi_Multi(VisaInstrument):
    """
    RPi Driver for switch
    P0 is dedicated state for reset, do not overwrite
    
    Given as: sw1: {"P0" : 10, "P1" : 3, "P2" : 5, "P3" : 7, "P4" : 11} etc.
    """
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=30)
        #kwargs['init_instrument_only'] = True

        self._switches = {}

        for cur_key in kwargs:
            if cur_key.lower().startswith('sw'):
                cur_ind = int(cur_key[2:])
                cur_pins = kwargs[cur_key]
                leName = cur_key
                cur_module = SW_BJT_RPi_Multi_Channel(self, cur_ind, leName, cur_pins)
                self.add_submodule(leName, cur_module)    #Name is christened inside the channel object...
                self._switches[leName] = cur_module

    def read_line(self, channel):
        if (not channel.channel.eof_received):
            return channel.readline()
        else :
            return None

