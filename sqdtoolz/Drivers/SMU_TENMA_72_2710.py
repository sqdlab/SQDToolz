from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
import numpy as np
import serial

class SMU_TENMA_72_2710(Instrument):
    """This class represents and controls a TENMA 72-2710 Programmable DC Power Supply 30V 5A. For operating
    details of this instrument, refer to https://www.farnell.com/datasheets/2578054.pdf."""

    def __init__(self, name, address, **kwargs):
        super().__init__(name, **kwargs)

        self.description = "TENMA 72-2710 Programmable DC Power Supply 30V 5A"
        self.expectedMfr = "TENMA"
        self.expectedModel = "72-2710"
        
        self.ser = serial.Serial(port=address, baudrate=9600, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
        
        idn_str = self.query('*IDN?')
        assert idn_str[:5] == self.expectedMfr and idn_str[6:13] == self.expectedModel, "Could not verify model " + self.description

        # self.write('LOCK1')

        self.add_parameter(name = 'voltage',
                           label = 'Set Voltage',
                           get_cmd = lambda: float(self._try_get_voltage()),
                           set_cmd = lambda x: self.write(f'VSET1:{x:2.2f}'),
                           vals = vals.Numbers(0, 30),
                           inter_delay = 0.05,
                           step = 0.01)

        self.add_parameter(name = 'current',
                           label = 'Set Current',
                           get_cmd = lambda: float(self.query('ISET1?')),
                           set_cmd = lambda x: self.write(f'ISET1:{x:2.2f}'),
                           vals = vals.Numbers(0, 5.1),
                           inter_delay = 0.05,
                           step = 0.01)

        self.add_parameter(name = 'voltage_measure',
                           label = 'Actual Voltage',
                           get_cmd = lambda: float(self.query('VOUT1?')))
    
        self.add_parameter(name = 'current_measure',
                           label = 'Actual Current',
                           get_cmd = lambda: float(self.query('IOUT1?')))
    
        self.add_parameter(name = 'output',
                           label = 'Output status',
                           get_cmd = lambda: self._get_status()[0],
                           set_cmd = lambda x: self.write(f'OUT{x}'),
                           val_mapping={True:  1, False : 0})
        
        self.add_parameter(name = 'ocp',
                           label = 'Overcurrent protection',
                           set_cmd = lambda x: self.write(f'OCP{x}'),
                           val_mapping={True:  1, False : 0})
        self.ocp(False)

    @property
    def Voltage(self):
        return self.voltage()
    @Voltage.setter
    def Voltage(self, val):
        self.voltage.set(val)

    def _try_get_voltage(self):
        num_tries = 1000
        while(num_tries > 0):
            num_tries -= 1
            try:
                return float(self.query('VSET1?'))
            except:
                continue
        assert False, "Error getting voltage on Tenma PSU..."

    @property
    def Current(self):
        return self.current()
    @Current.setter
    def Current(self, val):
        self.current.set(val)

    @property
    def SenseVoltage(self):
        return self.voltage_measure()

    @property
    def SenseCurrent(self):
        return self.current_measure()

    @property
    def Output(self):
        return self.output()
    @Output.setter
    def Output(self, val):
        self.output(val)

    @property
    def ComplianceCurrent(self):
        return self.Current
    @ComplianceCurrent.setter
    def ComplianceCurrent(self, val):
        self.Current = val
    
    @property
    def ComplianceVoltage(self):
        return self.Voltage
    @ComplianceVoltage.setter
    def ComplianceVoltage(self, val):
        self.Voltage = val
    
    @property
    def Mode(self):
        cv = self._get_status()[1]
        if cv:
            return 'SrcV_MeasI'
        else:
            return 'SrcI_MeasV'
    @Mode.setter
    def Mode(self, val):
        pass    #Cannot set the mode on this one...
    
    
    @property
    def RampRateVoltage(self):
        return self.voltage.step/self.voltage.inter_delay
    @RampRateVoltage.setter
    def RampRateVoltage(self, val):
        ramp_rate = val
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
    def RampRateCurrent(self):
        return self.current.step/self.current.inter_delay
    @RampRateCurrent.setter
    def RampRateCurrent(self, val):
        ramp_rate = val
        if ramp_rate < 0.01:
            self.current.step = 0.001
        elif ramp_rate < 0.1:
            self.current.step = 0.010
        elif ramp_rate < 1.0:
            self.current.step = 0.100
        else:
            self.current.step = 1.0
        self.current.inter_delay = self.current.step / ramp_rate

    @property
    def ProbeType(self):
        return 'TwoWire'
    @ProbeType.setter
    def ProbeType(self, val):
        pass    #Can't set this one...
    
    def write(self, cmd):
        self.ser.write(bytes(cmd,encoding='utf-8'))

    def query(self, cmd):
        self.write(cmd)
        ret_str = self.ser.read(1024)
        ret_str = ret_str.decode(encoding='utf-8')
        return ret_str

    def _get_status(self):
        self.write('STATUS?')
        status = bytearray(self.ser.read(1024))[0]
        if status & 0b01000000 > 0 :
            output = True
        else:
            output = False
        if status & 0b00000001 > 0 :
            cv = True # Power supply is in Constant Voltage mode
        else:
            cv = False # Power supply is in Constant Current mode

        return output, cv
        
    def get_idn(self):
        return {'vendor': 'Tenma', 'model': '72-2710', 'serial': None, 'firmware': None}

        