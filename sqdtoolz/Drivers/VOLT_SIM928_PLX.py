from functools import partial
import logging
import numpy as np
import time

from qcodes import Instrument, InstrumentChannel
from qcodes.utils import validators as vals

from sqdtoolz.Drivers.Dependencies.PrologixGPIBEthernet import PrologixGPIBEthernet

log = logging.getLogger(__name__)


class SIM928_ChannelModule(InstrumentChannel):
    def __init__(self, parent:Instrument, slot_num, leName) -> None:
        super().__init__(parent, leName)
        self._parent = parent
        self.slot_num = slot_num

        self.add_parameter('voltage', unit='V',
                        label="Output voltage",
                        vals=vals.Numbers(-20, 20),
                        get_cmd=self._get_voltage,
                        set_cmd=self._set_voltage,
                        get_parser=float,
                        inter_delay=0.05,
                        step=0.001)

        #NOTE: Although the ramp-rate is technically software-based, there could be a source that provides actual precision rates - so it's left as a parameter in general instead of being a HAL-level feature...
        
        self.add_parameter('voltage_ramp_rate', unit='V/s',
                        label="Output voltage ramp-rate",
                        initial_value=2.5e-3/0.05,
                        vals=vals.Numbers(0.001, 1),
                        get_cmd=lambda : self.voltage.step/self.voltage.inter_delay,
                        set_cmd=self._set_ramp_rate)

    def _get_voltage(self):
        try:
            result = float(self._parent._ask_module(self.slot_num, 'VOLT?'))
        except ValueError:
            result = self._get_voltage()
        return result

    def _set_voltage(self, voltage):
        """
        Set the output voltage of a module.
        
        NOTE: This exists primarily to round to 3dp... If there's a nice QCoDeS parser, kill this and update the voltage parameter...

        Args:
            voltage (float): Voltage value to set.
        """
        self._parent._write_module(self.slot_num, 'VOLT {:.3f}'.format(voltage))

    def _set_ramp_rate(self, ramp_rate):
        if ramp_rate < 0.01:
            self.voltage.step = 0.001
        elif ramp_rate < 0.1:
            self.voltage.step = 0.010
        elif ramp_rate < 1.0:
            self.voltage.step = 0.100
        else:
            self.voltage.step = 1.0
        self.voltage.inter_delay = self.voltage.step / ramp_rate

    @property
    def Output(self):
        return True
    @Output.setter
    def Output(self, val):
        pass
        
    @property
    def Voltage(self):
        return self.voltage()
    @Voltage.setter
    def Voltage(self, val):
        self.voltage(val)
        
    @property
    def RampRate(self):
        return self.voltage_ramp_rate()
    @RampRate.setter
    def RampRate(self, val):
        self.voltage_ramp_rate(val)


