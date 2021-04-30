from qcodes import Instrument, VisaInstrument, InstrumentChannel, validators as vals

class MultiDACchannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name, param_volt) -> None:
        super().__init__(parent, name)
        self._parent = parent
        self._param_volt = param_volt

        #NOTE: Although the ramp-rate is technically software-based, there could be a source that provides actual precision rates - so it's left as a parameter in general instead of being a HAL-level feature...
        self.add_parameter('voltage_ramp_rate', unit='V/s',
                        label="Output voltage ramp-rate",
                        initial_value=2.5e-3/0.05,
                        vals=vals.Numbers(0.001, 1),
                        get_cmd=lambda : self.voltage.step/self.voltage.inter_delay,
                        set_cmd=self._set_ramp_rate)

    def _set_ramp_rate(self, ramp_rate):
        if ramp_rate < 0.01:
            self._param_volt.step = 0.001
        elif ramp_rate < 0.1:
            self._param_volt.step = 0.010
        elif ramp_rate < 1.0:
            self._param_volt.step = 0.100
        else:
            self._param_volt.step = 1.0
        self._param_volt.inter_delay = self._param_volt.step / ramp_rate
        
    @property
    def Voltage(self):
        return self._param_volt()
    @Voltage.setter
    def Voltage(self, val):
        self._param_volt(val)
        
    @property
    def RampRate(self):
        return self.voltage_ramp_rate()
    @RampRate.setter
    def RampRate(self, val):
        self.voltage_ramp_rate(val)

class VOLT_RpiMultiDAC(VisaInstrument):
    '''
    Control DACs connected to Raspberry PI SPI pins running a DAC SCPI server
    '''
    def __init__(self, name, address, nch, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)
        # add parameters
        self.add_parameter(
            'nch', label='Number of outputs',
            get_cmd='SOUR:NCH?', get_parser=int,
            set_cmd='SOUR:NCH {:d}', vals=vals.Numbers(min_value=0))

        self.nch.set(nch)
        self._ch_objs = []
        for m in range(1,1+nch):
            prefix = 'SOUR:VOLT{:d}'.format(m)
            cur_name = '_raw_voltage_param{:d}'.format(m)
            self.add_parameter(
                cur_name, unit='V', 
                get_cmd=prefix+'?', get_parser=float, 
                set_cmd=prefix+' {:f}', vals=vals.Numbers(-10., 10.*(1-2**(-15)))
            )
            cur_channel = MultiDACchannel(self, f'CH{m}', self.parameters[cur_name])
            self.add_submodule(f'CH{m}', cur_channel)

        self.connect_message()
