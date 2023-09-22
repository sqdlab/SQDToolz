from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
import numpy as np
import logging
import time

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

        #Reset
        self.write('J0X')

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
        
        self._sweep_safe_mode = True
        self.add_parameter('sweep_safe_mode',
                           get_cmd=lambda: self._sweep_safe_mode,
                           set_cmd=lambda x: self._set_sweep_safe_mode(x),
                           get_parser=bool,
                           set_parser=bool)
        self._sweep_sample_time_ms = 1
        self._sweep_sample_points = 20
        self._sweep_sample_start = 0
        self._sweep_sample_end = 1e-4

        self.parameters.pop('IDN')

    def _set_sweep_safe_mode(self, x):
        self._sweep_safe_mode = x

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
        pass
        #Using DC Mode by default in both cases...  #TODO: FIX THIS AS IT CASUES ERRORS...
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
        #Just infer the mode instead of querying Mode - it's faster as the F0/F1 call takes 64ms in itself...
        if res[1:5] == 'SDCV':
            return float(res.split(',')[0][5:])
        elif res.split(',')[1][1:5] == 'MDCV':
            return float(res.split(',')[1][5:])
        else:
            assert False, "COM Error when reading source-measure"
    def _set_voltage(self, val):
        #Use auto-range and zero delay by default...
        self.write(f'B{val},0,0')

    @property
    def Voltage(self):
        return self.voltage()
    @Voltage.setter
    def Voltage(self, val):
        assert self.Mode == 'SrcV_MeasI', 'Cannot set voltage in Current source mode'
        self.voltage(val)

    def _get_current(self):
        res = self.src_meas()
        #Just infer the mode instead of querying Mode - it's faster as the F0/F1 call takes 64ms in itself...
        if res[1:5] == 'SDCI':
            return float(res.split(',')[0][5:])
        elif res.split(',')[1][1:5] == 'MDCI':
            return float(res.split(',')[1][5:])
        else:
            assert False, "COM Error when reading source-measure"
    def _set_current(self, val):
        #Use auto-range and zero delay by default...
        self.write(f'B{val},0,0')

    @property
    def Current(self):
        return self.current()
    @Current.setter
    def Current(self, val):
        assert self.Mode == 'SrcI_MeasV', 'Cannot set current in Voltage source mode'
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

    @property
    def ProbeType(self):
        value = self.ask('U4')
        if value.split('O')[1][0] == '0':
            return 'TwoWire'
        else:
            return 'FourWire'
    @ProbeType.setter
    def ProbeType(self, connection):
        assert connection == 'TwoWire' or connection == 'FourWire', "ProbeType must be FourWire or TwoWire"
        if connection == 'TwoWire':
            self.write('O0')
        else:
            self.write('O1')

    
    @property
    def SupportsSweeping(self):
        return True

    @property
    def SweepSampleTime(self):
        return self._sweep_sample_time_ms / 1000
    @SweepSampleTime.setter
    def SweepSampleTime(self, smpl_time_seconds):
        self._sweep_sample_time_ms = smpl_time_seconds*1000
    
    @property
    def SweepSamplePoints(self):
        return self._sweep_sample_points
    @SweepSamplePoints.setter
    def SweepSamplePoints(self, smpl_pts):
        self._sweep_sample_points = smpl_pts
    
    @property
    def SweepStartValue(self):
        return self._sweep_sample_start
    @SweepStartValue.setter
    def SweepStartValue(self, start_val):
        self._sweep_sample_start = start_val

    @property
    def SweepEndValue(self):
        return self._sweep_sample_end
    @SweepEndValue.setter
    def SweepEndValue(self, end_val):
        self._sweep_sample_end = end_val



    def _set_ramp_rate_volt(self, ramp_rate):
        if ramp_rate < 0.01:
            self.voltage.step = 0.001
        elif ramp_rate < 0.1:
            self.voltage.step = 0.010
        elif ramp_rate < 1.0:
            self.voltage.step = 0.100
        else:
            self.voltage.step = 1.0
        self.voltage.inter_delay = self.voltage.step / ramp_rate

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

    def get_data(self):
        '''
        Function to handle measuring resistance only. This currently constitutes of a voltage/current sweep, measuring current/voltage.
        While this can be done using a standard sweep and the GENsmu HAL, this one is used to speed up a sweep.
        For example the Keithley 236 is best used with a programmed sweep.
        
        Note: If safe is False, the function assumes that it is safe to send the two extreme voltages set.
              It will jump to the start_v voltage value, sweep to the stop_v voltage value and then jump to the set bias value.

              If safe is True, the bias value must be zero and three voltage_sweeps are used. The first from 0V to start_v,
              the second used for the actual measurement and the third going back to 0V.

              Set in YAML using sweep_safe_mode parameter...
        '''
        assert self.SweepStartValue != self.SweepEndValue, "Must supply different values for the starting and ending values for the sweep..."
        assert self.SweepSamplePoints > 1, "Must have more than 1 sweeping point..."
        safe = self.sweep_safe_mode()

        self.write('G1,2,0') # get source bias
        bias = float(self.read())

        start_v, stop_v = self.SweepStartValue, self.SweepEndValue
        step = np.abs(stop_v - start_v) / (self.SweepSamplePoints-1)
        delay = self._sweep_sample_time_ms

        if safe:
            assert bias == 0, 'The bias value is not zero. This is unsafe.'

        self.ask('R0X')
        self.ask('N0X')

        old_mode = self.Mode
        if old_mode == 'SrcV_MeasI':
            if safe:
                self.Voltage = start_v
            self.ask('F0,1')        #Source Voltage, Measure Current Sweep
        else:
            if safe:
                self.Current = start_v
            self.ask('F1,1')        #Source Current, Measure Voltage Sweep

        #Using Range = 0 for autorange... c.f. page 216 of SMU manual
        # if safe:
        #     if start_v != 0:
        #         self.ask(f'Q1,{0},{start_v},{step},0,{delay}X')
        #         self.ask(f'Q7,{start_v},{stop_v},{step},0,{delay}X')
        #     else:
        #         self.ask(f'Q1,{start_v},{stop_v},{step},0,{delay}X')
        #     if stop_v != 0:
        #         self.ask(f'Q7,{stop_v},{0},{step},0,{delay}X')
        # else:
        self.ask(f'Q1,{start_v},{stop_v},{step},0,{delay}X')

        self.ask('R1XN1XH0X')  #c.f. Page 225 of the SMU manual

        # time.sleep(5)
        result = self.ask('G5,2,2X')
        meas_vals = np.array( [float(x) for x in result.replace('\r','').replace('\n',',').split(',') if len(x) > 0] )
        src_vals = meas_vals[::2]
        meas_vals = meas_vals[1::2]
        self.write('N0')

        self.Mode = old_mode

        if old_mode == 'SrcV_MeasI':
            voltages = src_vals
            currents = meas_vals
            if safe:
                self.Voltage = 0
        else:
            voltages = meas_vals
            currents = src_vals
            if safe:
                self.Current = 0

        data_pkt = {
                    'parameters' : ['Points'],
                    'data' : { 'Current' : currents, 'Voltage' : voltages }
                }

        return data_pkt