class VOLT_SIM928_PLX(PrologixGPIBEthernet, Instrument):
    """
    A driver for Stanford Research Systems SIM 928 DC source modules installed
    in a SIM900 mainframe.

    Note that this is a driver when using the Prologix Ethernet-to-GPIB adapter;
    hence the "PLX" prefix...

    Args:
        name (str): An identifier for this instrument, particularly for
            attaching it to a ``Station``.
        address (str): The visa resource name to use to connect.
        timeout (number): Seconds to allow for responses. Default ``5``.
        metadata (Optional[Dict]): Additional static metadata to add to this
            instrument's JSON snapshot.
    """

    def __init__(self, name, address, gpib_slot, **kw):
        super().__init__(address=address)
        Instrument.__init__(self, name, **kw)
        self.connect()
        self.select(gpib_slot)
        
        self.write('*DCL')  # device clear
        self.write('FLSH')  # flush port buffers
        self.write('SRST')  # SIM reset (causes 100 ms delay)
        time.sleep(0.5)

        #Build up the available module outputs on all slots...
        #TODO: Is this a bit draconian (e.g. slots could be shared across experiments)? Usually they make the actual module the arching object while
        #it's being treated as if it were a single voltage-source entity... Also, there are LP/HP SIM-Rack filters that can be tuned from the PC...
        #Anyway, food for thought...
        self.modules = self._find_modules()
        self._source_outputs = {}
        for ch_ind in self.modules:
            self._write_module(ch_ind, 'TERM LF')
            leName = f'CH{ch_ind}'
            cur_module = SIM928_ChannelModule(self, ch_ind, leName)
            self.add_submodule(leName, cur_module)    #Name is christened inside the channel object...
            self._source_outputs[ch_ind] = cur_module

        super().connect_message()

    def get_output(self, slot_id):
        return self._source_outputs[slot_id]

    def get_all_outputs(self):
        return [(x,self._source_outputs[x]) for x in self._source_outputs]

    def _get_module_idn(self, i):
        """
        Get the vendor, model, serial number and firmware version of a module.

        Args:
            i (int): Slot number of the module whose id is returned.

        Returns:
            A dict containing vendor, model, serial, and firmware.
        """
        idstr = self._ask_module(i, '*IDN?')
        idparts = [p.strip() for p in idstr.split(',', 3)]
        if len(idparts) < 4:
            idparts += [None] * (4 - len(idparts))
        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _find_modules(self):
        """
        Query the SIM900 mainframe for which slots have a SIM928 module present.

        Returns:
             A list of slot numbers where a SIM928 module is present (starting
                 from 1)
        """
        CTCR = self.ask('CTCR?')
        CTCR = int(CTCR) >> 1
        modules = []
        for i in range(1, 10):
            if CTCR & 1 != 0 and self._get_module_idn(i)['model'] == 'SIM928':
                modules.append(i)
            CTCR >>= 1
        return modules

    def _ask_module(self, i, cmd):
        """
        Write a command string to a module and return a response.

        Args:
            i (int): Slot number of the module to ask from.
            cmd (str): The VISA query string.

        Returns:
            The response string from the module.
        """
        msg = 'SNDT {},"{}"'.format(i, cmd)
        self.write(msg)
        time.sleep(100e-3)
        msg = 'GETN? {},128'.format(i)
        msg = self.ask(msg)
        # first read consumes the terminator of the message from the submodule,
        # so we have a terminator from the message to us still in the input
        # buffer.

        if msg[:2] != '#3':
            raise RuntimeError('Unexpected format of answer: {}'.format(msg))
        return msg[5:]

    def _write_module(self, i, cmd):
        """
        Write a command string to a module with NO response expected.

        Args:
            i (int): Slot number of the module to write to.
            cmd (str): The VISA command string.

            NOTE: SNDT means "Send Terminated Message to Port" (see SIM900m PDF documentation)
        """
        self.write('SNDT {},"{}"'.format(i, cmd))

    def _get_module_status(self, i):
        """
        Gets and clears the status bytes corresponding to the registers ESR,
        CESR and OVSR of module ``i``.

        Args:
            i (int): Slot number of the module of which to retrieve status.

        Returns:
            int, int, int: The bytes corresponding to standard event,
            communication error and overload statuses of module ``i``
        """
        stdevent = self._ask_module(i, '*ESR?')
        commerr = self._ask_module(i, 'CESR?')
        overload = self._ask_module(i, 'OVSR?')
        return stdevent, commerr, overload

    def reset_module(self, i):
        """
        Sends the SIM Reset signal to module i.

        Causes a break signal (MARK level) to be asserted for 100 milliseconds
        to module i. Upon receiving the break signal the modul will flush its
        internal input buffer, reset its command parser, and default to 9600
        baud communications.

        Args:
            i (int): Slot number of the module to reset.
        """
        self.write('SRST {}'.format(i))


    def check_module_errors(self, i, raiseexc=True):
        """
        Check if any errors have occurred on module ``i`` and clear the status
        registers.

        Args:
            i (int/str): Slot number or module name (as in ``slot_names``)
                of the module to check the error of.
            raiseexc (bool): If true, raises an exception if any errors have
                occurred. Default ``True``.

        Returns:
            list[str]: A list of strings with the error messages that have
            occurred.
        """
        stdevent, commerr, overload = self._get_module_status(i)
        OPC, INP, QYE, DDE, EXE, CME, URQ, PON \
            = self.byte_to_bits(int(stdevent))
        PARITY, FRAME, NOISE, HWOVRN, OVR, RTSH, CTSH, DCAS \
            = self.byte_to_bits(int(commerr))
        Overload, Overvoltage, BatSwitch, BatFault, _, _, _, _ \
            = self.byte_to_bits(int(overload))

        errors = []
        warnings = []
        if INP:
            errors.append('Input Buffer Error.')
        if QYE:
            errors.append('Query Error.')
        if DDE:
            code = self._ask_module(i, 'LDDE?')
            errors.append('Device Dependant Error: {}.'.format(code))
        if EXE:
            code = self._ask_module(i, 'LEXE?')
            msg = {0: 'No error',
                   1: 'Illegal value',
                   2: 'Wrong token',
                   3: 'Invalid bit'}.get(int(code), 'Unknown')
            if int(code) > 3 or int(code) == 0:
                warnings.append('Execution Error: {} ({}).'.format(msg, code))
            else:
                errors.append('Execution Error: {} ({}).'.format(msg, code))
        if CME:
            code = self._ask_module(i, 'LCME?')
            msg = {0: 'No error',
                   1: 'Illegal command',
                   2: 'Undefined command',
                   3: 'Illegal query',
                   4: 'Illegal set',
                   5: 'Missing parameter(s)',
                   6: 'Extra parameter(s)',
                   7: 'Null parameter(s)',
                   8: 'Parameter buffer overflow',
                   9: 'Bad floating-point',
                   10: 'Bad integer',
                   11: 'Bad integer token',
                   12: 'Bad token value',
                   13: 'Bad hex block',
                   14: 'Unknown token'}.get(int(code), 'Unknown')
            if int(code) > 14 or int(code) == 0:
                warnings.append('Command Error: {} ({}).'.format(msg, code))
            else:
                errors.append('Command Error: {} ({}).'.format(msg, code))
        if PARITY:
            errors.append('Parity Error.')
        if FRAME:
            errors.append('Framing Error.')
        if NOISE:
            errors.append('Noise Error.')
        if HWOVRN:
            errors.append('Hardware Overrun.')
        if OVR:
            errors.append('Input Buffer Overrun.')
        if RTSH:
            errors.append('Undefined Error (RTSH).')
        if CTSH:
            errors.append('Undefined Error (CTSH).')
        if Overload:
            errors.append('Current Overload.')
        if Overvoltage:
            errors.append('Voltage Overload.')
        if BatFault:
            errors.append('Battery Fault.')

        if raiseexc:
            if len(errors) != 0:
                raise Exception(' '.join(errors + warnings))
        return errors + warnings

    @staticmethod
    def byte_to_bits(x):
        """
        Convert an integer to a list of bits

        Args:
            x (int): The number to convert.

        Returns:
            list[bool]: A list of the lowest 8 bits of ``x`` where ``True``
            represents 1 and ``False`` 0.
        """
        bits = []
        for _ in range(8):
            if x & 1 != 0:
                bits.append(True)
            else:
                bits.append(False)
            x >>= 1
        return bits

    def __del__(self):
        self.close()

def runme():
    mySim = SIM928_PLX("bob", '192.168.1.208', 2)
    mySim.get_output(3).RampRate = 0.5
    mySim.get_output(3).Voltage = 0.0
    a = 0


if __name__ == '__main__':
    runme()

