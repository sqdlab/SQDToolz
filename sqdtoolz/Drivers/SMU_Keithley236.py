from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
import numpy as np

from sqdtoolz.Drivers.Dependencies.PrologixGPIBEthernet import PrologixGPIBEthernet

class SMU_Keithley236(PrologixGPIBEthernet, Instrument):
    """This class represents and controls a Keithley 236 SMU. For operating
    details of this instrument, refer to Keithley 236 SMU manual - especially
    Section 3.6 which lists the specific commands.

    This Java code-listing is also useful:
        https://codeshare.phy.cam.ac.uk/waw31/JISA/-/blob/9db4b0f103430be1458007b3f234fed3e38cc33f/src/JISA/Devices/K236.java
    """

    def write(self, cmd):
        super().write(cmd + 'H0X')

    def __init__(self, name, address, gpib_slot, **kwargs):
        super().__init__(address=address)
        Instrument.__init__(self, name, **kwargs)
        self.connect()
        self.select(gpib_slot)

        self.description = "Keithley 236 SMU"
        self.expectedMfr = "Keithley"
        self.expectedModel = "236"

        #Remote ENABLE
        self.write('REMOTE 716')
        #Reset
        self.write('J0')

        self.add_parameter('status_error', get_cmd='U1')
        self.add_parameter('status_machine', get_cmd='U3')
        self.add_parameter('status_measurement', get_cmd='U4')
        self.add_parameter('status_compliance', get_cmd='U5')
        self.add_parameter('status_suppression', get_cmd='U6')
        self.add_parameter('src_meas', get_cmd='G5,0,0')

        self.add_parameter('voltage',
                            label='Output Voltage',
                            get_cmd=lambda: self._get_voltage(),
                            set_cmd=lambda x: self._set_voltage(x),
                            vals=vals.Numbers(-210.0, 210.0),
                            get_parser=float,
                            inter_delay=0.05,
                            step=0.001)
        self.add_parameter('voltage_ramp_rate', unit='V/s',
                            label="Output voltage ramp-rate",
                            initial_value=2.5e-3/0.05,
                            vals=vals.Numbers(0.001, 100),
                            get_cmd=lambda : self.voltage.step/self.voltage.inter_delay,
                            set_cmd=self._set_ramp_rate_volt)

        self.add_parameter('current',
                            label='Output Current',
                            get_cmd=lambda: self._get_current(),
                            set_cmd=lambda x: self._set_current(x),
                            vals=vals.Numbers(-210.0, 210.0),
                            get_parser=float,
                            inter_delay=0.05,
                            step=0.001)
        self.add_parameter('current_ramp_rate', unit='A/s',
                            label="Output current ramp-rate",
                            initial_value=0.001,
                            vals=vals.Numbers(0.001, 100),
                            get_cmd=lambda : self.current.step/self.current.inter_delay,
                            set_cmd=self._set_ramp_rate_current)

    @property
    def Mode(self):
        res = self.status_measurement()
        assert res[7] == 'F', "COM Error when reading machine status"
        if res[8] == '0':
            return 'SrcV_MeasI'
        else:
            return 'SrcI_MeasV'
    @Mode.setter
    def Mode(self, mode):
        #Using DC Mode by default in both cases...
        if mode == 'SrcV_MeasI':
            self.ask('F0,0')
        else:
            self.ask('F1,0')

    @property
    def Output(self):
        res = self.status_machine()
        assert res[18] == 'N', "COM Error when reading machine status"
        return res[19] == '1'
    @Output.setter
    def Output(self, val):
        if val:
            self.write('N1')
        else:
            self.write('N0')

    def _get_voltage(self):
        res = self.src_meas()
        if self.Mode == 'SrcV_MeasI':
            assert res[1:5] == 'SDCV', "COM Error when reading source-measure"
            return float(res.split(',')[0][5:])
        else:
            assert res.split(',')[1][1:5] == 'MDCV', "COM Error when reading source-measure"
            return float(res.split(',')[1][5:])
    def _set_voltage(self, val):
        #Use auto-range and zero delay by default...
        self.write(f'B{val},0,0')

    @property
    def Voltage(self):
        return self.voltage()
    @Voltage.setter
    def Voltage(self, val):
        self.voltage(val)

    def _get_current(self):
        res = self.src_meas()
        if self.Mode == 'SrcI_MeasV':
            assert res[1:5] == 'SDCI', "COM Error when reading source-measure"
            return float(res.split(',')[0][5:])
        else:
            assert res.split(',')[1][1:5] == 'MDCI', "COM Error when reading source-measure"
            return float(res.split(',')[1][5:])
    def _set_current(self, val):
        #Use auto-range and zero delay by default...
        self.write(f'B{val},0,0')

    @property
    def Current(self):
        return self.current()
    @Current.setter
    def Current(self, val):
        self.current(val)

    @property
    def SenseVoltage(self):
        return self.Voltage

    @property
    def SenseCurrent(self):
        return self.Current
    
    @property
    def ComplianceCurrent(self):
        if self.Mode == 'SrcI_MeasV':
            return -1
        res = self.status_compliance()
        assert res[:3] == 'ICP', "COM Error when reading compliance"
        return float(res[3:])
    @ComplianceCurrent.setter
    def ComplianceCurrent(self, val):
        if self.Mode == 'SrcV_MeasI':
            range = np.clip(10 + np.ceil(np.log10(val)), 1, 10) #Check Page 206 of manual
            self.write(f'L{val},{int(range)}') # TODO: change this better
    
    @property
    def ComplianceVoltage(self):
        if self.Mode == 'SrcV_MeasI':
            return -1
        res = self.status_compliance()
        assert res[:3] == 'VCP', "COM Error when reading compliance"
        return float(res[3:])
    @ComplianceVoltage.setter
    def ComplianceVoltage(self, val):
        if self.Mode == 'SrcI_MeasV':
            self.write(f'L{val},0')

    @property
    def RampRateVoltage(self):
        return self.voltage_ramp_rate()
    @RampRateVoltage.setter
    def RampRateVoltage(self, val):
        self.voltage_ramp_rate(val)

    @property
    def RampRateCurrent(self):
        return self.current_ramp_rate()
    @RampRateCurrent.setter
    def RampRateCurrent(self, val):
        self.current_ramp_rate(val)

    #Basically ProbeType and Mode are the same on thus SMU?
    @property
    def ProbeType(self):
        if self.Mode == 'SrcV_MeasI':
            return 'TwoWire'
        else:
            return 'FourWire'
    @ProbeType.setter
    def ProbeType(self, connection):
        assert connection == 'TwoWire' or connection == 'FourWire', "ProbeType must be FourWire or TwoWire"
        if connection == 'TwoWire':
            self.Mode = 'SrcV_MeasI'
        else:
            self.Mode = 'SrcI_MeasV'

    def _set_ramp_rate_volt(self, ramp_rate):
        self.voltage.step = self.voltage.inter_delay * ramp_rate
 
    def _set_ramp_rate_current(self, ramp_rate):
        if ramp_rate < 0.01:
            self.current.step = 0.001
        elif ramp_rate < 0.1:
            self.current.step = 0.010
        elif ramp_rate < 1.0:
            self.current.step = 0.100
        else:
            self.current.step = 1.0
        self.current.inter_delay = self.current.step / ramp_rate
