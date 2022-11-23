from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
from functools import partial
import serial
import datetime

class THERM_TC0309_Channel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, chan_ind) -> None:
        super().__init__(parent, name)
        self._parent = parent
        self._chan_ind = chan_ind

    @property
    def Temperature(self):
        self._parent.refresh_stats()
        return self._parent.temperatures[self._chan_ind]

class THERM_TC0309(Instrument):
    """
    Driver for the Windfreak SynthHD PRO v2.
    """
    def __init__(self, name, address, **kwargs):
        Instrument.__init__(self, name, **kwargs)

        # Output channels added to both the module for snapshots and internal output sources for use in queries
        self._source_outputs = {}
        self._chan_names = ['CH1','CH2','CH3','CH4']
        for ch_ind, ch_name in enumerate(self._chan_names):
            cur_channel = THERM_TC0309_Channel(self, ch_name, ch_ind)
            self.add_submodule(ch_name, cur_channel)
            self._source_outputs[ch_name] = cur_channel
        
        self.address = address
        self.ser = serial.Serial(port=address, baudrate=9600, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
        self.last_refresh_time = datetime.datetime(1900, 1, 1)
        self.temperatures = [0]*4

        self.add_parameter('status', label='Status Command A',
                            get_cmd=lambda: self._get_status())
        self._get_status()

    def _get_status(self):
        self.refresh_stats()
        #TODO: Open up all parameters...
        return ','.join([str(int(x)) for x in self.data])

    def refresh_stats(self):
        delta_time = datetime.datetime.now() - self.last_refresh_time
        delta_time = delta_time.seconds + delta_time.microseconds / 1.0e6
        if delta_time < 21e-3:  #Typical acquisition time...
            return

        data = None
        max_tries = 100
        while (data == None or data[0] != 2 or data[-1] != 3):
            self.ser.write(bytes('A',encoding='utf-8'))
            data = self.ser.read(45)
            max_tries -= 1
            if max_tries <= 0:
                assert False, f"Serial read error in the TC0309 thermometer on address {self.address}"
        
        self.temperatures[0] = ((data[7] << 8) | data[8]) / 10.0
        self.temperatures[1] = ((data[9] << 8) | data[10]) / 10.0
        self.temperatures[2] = ((data[11] << 8) | data[12]) / 10.0
        self.temperatures[3] = ((data[13] << 8) | data[14]) / 10.0
        self.last_refresh_time = datetime.datetime.now()
        self.data = data

    def get_idn(self):
        return {'vendor': 'Perfect Prime', 'model': 'TC0309', 'serial': None, 'firmware': None}

# drv = THERM_TC0309('test', 'COM4')
# drv.refresh_stats()
