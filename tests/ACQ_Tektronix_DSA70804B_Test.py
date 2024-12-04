import time
from collections import OrderedDict
import numpy as np
import pandas as pd
from qcodes import validators as vals
from qcodes.instrument import VisaInstrument
from qcodes.instrument_drivers.tektronix import TektronixDSA70000 


class TektronixDSA70804B(VisaInstrument):
    def __init__(self, name, address, channel_number, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=60, **kwargs)
        self.channel_number = channel_number

        self.add_parameter(
        'data_source', label = 'Data Source', unit = 'a.u.',
        get_cmd = 'data:source?', get_parser =str,
        set_cmd = 'data:source ch%d'%(self.channel_number,)#, vals = vals.Numbers(1, 1e5)
        )

obj = TektronixDSA70804B('test', address='TCPIP::192.168.1.200',channel_number = 1)

obj.write('DATa:ENCdg FAStest')#modify to FPBinary: floating point (width = 4) data
obj.write('DATa:BN_Fmt RI')#modify to :FP and BYT_NR to 4 using WFMOutpre:BYT_Nr
# obj.write('DATa:BYT_NR 1')
obj.visa_handle.timeout = 60000
data = obj.visa_handle.query_binary_values('CURVe?', datatype='H')

a=0

