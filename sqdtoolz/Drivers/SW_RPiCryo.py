import time
from contextlib import contextmanager
from qcodes import (
    VisaInstrument, InstrumentChannel, Parameter, ManualParameter, 
    validators as vals
)

class DriverChannel(object):
    '''
    Half-bridge driver channel. 
    Attributes:
        pin_en: `int`
            Enable pin number on the RPi.
        pin_in: `int`
            Input pin number on the RPi.
    '''
    def __init__(self, pin_in, pin_en):
        self.pin_en = pin_en
        self.pin_in = pin_in


class CryoSwitchPort(Parameter):
    def __init__(self, name, port, **kwargs):
        super().__init__(name, **kwargs)
        self.port = port

    def get_raw(self):
        return getattr(self, 'state', None)

    def set_raw(self, state):
        self._instrument.switch(self.port, state)
        self.state = state


class CryoSwitchChannel(InstrumentChannel):
    def __init__(self, parent, name, cs, rs, fault, portmap):
        '''
        Arguments:
            cs: `int`
                H-bridge chip select pin
            rs: `int`
                H-bridge reset pin
            fault: `tuple` of `int`
                H-bridge fault pin(s)
            portmap: `dict` with `str`:(`BridgeChannel`, `BridgeChannel`) items
                H-bridge input and enable pins for the anode and cathode of 
                each switch channel.
        '''
        super().__init__(parent, name)
        self.pin_rs = rs
        self.pin_cs = cs
        self.pins_fault = fault
        self.portmap = portmap
        self.add_parameter('settle_time', ManualParameter, initial_value=10e-3, 
                           vals=vals.Numbers(0.5e-6, 1.), unit='s')
        for port in self.portmap.keys():
            self.add_parameter('{}_state'.format(port), CryoSwitchPort, 
                               port=port, vals=vals.Enum(True, False, None))
        self.initialize()

    def direction(self, pin, direction):
        '''Set digital output `pin` direction to `direction` ('IN' or 'OUT')'''
        if direction not in ['IN', 'OUT']:
            raise ValueError('direction must be IN or OUT')
        self.write('SOUR:DIG:IO{:d} {}'.format(pin, direction))

    def outpin(self, pin, state):
        '''Set digital output `pin` to logical state `state`.'''
        self.write('SOUR:DIG:DATA{:d} {:d}'.format(pin, state))

    def pulse(self, pin, state, pulse_length):
        '''Pulse digital output `pin` to `state` for `pulse_length` seconds.'''
        self.write('SOUR:DIG:PULS{:d} {:d},{:f}'.format(pin, state, pulse_length))
        
    def initialize(self):
        '''Initialize pins on the RPi'''
        # set rs/cs to LOW, resets the bridges
        self.outpin(self.pin_rs, False)
        self.direction(self.pin_rs, 'OUT')
        self.outpin(self.pin_cs, False)
        self.direction(self.pin_cs, 'OUT')
        # set other outputs to LOW
        for channels in self.portmap.values():
            for channel in channels:
                for pin in (channel.pin_en, channel.pin_in):
                    self.outpin(pin, False)
                    self.direction(pin, 'OUT')
        for pin in self.pins_fault:
            self.direction(pin, 'IN')

    @contextmanager
    def select(self):
        '''Context manager that enables the bridges for this channel.'''
        self.outpin(self.pin_rs, True)
        self.outpin(self.pin_cs, True)
        try:
            yield
        finally:
            self.outpin(self.pin_rs, False)
            self.outpin(self.pin_cs, False)

    def switch(self, port, state):
        '''Connect or disconnect `port`.'''
        if port not in self.portmap:
            raise KeyError('Invalid port {}.'.format(port))
        anode, cathode = self.portmap[port]
        # select and later unselect bridges for this channel
        with self.select():
            time.sleep(0.1)
            # set polarity of the two ends
            self.outpin(anode.pin_in, not state)
            self.outpin(cathode.pin_in, state)
            # enable cathode, pulse anode
            self.outpin(cathode.pin_en, True)
            self.pulse(anode.pin_en, True, self.settle_time.get())
            self.outpin(cathode.pin_en, False)


class SW_RPiCryo(VisaInstrument):
    '''
    SQDLab cryogenic switch rev. 2 driver
    '''
    def __init__(self, name, address, switch_ind, init_pos='P4'):
        super().__init__(name, address, terminator='\n')
        # the box contains two pairs of half bridges for the two switches
        # switch 0: P1=A1, P2=A2, P4=A3, P5=B1, CG=B2, (CG1=B3)
        # switch 1: P1=C1, P2=C2, P4=C3, P5=D1, CG=D2, (CG1=D3)
        #
        # rpi connections (ports >=29 need an offset of -2 on the pi)
        # the sleep and reset pins for each switch are wired together
        # the enable and input pins for each port are wired together
        # bridge A+C: en1=3, in1=5, en2=7, in2=8, en3=10, in3=11, nFault=13
        # bridge B+D: en1=19, in1=18, en2=22, in2=21, en3=24, in3=23, nFault=26
        # bridge A+B: nSleep=12, nReset=15
        # bridge C+D: nSleep=29, nReset=31

        #NOTE THAT P3 IS THE COMMON PIN TO WHICH P1, P2, P4 and P5 SWITCH TO...

        # en and in lines are shared between both switches
        cground0 = DriverChannel(21, 22)
        cground1 = DriverChannel(23, 24) # now unused
        ports = dict(
            P1 = (DriverChannel(5, 3), cground0), 
            P2 = (DriverChannel(8, 7), cground0), 
            P4 = (DriverChannel(11, 10), cground0), 
            P5 = (DriverChannel(18, 19), cground0)
        )

        self._cur_contacts = ['P1', 'P2', 'P4', 'P5']

        if switch_ind == 0:
            # the rs(nReset) and cs(nSleep) are per switch
            self.add_submodule('cur_switch', CryoSwitchChannel(
                self, 'sw0', rs=31-2, cs=29-2, fault=(13, 26), portmap=ports
            ))
        elif switch_ind == 1:
            self.add_submodule('cur_switch', CryoSwitchChannel(
                self, 'sw1', rs=15, cs=12, fault=(13, 26), portmap=ports
            ))
        else:
            assert False, "Parameter cur_switch must be 0 or 1"

        self.connect_message()
        print('Hold infinity in the palm of your hand...')

        self.Position = init_pos

    @property
    def Position(self):
        for cur_port in self._cur_contacts:
            if self.cur_switch.get(cur_port + '_state'):
                return cur_port            
        return None
    @Position.setter
    def Position(self, pos):
        if pos in self._cur_contacts:
            for cur_port in self._cur_contacts:
                self.cur_switch.set(cur_port + '_state', False)
            self.cur_switch.set(pos + '_state', True)

    def get_all_switch_contacts(self):
        return self._cur_contacts[:]

# sw = SW_RPiCryo('test', 'TCPIP::192.168.1.144::4000::SOCKET', 1)
# a=0
