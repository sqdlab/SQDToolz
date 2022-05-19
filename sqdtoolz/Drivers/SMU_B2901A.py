from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
import numpy as np

class SMU_B2901A(VisaInstrument):
    """This class represents and controls a Keysight B2901A SMU.  For operating
    details of this instrument, refer to Keysight document B2910-90030, titled
    "Keysight B2900 SCPI Command Reference"."""

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        self.description = "Keysight B2901 SMU"
        self.expectedMfr = "Keysight Technologies"
        self.expectedModel = "B2901A"
        self.VID = 0x0957
        self.PID = 0x8b18
        #instrument-specific additional setup
        self.write("*ESE 1")    #enable summary of bit 0, Event Status register, to enable *OPC monitoring
        self.write("*SRE 32")   #enable summary of bit 5, Status Byte, to enable *OPC monitoring

        #Set to auto-ranging
        self.write(':RANG:AUTO:VOLT ON')
        self.write(':RANG:AUTO:CURR ON')
        #Setup compliance checks
        self.write(':OUTP:PROT ON')
        self.write(':CALC:LIM:FUNC COMP')
        self.write(':CALC:LIM:COMP:FAIL OUT')
        self.write(":CALC:LIM:STAT 0")
        # self.write(":CALC:LIM:STAT?") WHY DOES self.ask(":SENS:CURR:PROT:TRIP?") NOT WORK?!?!?!?
        #TODO: Currently it sends out nan for compliance hit; but that isn't realiable. Figure out how to get TRIP working so that it returns a nice saturated compliance value instead...

        self.add_parameter('volt_force',
                           label='Output Voltage',
                           get_cmd='SOUR:VOLT?',
                           set_cmd='SOUR:VOLT {}',
                           vals=vals.Numbers(-210.0, 210.0),
                           get_parser=float,
                           inter_delay=0.05,
                           step=0.001)

        self.add_parameter('current_force',
                           label='Output Current',
                           get_cmd='SOUR:CURR?',
                           set_cmd='SOUR:CURR {}',
                           vals=vals.Numbers(-3.0, 3.0),
                           get_parser=float,
                           inter_delay=0.05,
                           step=0.001)

        self.add_parameter('current_compliance',
                           label='Compliance Current',
                           get_cmd=':SENS:CURR:PROT?',
                           set_cmd=':SENS:CURR:PROT {}',
                           vals=vals.Numbers(-3.0, 3.0),
                           get_parser=float)

        self.add_parameter('voltage_compliance',
                           label='Compliance Current',
                           get_cmd=':SENS:VOLT:PROT?',
                           set_cmd=':SENS:VOLT:PROT {}',
                           vals=vals.Numbers(-210.0, 210.0),
                           get_parser=float)

        self.add_parameter('output',
                            get_cmd=':OUTP?',
                            set_cmd=':OUTP {}',
                            set_parser=int,
                            val_mapping={True:  1, False : 0})

        self.add_parameter('mode',
                            get_cmd=lambda : self.ask(':FUNC:MODE?').strip(),
                            set_cmd=':FUNC:MODE {}',
                            val_mapping={'SrcV_MeasI' : 'VOLT', 'SrcI_MeasV' : 'CURR'})

        self.add_parameter('voltage_ramp_rate', unit='V/s',
                        label="Output voltage ramp-rate",
                        initial_value=2.5e-3/0.05,
                        vals=vals.Numbers(0.001, 1),
                        get_cmd=lambda : self.volt_force.step/self.volt_force.inter_delay,
                        set_cmd=self._set_ramp_rate_volt)

        self.add_parameter('current_ramp_rate', unit='A/s',
                        label="Output current ramp-rate",
                        initial_value=0.001,
                        vals=vals.Numbers(0.001, 1),
                        get_cmd=lambda : self.current_force.step/self.current_force.inter_delay,
                        set_cmd=self._set_ramp_rate_current)

        self.add_parameter('current_measure', unit='A',
                        label="Current Measure",
                        get_parser=float,
                        get_cmd=":MEAS:CURR?")

        self.add_parameter('volt_measure', unit='V',
                        label="Voltage Measure",
                        get_parser=float,
                        get_cmd=":MEAS:VOLT?")
        
        self._last_user_output_state = self.Output

    @property
    def Mode(self):
        return self.mode()
    @Mode.setter
    def Mode(self, mode):
        self.mode(mode)
        self.write(':OUTP:PROT ON')
        if mode == 'SrcV_MeasI':
            self.write(':SENS:FUNC CURR')
        else:
            self.write(':SENS:FUNC VOLT')

    @property
    def Output(self):
        return self.output()
    @Output.setter
    def Output(self, val):
        self._last_user_output_state = val
        self.write(':OUTP:PROT ON')
        self.output(val)

    @property
    def Voltage(self):
        return self.volt_force()
    @Voltage.setter
    def Voltage(self, val):
        temp = self._last_user_output_state
        self.Output = False
        self.volt_force(val)
        self._last_user_output_state = temp
        self.Output = self._last_user_output_state

    @property
    def Current(self):
        return self.current_force()
    @Current.setter
    def Current(self, val):
        temp = self._last_user_output_state
        self.Output = False
        self.current_force(val)
        self._last_user_output_state = temp
        self.Output = self._last_user_output_state

    @property
    def SenseVoltage(self):
        if self.Output != self._last_user_output_state: #i.e. it turned off due to compliance
            return np.nan
        return np.clip(self.volt_measure(), -210, 210)

    def is_tripped(self):
        return int(self.ask(":SYST:INT:TRIP?"))

    @property
    def SenseCurrent(self):
        if self.Output != self._last_user_output_state: #i.e. it turned off due to compliance
            return np.nan
        return self.current_measure()
    
    @property
    def ComplianceCurrent(self):
        return self.current_compliance()
    @ComplianceCurrent.setter
    def ComplianceCurrent(self, val):
        self.current_compliance(val)
    
    @property
    def ComplianceVoltage(self):
        return self.voltage_compliance()
    @ComplianceVoltage.setter
    def ComplianceVoltage(self, val):
        self.voltage_compliance(val)

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

    def _set_ramp_rate_volt(self, ramp_rate):
        if ramp_rate < 0.01:
            self.volt_force.step = 0.001
        elif ramp_rate < 0.1:
            self.volt_force.step = 0.010
        elif ramp_rate < 1.0:
            self.volt_force.step = 0.100
        else:
            self.volt_force.step = 1.0
        self.volt_force.inter_delay = self.volt_force.step / ramp_rate

    def _set_ramp_rate_current(self, ramp_rate):
        if ramp_rate < 0.01:
            self.current_force.step = 0.001
        elif ramp_rate < 0.1:
            self.current_force.step = 0.010
        elif ramp_rate < 1.0:
            self.current_force.step = 0.100
        else:
            self.current_force.step = 1.0
        self.current_force.inter_delay = self.current_force.step / ramp_rate

