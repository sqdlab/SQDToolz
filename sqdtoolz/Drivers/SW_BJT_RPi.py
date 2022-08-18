from qcodes import (Instrument)

import paramiko
import time

class SW_BJT_RPi(Instrument):
    """
    RPi Driver for switch
    P0 is dedicated state for reset, do not overwrite
    """
    def __init__(self, name, address, username, password, \
        pins = {"P0" : 19, "P1" : 16, "P2" : 26, "P4" : 20, "P5" : 21}, **kwargs):
        #kwargs['init_instrument_only'] = True
        port = kwargs.get('port', 22)


        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try :
            self._ssh.connect(address, port, username, password)
        except :
            assert False, f"Unable to connect to RPi at {address}"

        self._stdin, self._stdout, self._stderr = self._ssh.exec_command("python3 RPi_gpio_interface.py\n")
        res = self.read_line(self._stdout)

        # Generate String for setting up pins
        inputString = ""
        for value in pins.values() :
            inputString += str(value) + ","
        inputString = inputString[:-1] 
        inputString += "\n"
        print("INPUT STRING IS:", inputString)
        self._stdin.write(inputString)
        self._stdout.flush()
        self._stdin.flush()
        self._state_map = pins
        self._current_state = "P0"
        self._initialise_pins()
        super().__init__(name, **kwargs)
        self.Position = self._current_state

    def read_line(self, channel):
        if (not channel.channel.eof_received):
            return channel.readline()
        else :
            return None


    #NEED THESE BECAUSE QCODES INSERTS \n etc...
    def _get_cmd(self, cmd):
        """
        Internal method to perform read command of GPIO
        """
        self._stdin.write('READ:' + cmd + '\n')
        return self.read_line(self._stdout)

    def _set_cmd(self, cmd):
        """
        Internal method to perform set command of GPIO
        """
        self._stdin.write('WRITE:' + cmd + '\n')
        self.read_line(self._stdout)
        self._stdout.flush()

    def _set_gpio(self, pin, state) :
        """
        """
        f = lambda x: ",1" if x else ",0"
        cmd = str(pin) + f(state)
        self._set_cmd(cmd) 

    def _set_state(self, state) :
        """
        Wrapper method to handle setting of state
        @param state <String> : Switch position e.g. "P1"
        """
        # RESET SWITCH
        #self._set_gpio(self._state_map[self._current_state], False) # Turn off current state GPIO
        self._set_gpio(self._state_map["P0"], True) # Trigger reset
        # perhaps wait here for a bit
        time.sleep(2)
        self._set_gpio(self._state_map["P0"], False) # Turn off reset trigger
        # SET NEW STATE
        if (state != "P0") :
            self._set_gpio(self._state_map[state], True) # Set new state to high
            time.sleep(2)
            self._set_gpio(self._state_map[state], False)
        self._current_state = state # update state tracking variable

    def _initialise_pins(self) :
        for key in self._state_map :
            self._set_gpio(self._state_map[key], False)
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
        return self._cur_contacts[:]