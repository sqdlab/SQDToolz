from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
from functools import partial
import datetime
import laboneq.simple as lbeqs
import numpy as np


class ZILabOneQ(Instrument):
    """
    Driver for the Zurich Instruments boxes
    """
    def __init__(self, name, address, port, setup_yaml, **kwargs):
        Instrument.__init__(self, name, **kwargs)

        self.device_setup = lbeqs.DeviceSetup("ZI_QCCS")
        self.device_setup.add_dataserver(
            host=address,
            port=port,
        )

        leBoxes = []
        self._shfqcs = []
        for cur_uid in setup_yaml:
            options = {
                'address':setup_yaml[cur_uid]['address'],
                'device_options':setup_yaml[cur_uid]['device_options']
                }
            if setup_yaml[cur_uid]['type'] == 'SHFQC':
                if 'reference_clock_source' in setup_yaml[cur_uid]:
                    options['reference_clock_source'] = setup_yaml[cur_uid]['reference_clock_source']
                leBoxes.append(lbeqs.SHFQC(uid=cur_uid, **options))
                self._shfqcs.append(cur_uid)
            elif setup_yaml[cur_uid]['type'] == 'HDAWG':
                leBoxes.append(lbeqs.HDAWG(uid=cur_uid, **options))
            elif setup_yaml[cur_uid]['type'] == 'PQSC':
                leBoxes.append(lbeqs.PQSC(uid=cur_uid, **options))
        self.device_setup.add_instruments(*leBoxes)

        for cur_shfqc in self._shfqcs:
            conns_m = []
            for m in range(8):  #TODO: Check if it is SHFQC-16W to unlock 16 demodulations?
                conns_m.append(lbeqs.create_connection(to_signal=f"aux_{cur_shfqc}_{m}/measure", ports="QACHANNELS/0/OUTPUT", type="iq"))
                conns_m.append(lbeqs.create_connection(to_signal=f"aux_{cur_shfqc}_{m}/acquire", ports="QACHANNELS/0/INPUT", type="acquire"))
            self.device_setup.add_connections(cur_shfqc, *conns_m)

        # self.device_setup = lbeqs.DeviceSetup.from_yaml(filepath = setup_yaml, server_host=address, server_port=port)

    def get_shfqcs(self):
        return self._shfqcs[:]

    def get_free_aux_readout_lines(self, shfqc_taken_counts:dict):
        avail_lines = {}
        #TODO: Check if it is SHFQC-16W to unlock 16 demodulations?
        for sid,cur_shfqc in enumerate(self._shfqcs):
            for m in range(8-shfqc_taken_counts[cur_shfqc]):
                avail_lines[f"aux_{sid}_{m}"] = {'log_conn': f"aux_{cur_shfqc}_{m}", 'shfqc': cur_shfqc, 'f_LO': 7e9}
        return avail_lines

    def get_idn(self):
        return {'vendor': 'Zurich Instruments', 'model': 'everything', 'serial': None, 'firmware': None}

