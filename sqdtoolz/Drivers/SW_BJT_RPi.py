from qcodes import VisaInstrument
import time

class SW_BJT_RPi(VisaInstrument):
    """
    RPi Driver for switch
    P0 is dedicated state for reset, do not overwrite
    """
    def __init__(self, name, address, \
        pins = {"P0" : 10, "P1" : 3, "P2" : 5, "P3" : 7, "P4" : 11}, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=30)
        #kwargs['init_instrument_only'] = True
        self._state_map = pins

        #Set the prescribed pins to outputs
        for cur_key in self._state_map:
            self.write(f'GPIO:SOUR:DIG:IO{self._state_map[cur_key]} OUT')
            self.write(f'GPIO:SOUR:DIG:DATA{self._state_map[cur_key]} 0')

        self._set_state('P0')
        self.Position = self._current_state

    def read_line(self, channel):
        if (not channel.channel.eof_received):
            return channel.readline()
        else :
            return None

    def _set_gpio(self, pin, state) :
        """
        """
        f = lambda x: ",1" if x else ",0"
        cmd = str(pin) + f(state)
        self._set_cmd(cmd) 

    def _wait_till_ready(self):
        for m in range(10):
            time.sleep(1)
            if (int(self.ask('*OPC?')) == 1):
                return
        assert False, "Timed out waiting for RPi-Switch to get ready..."

    def _set_state(self, state) :
        """
        Wrapper method to handle setting of state
        @param state <String> : Switch position e.g. "P1"
        """
        # RESET SWITCH with a 1s pulse
        self.write(f'GPIO:SOUR:DIG:PULS{self._state_map["P0"]} 1, 0.1')
        self._wait_till_ready()        

        # SET NEW STATE with a 1s pulse
        if (state != "P0"):
            self.write(f'GPIO:SOUR:DIG:PULS{self._state_map[state]} 1, 0.1')
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
