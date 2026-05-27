from qcodes import Instrument, InstrumentChannel, VisaInstrument
from qcodes.utils import validators as vals
import time

class SW_RFSwitchController_CryoRadiall_Channel(InstrumentChannel):
    def __init__(self, parent:Instrument, sw_num, leName, switch_type) -> None:
        super().__init__(parent, leName)
        self._parent = parent
        self.sw_num = sw_num

        self._switch_type = switch_type
        self._current_state = 'P0'
        if switch_type == 'Daisy':
            self._allowed_states = ['P0','P1', 'P2', 'P3', 'P4', 'P5', 'P6']
            self._daisy_engage_pair("P0",False)  #Disengage all relays
        else:
            self._allowed_states = ['P0','P1', 'P2', 'P3', 'P4', 'P5']
            assert False, "Individual Reset untested."

    def _latch_all_relays(self):
        self.write(f"GPIO:SR:LAT")

    def _daisy_engage_pair(self, pos, setting):
        for m in range(self._parent._num_switches,0,-1):    #Loading the SRs from the last channel to the first channel before latching the outputs
            if m == self.sw_num:
                self._daisy_engage_pair_single(pos, setting)
            else:
                self._daisy_engage_pair_single('P0',False)  #Disengage all relays on this switch
        self._latch_all_relays()

    def _daisy_engage_pair_single(self, pos, setting):
        '''
        This only sets the relays to create a positive/negative (i.e. set/reset) path for a contact-pair
        in the RF switch. If it's P0, all relay paths disengage from the RF switch. Setting setting just
        sets whether the chosen contact-pair is in set/reset mode (for True/False).
        '''
        assert pos in self._allowed_states, f"State {pos} is invalid."
        pos = int(pos[1:])  #Strip the P from P3 etc. to just get 3 etc...
        if setting:
            byte = 2    #Set
        else:
            byte = 1    #Reset
        if self._switch_type == 'Daisy':
            for m in range(6):
                if m+1 == pos:
                    byte += 2<<(2*(m+1))    #i.e. 10 engages that cell
                else:
                    byte += 1<<(2*(m+1))    #i.e. 01 disengages that cell
        self.write(f"GPIO:SR:LOAD {byte>>8}")
        self.write(f"GPIO:SR:LOAD {byte & 0xFF}")

    def _switch_off_all_relay_currents(self):
        '''
        This just sets all control lines to the relay coils to zero; it will not affect the state
        of the relay paths and thus, the state of the RF switch.
        '''
        for m in range(self._parent._num_switches):
            self.write(f"GPIO:SR:LOAD 0")
            self.write(f"GPIO:SR:LOAD 0")
        self._latch_all_relays()

    @property
    def Position(self):
        return self._current_state
    @Position.setter
    def Position(self, pos):
        if self._switch_type == 'Daisy':
            #Reset all contacts on RF Switch
            for m in range(6):
                self._daisy_engage_pair(f"P{m+1}", False)
                time.sleep(self._parent._delay_time)
            self._daisy_engage_pair("P0",False)  #Disengage all relays
            time.sleep(self._parent._delay_time)
            self._switch_off_all_relay_currents()       #Switch off current to relays
            #Engage contact on RF Switch
            if pos != 'P0':
                self._daisy_engage_pair(pos, True)
                time.sleep(self._parent._delay_time)
            self._daisy_engage_pair("P0",False)  #Disengage all relays
            self._switch_off_all_relay_currents()       #Switch off current to relays
            self._current_state = pos

    def get_all_switch_contacts(self):
        return self._allowed_states[:]


class SW_RFSwitchController_CryoRadiall(VisaInstrument):
    """
    RPi Driver for switch based on SQDelectrik/Projects/RFSwitchController_CryoRadiall
    GPIO4=DAT
    GPIO17=LAT
    GPIO18-CLK
    switch_type can be 'Daisy' or 'Individual' for daisy-chained and individual-reset varieties...
    P0 is reserved for full reset...

    For Switches with Reset:
        - Normal Negative Common: D1=0, D2=1
        - Positive Common: D1=1, D2=0
    For Switches with Daisy Chain:
        - Set: D1=0, D2=1
        - Reset: D1=1, D2=0
    """
    def __init__(self, name, address, \
        pins = {"DAT" : 4, "CLK" : 18, "LAT": 17},
        switch_types=['Daisy'], **kwargs):
        super().__init__(name, address, terminator='\n', timeout=30)
        #kwargs['init_instrument_only'] = True
        self._state_map = pins

        self._delay_time = 0.5
        self.add_parameter('pulse_delay_time', unit='s',
                label="Output voltage pulse time",
                initial_value=0.5,
                vals=vals.Numbers(0.001, 10),
                get_cmd=lambda : self._delay_time,
                set_cmd=self._set_delay)

        self._num_switches = len(switch_types)

        #Set the prescribed pins to outputs
        for cur_key in self._state_map:
            self.write(f'GPIO:SOUR:DIG:IO{self._state_map[cur_key]} OUT')
            self.write(f'GPIO:SOUR:DIG:DATA{self._state_map[cur_key]} 0')

        self.write(f"GPIO:SR:PINS {self._state_map['DAT']},{self._state_map['CLK']},{self._state_map['LAT']}")

        # self._switches = {}
        for m,cur_switch_type in enumerate(switch_types):
            leName = f"sw{m+1}"
            cur_module = SW_RFSwitchController_CryoRadiall_Channel(self, m+1, leName, cur_switch_type)
            self.add_submodule(leName, cur_module)    #Name is christened inside the channel object...
            # self._switches[leName] = cur_module

    def _set_delay(self, delay):
        self._delay_time = delay




if __name__ == '__main__':
    dev = SW_RFSwitchController_CryoRadiall('test', 'TCPIP::10.42.95.97::4000::SOCKET', switch_types=['Daisy']*3)
    # dev._daisy_engage_pair('P1',True)
    dev.sw1.Position = 'P1'


    a=0
