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

        self.device_setup = lbeqs.DeviceSetup("ZI_QCCS")
        self.device_setup.add_dataserver(
            host=address,
            port=port,
        )

        leBoxes = []
        for cur_uid in setup_yaml:
            if setup_yaml[cur_uid]['type'] == 'SHFQC':
                leBoxes.append(lbeqs.SHFQC(uid=cur_uid, address=setup_yaml[cur_uid]['address'], device_options=setup_yaml[cur_uid]['device_options']))
            elif setup_yaml[cur_uid]['type'] == 'HDAWG':
                leBoxes.append(lbeqs.HDAWG(uid=cur_uid, address=setup_yaml[cur_uid]['address'], device_options=setup_yaml[cur_uid]['device_options']))
            elif setup_yaml[cur_uid]['type'] == 'PQSC':
                leBoxes.append(lbeqs.PQSC(uid=cur_uid, address=setup_yaml[cur_uid]['address'], device_options=setup_yaml[cur_uid]['device_options']))
        self.device_setup.add_instruments(*leBoxes)

        # self.device_setup = lbeqs.DeviceSetup.from_yaml(filepath = setup_yaml, server_host=address, server_port=port)

    def get_idn(self):
        return {'vendor': 'Zurich Instruments', 'model': 'everything', 'serial': None, 'firmware': None}

