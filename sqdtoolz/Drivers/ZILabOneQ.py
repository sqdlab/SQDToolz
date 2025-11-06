from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
from functools import partial
import datetime
import laboneq.simple as lbeqs
import numpy as np


class ZILabOneQ(Instrument):
    """
    Driver for the Windfreak SynthHD PRO v2.
    """
    def __init__(self, name, address, port, setup_yaml, **kwargs):
        Instrument.__init__(self, name, **kwargs)
        self.device_setup = lbeqs.DeviceSetup.from_yaml(filepath = setup_yaml, server_host=address, server_port=port)

    def get_idn(self):
        return {'vendor': 'Zurich Instruments', 'model': 'everything', 'serial': None, 'firmware': None}

