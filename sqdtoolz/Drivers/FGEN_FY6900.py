from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
import numpy as np
import serial

class FGEN_FY6900_ChannelModule(InstrumentChannel):
    def __init__(self, parent:Instrument, chan_num, leName) -> None:
        super().__init__(parent, leName)
        self._parent = parent
        self._chan_num = chan_num
        self._prefix = 'M' if chan_num == 1 else 'F'

        self.lookup_waveform_to_index = {
            'SINE': 0,
            'SQUARE': 1,
            'SAWTOOTH': 8,  #i.e. "Ramp"...
            'TRIANGLE': 7,
            'PULSE': 2      #i.e. "Rectangle"...
        }
        if chan_num == 2:
            self.lookup_waveform_to_index['SAWTOOTH'] = 7
            self.lookup_waveform_to_index['TRIANGLE'] = 6
        self.lookup_index_to_waveform = {v: k for k, v in self.lookup_waveform_to_index.items()}

        self.add_parameter('waveform_type',
                        get_cmd = self._get_waveform_type,
                        set_cmd = self._set_waveform_type,
                        vals = vals.Enum(*[x for x in self.lookup_waveform_to_index]))

        self.add_parameter('frequency', unit='Hz',
                        label="Output frequency",
                        vals=vals.Numbers(0.01, 100e6),
                        get_cmd=self._get_frequency,
                        set_cmd=self._set_frequency,
                        inter_delay=0.05)

        self.add_parameter('voltage_amplitude', unit='V',
                        label="Output amplitude",
                        vals=vals.Numbers(0, 10),
                        get_cmd=self._get_voltage_amplitude,
                        set_cmd=self._set_voltage_amplitude,
                        inter_delay=0.05)

        self.add_parameter('voltage_offset', unit='V',
                        label="Output voltage offset",
                        vals=vals.Numbers(-12, 12),
                        get_cmd=self._get_voltage_offset,
                        set_cmd=self._set_voltage_offset,
                        inter_delay=0.05)

        self.add_parameter('duty_cycle', unit=r"%",
                        label="Output duty cycle",
                        vals=vals.Numbers(0.01, 99.99),
                        get_cmd=self._get_duty_cycle,
                        set_cmd=self._set_duty_cycle,
                        inter_delay=0.05)

        self.add_parameter(name = 'output',
                        label = 'Output status',
                        get_cmd = self._get_output,
                        set_cmd = self._set_output,
                        vals = vals.Enum(True, False))


    def _get_waveform_type(self):
        for m in range(10):
            try:
                result = int(self._parent.query(f'R{self._prefix}W\n').strip())
            except ValueError:
                continue
            if not result in self.lookup_index_to_waveform:
                print("Warning: The function generator is set to a mode unsupported by this driver. Setting to SINE.")
                self._set_waveform_type('SINE')
            return self.lookup_index_to_waveform[result]
    def _set_waveform_type(self, val):
        for m in range(10):
            if self._parent.query(f'W{self._prefix}W{self.lookup_waveform_to_index[val]}\n') == '\n':
                return

    def _get_frequency(self):
        for m in range(10):
            try:
                result = float(self._parent.query(f'R{self._prefix}F\n').strip())
            except ValueError:
                continue
            return result
    def _set_frequency(self, val):
        for m in range(10):
            if self._parent.query(f'W{self._prefix}F{val:015.6f}\n') == '\n':
                return

    def _get_voltage_amplitude(self):
        for m in range(10):
            try:
                result = int(self._parent.query(f'R{self._prefix}A\n').strip())
                result = result / 10000.0 / 2.0   #It returns Vpp...
            except ValueError:
                continue
            return result
    def _set_voltage_amplitude(self, val):
        for m in range(10):
            if self._parent.query(f'W{self._prefix}A{(val*2):.4f}\n') == '\n':
                return

    def _get_voltage_offset(self):
        for m in range(10):
            try:
                result = int(self._parent.query(f'R{self._prefix}O\n').strip())
                if result >= 2147483648: #2^31
                    result -= 2**32
                result /= 1000.0
            except ValueError:
                continue
            return result
    def _set_voltage_offset(self, val):
        for m in range(10):
            if self._parent.query(f'W{self._prefix}O{val:.3f}\n') == '\n':
                return

    def _get_duty_cycle(self):
        for m in range(10):
            try:
                result = int(self._parent.query(f'R{self._prefix}D\n').strip())
                result /= 1000.0
            except ValueError:
                continue
            return result
    def _set_duty_cycle(self, val):
        for m in range(10):
            if self._parent.query(f'W{self._prefix}D{val:.3f}\n') == '\n':
                return

    def _get_output(self):
        for m in range(10):
            try:
                result = int(self._parent.query(f'R{self._prefix}N\n').strip())
            except ValueError:
                continue
            return not result == 0
    def _set_output(self, val):
        val = 1 if val else 0
        for m in range(10):
            if self._parent.query(f'W{self._prefix}N{val}\n') == '\n':
                return

    @property
    def Output(self):
        return self.output()
    @Output.setter
    def Output(self, val):
        self.output(val)

    @property
    def Waveform(self):
        return self.waveform_type()
    @Waveform.setter
    def Waveform(self, val):
        self.waveform_type(val)

    @property
    def Frequency(self):
        return self.frequency()
    @Frequency.setter
    def Frequency(self, val):
        self.frequency(val)

    @property
    def Amplitude(self):
        return self.voltage_amplitude()
    @Amplitude.setter
    def Amplitude(self, val):
        self.voltage_amplitude(val)

    @property
    def Offset(self):
        return self.voltage_offset()
    @Offset.setter
    def Offset(self, val):
        self.voltage_offset(val)

    @property
    def DutyCycle(self):
        return self.duty_cycle()
    @DutyCycle.setter
    def DutyCycle(self, val):
        self.duty_cycle(val)



class FGEN_FY6900(Instrument):
    """This class represents and controls the FeelElec FY6900 function generator. The driver is inspired by
    the GitHub repository: https://github.com/mattwach/fygen/blob/master/fygen.py."""

    def __init__(self, name, address, **kwargs):
        super().__init__(name, **kwargs)

        self.description = "FeelElec FY6900 Function/Arbitrary waveform generator."
        self.expectedMfr = "FeelElec"
        self.expectedModel = "FY6900"
        
        self.ser = serial.Serial(port=address, baudrate=115200, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

        for m in range(2):  #Loop to flush any previous errors...
            idn_str = self.query('UMO\n')
        assert len(idn_str) >= 6 and idn_str[:6] == 'FY6900', "The model is not compatible with this driver." #TODO: Could look into expanding this for other models?

        self._source_outputs = {}
        for ch_ind in [1,2]:
            leName = f'CH{ch_ind}'
            cur_module = FGEN_FY6900_ChannelModule(self, ch_ind, leName)
            self.add_submodule(leName, cur_module)    #Name is christened inside the channel object...
            self._source_outputs[leName] = cur_module

    def write(self, cmd):
        self.ser.write(bytes(cmd,encoding='utf-8'))

    def query(self, cmd):
        self.write(cmd)
        ret_str = self.ser.read(1024)
        ret_str = ret_str.decode(encoding='utf-8')
        return ret_str

    def get_output(self, identifier):
        return self._source_outputs[identifier]

    def get_all_outputs(self):
        return [(x,self._source_outputs[x]) for x in self._source_outputs]

    def get_idn(self):
        return {'vendor': 'FeelElec', 'model': 'FY6900', 'serial': None, 'firmware': None}

if __name__ == '__main__':
    FGEN_FY6900('fgen', '/dev/ttyUSB0')
    a=0

