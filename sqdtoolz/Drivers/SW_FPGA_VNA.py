"""
This is a driver for the Stahl power supplies
"""

import logging
import re
from collections import OrderedDict
from functools import partial
from typing import Any, Callable, Dict, Iterable, Optional

import numpy as np

import serial

from qcodes import Instrument

from qcodes.instrument import ChannelList, InstrumentChannel, VisaInstrument
from qcodes.utils.validators import Numbers

from qcodes.utils import validators as vals

logger = logging.getLogger()
import time



class SW_FPGA_VNA(Instrument):
    """
    FPGA VNA Switch driver for the device shown here: https://github.com/sqdlab/SQDfpgaVNAswitch

    Args:
        name
        address: A serial port address
    """

    def __init__(self, name: str, address: str, **kwargs: Any):
        super().__init__(name, **kwargs)

        self.ser = serial.Serial(port=address, baudrate=9600, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

        self.add_parameter(
            "state",
            get_cmd=lambda: self.get_state()
        )
        self._position_init = "P1"

    def get_state(self):
        tries = 100
        while (tries > 0):
            try:
                cur_val = int(self.query('Z'))
                return cur_val
            except:
                tries -= 1
                continue
        assert False, "Issue querying switch state?"

    def get_idn(self):
        return 'VNA FPGA Switch'

    def write(self, cmd):
        self.ser.write(bytes(cmd,encoding='utf-8'))

    def query(self, cmd):
        self.ser.reset_input_buffer()
        self.write(cmd)
        ret_str = self.ser.read(1)
        ret_str = ret_str.decode(encoding='utf-8')
        return ret_str

    @property
    def Position(self):
        return "P" + str(self.state())
    @Position.setter
    def Position(self, pos):
        ans = ''
        if pos == "P1":
            while (ans != 'P'):
                ans = self.query('U')
        elif pos == "P2":
            while (ans != 'R'):
                ans = self.query('j')
        elif pos == "P3":
            while (ans != 'S'):
                ans = self.query('f')
        elif pos == "P4":
            self.write('w')

    @property
    def PositionInit(self):
        return self._position_init
    @PositionInit.setter
    def PositionInit(self, pos):
        assert pos in ["P1", "P2", "P3"], "PositionInit must be P1, P2 or P3"
        self._position_init = pos

    def manual_trigger(self):
        self.Position = self._position_init
        cur_ans = ''
        while (True):
            cur_ans = self.query('w')
            if cur_ans == 'T':
                break
            self.Position = self._position_init
    
    def hold(self):
        self.Position = self._position_init

    def get_all_switch_contacts(self):
        return ["P1", "P2", "P3", "P4"]

if __name__ == '__main__':
    test = SW_FPGA_VNA('bob', 'COM5')   #VISA Address for COM3 is ASRL3
    a=0