from typing import Any
import numpy as np
from qcodes import (ChannelList, InstrumentChannel, ParameterWithSetpoints,
                    VisaInstrument)
from qcodes.utils.validators import Arrays, Enum, Numbers
from qcodes import validators as vals
import time

class RigolDS1054ZChannel(InstrumentChannel):
    """
    Contains methods and attributes specific to the Rigol
    oscilloscope channels.

    The output trace from each channel of the oscilloscope
    can be obtained using 'trace' parameter.
    """

    def __init__(self,
                 parent: "DS1054Z",
                 name: str,
                 channel: int
                 ):
        super().__init__(parent, name)
        self.channel = channel

        self.add_parameter("vertical_scale",
                           get_cmd=f":CHANnel{channel}:SCALe?",
                           set_cmd=":CHANnel{}:SCALe {}".format(channel, "{}"),
                           get_parser=float
                           )

        self.add_parameter("vertical_offset",
                           get_cmd=f":CHANnel{channel}:OFFSet?",
                           set_cmd=":CHANnel{}:OFFSet {}".format(channel, "{}"),
                           get_parser=float
                           )

        self.add_parameter("input_coupling",
                           get_cmd=f":CHANnel{channel}:COUPling?",
                           set_cmd=":CHANnel{}:COUPling {}".format(channel, "{}"),
                           vals=Enum('AC', 'DC', 'GND')
                           )

        self.add_parameter("displayed",
                           get_cmd=f":CHANnel{channel}:DISPlay?",
                           set_cmd=":CHANnel{}:DISPlay {}".format(channel, "{}"),
                           val_mapping={True: '1', False: '0'}
                           )

    @property
    def VoltageRange(self):
        return self.vertical_scale() * 8    #8 vertical divisions
    @VoltageRange.setter
    def VoltageRange(self, volt_range):
        self.vertical_scale(volt_range/8)   #8 vertical divisions

    @property
    def VoltageOffset(self):
        return self.vertical_offset()
    @VoltageOffset.setter
    def VoltageOffset(self, volt_offset):
        self.vertical_offset(volt_offset)

    @property
    def InputCoupling(self):
        return self.input_coupling()
    @InputCoupling.setter
    def InputCoupling(self, coupling):
        self.input_coupling(coupling)

    @property
    def Enabled(self):
        return self.displayed()
    @Enabled.setter
    def Enabled(self, enabled):
        self.displayed(enabled)

    def _get_full_trace(self) -> np.ndarray:
        y_raw = self._get_raw_trace()*1.0
        preamble = self.ask(':WAVeform:PREamble?').split(',')
        y_ori = float(preamble[8])
        y_increm = float(preamble[7])
        y_ref = float(preamble[9])
        return (y_raw - y_ori - y_ref) * y_increm

    def _get_raw_trace(self) -> np.ndarray:
        # set the channel from where data will be obtained
        self.root_instrument.data_source(f"CH{self.channel}")

        def get_raw_data():
            return self.root_instrument.visa_handle.query_binary_values(
                    'WAV:DATA?',
                    datatype='B',   #Unsigned Char
                    is_big_endian=False,
                    expect_termination=False)

        # Obtain the trace
        numPts = self.root_instrument.waveform_npoints()
        if numPts < 250000:
            self.root_instrument.write(f':WAV:STAR 1')
            self.root_instrument.write(f':WAV:STOP {numPts}')
            while (not self.ask('*OPC?')):
                pass
            raw_trace_val = get_raw_data()
        else:
            numCycls = int(numPts / 250000)
            numRemn = int(numPts % 250000)
            data = []
            for m in range(numCycls):
                self.root_instrument.write(f':WAV:STAR {m*250000+1}')
                self.root_instrument.write(f':WAV:STOP {(m+1)*250000}')
                data += [get_raw_data()]
            if numRemn > 0:
                self.root_instrument.write(f':WAV:STAR {(m+1)*250000+1}')
                self.root_instrument.write(f':WAV:STOP {numPts}')
                data += [get_raw_data()]
            raw_trace_val = np.concatenate(data)
        return np.array(raw_trace_val)


class DSO_DS1054Z(VisaInstrument):
    """
    The QCoDeS drivers for Oscilloscope Rigol DS1074Z.

    Args:
        name: name of the instrument.
        address: VISA address of the instrument.
        timeout: Seconds to allow for responses.
        terminator: terminator for SCPI commands.
    """
    def __init__(
            self,
            name: str,
            address: str,
            terminator: str = '\n',
            timeout: float = 5,
            **kwargs: Any):
        super().__init__(name, address, terminator=terminator, timeout=timeout,
                         **kwargs)

        self._allowed_time_divs = [ 5e-9, 1e-8, 2e-8, 5e-8,
                                    1e-7, 2e-7, 5e-7,
                                    1e-6, 2e-6, 5e-6,
                                    1e-5, 2e-5, 5e-5,
                                    1e-4, 2e-4, 5e-4,
                                    1e-3, 2e-3, 5e-3,
                                    1e-2, 2e-2, 5e-2,
                                    1e-1, 2e-1, 5e-1,
                                    1, 2, 5,
                                    10, 20, 50]

        self.add_parameter('time_per_division',
                           get_cmd=':TIMebase:MAIN:SCALe?',
                           set_cmd=':TIMebase:MAIN:SCALe {}',
                           unit='s',
                           vals = vals.Enum(*self._allowed_time_divs),
                           get_parser=float
                           )

        self.add_parameter('mem_depth',
                           get_cmd=':ACQuire:MDEPth?',
                           set_cmd=':ACQuire:MDEPth {}',
                           get_parser=int
                           )

        self.add_parameter('waveform_xorigin',
                           get_cmd='WAVeform:XORigin?',
                           unit='s',
                           get_parser=float
                           )

        self.add_parameter('waveform_xincrem',
                           get_cmd=':WAVeform:XINCrement?',
                           unit='s',
                           get_parser=float
                           )

        self.add_parameter('waveform_npoints',
                           get_cmd=self._get_num_pts,
                           unit='s',
                           get_parser=int
                           )

        self.add_parameter('waveform_yorigin',
                           get_cmd='WAVeform:YORigin?',
                           unit='V',
                           get_parser=float
                           )

        self.add_parameter('waveform_yincrem',
                           get_cmd=':WAVeform:YINCrement?',
                           unit='V',
                           get_parser=float
                           )

        self.add_parameter('waveform_yref',
                           get_cmd=':WAVeform:YREFerence?',
                           unit='V',
                           get_parser=float
                           )

        self.add_parameter('trigger_mode',
                           get_cmd=':TRIGger:MODE?',
                           set_cmd=':TRIGger:MODE {}',
                           unit='V',
                           vals=Enum('edge',
                                     'pulse',
                                     'video',
                                     'pattern'
                                     ),
                           get_parser=str
                           )

        # trigger source
        self.add_parameter('trigger_level',
                           unit='V',
                           get_cmd=self._get_trigger_level,
                           set_cmd=self._set_trigger_level,
                           get_parser=float
                           )

        self.add_parameter('trigger_edge_source',
                           label='Source channel for the edge trigger',
                           get_cmd=':TRIGger:EDGE:SOURce?',
                           set_cmd=':TRIGger:EDGE:SOURce {}',
                           val_mapping={'CH1': 'CHAN1',
                                        'CH2': 'CHAN2',
                                        'CH3': 'CHAN3',
                                        'CH4': 'CHAN4'
                                        }
                           )

        self.add_parameter('trigger_edge_slope',
                           label='Slope of the edge trigger',
                           get_cmd=':TRIGger:EDGE:SLOPe?',
                           set_cmd=':TRIGger:EDGE:SLOPe {}',
                           vals=Enum('positive', 'negative', 'neither')
                           )

        self.add_parameter('trigger_status',
                           label='Slope of the edge trigger',
                           get_cmd=':TRIGger:STATus?',
                           vals=Enum('TD', 'WAIT', 'RUN', 'AUTO', 'STOP')
                           )

        self.add_parameter('data_source',
                           label='Waveform Data source',
                           get_cmd=':WAVeform:SOURce?',
                           set_cmd=':WAVeform:SOURce {}',
                           val_mapping={'CH1': 'CHAN1',
                                        'CH2': 'CHAN2',
                                        'CH3': 'CHAN3',
                                        'CH4': 'CHAN4'
                                        }
                           )

        self.add_parameter('time_axis',
                           unit='s',
                           label='Time',
                           set_cmd=False,
                           get_cmd=self._get_time_axis,
                           vals=Arrays(shape=(self.waveform_npoints,)),
                           snapshot_value=False
                           )

        channels = ChannelList(self,
                               "channels",
                               RigolDS1054ZChannel,
                               snapshotable=False
                               )

        self._input_channels = {}
        for channel_number in range(1, 5):
            leName = f"CH{channel_number}"
            channel = RigolDS1054ZChannel(self,
                                          leName,
                                          channel_number
                                          )
            channels.append(channel)
            self._input_channels[leName] = channel

        channels.lock()
        self.add_submodule('channels', channels)

        # set the out type from oscilloscope channels to BYTE
        self.root_instrument.write(':WAVeform:FORMat BYTE')
        self.root_instrument.write(':WAVeform:MODE RAW')
        self.root_instrument.write(':mem_depth 12000000')

        self.connect_message()

    def _get_allowed_memory_depths(self):
        num_chs_enabled = 0
        for ch in self._input_channels:
            if self._input_channels[ch].Enabled:
                num_chs_enabled += 1
        if num_chs_enabled > 2:
            return [3000, 30000, 300000, 3000000, 6000000]
        elif num_chs_enabled == 2:
            return [6000, 60000, 600000, 6000000, 12000000]
        else:
            return [12000, 120000, 1200000, 12000000, 24000000]

    def _get_num_pts(self):
        return int(self.ask(':WAVeform:PREamble?').split(',')[2])

    def _get_time_axis(self) -> np.ndarray:
        preamble = self.ask(':WAVeform:PREamble?').split(',')
        xorigin = float(preamble[5])
        xincrem = float(preamble[4])
        npts = int(preamble[2])
        xdata = np.linspace(xorigin, npts * xincrem + xorigin, npts)
        return xdata

    def _get_trigger_level(self) -> str:
        trigger_level = self.root_instrument.ask(f":TRIGger:{self.trigger_mode()}:LEVel?")
        return trigger_level

    def _set_trigger_level(self, value: str) -> None:
        self.root_instrument.write(f":TRIGger:{self.trigger_mode()}:LEVel {value}")


    def get_output(self, identifier):
        return self._input_channels[identifier]

    def get_all_outputs(self):
        return [(x,self._input_channels[x]) for x in self._input_channels]

    @property
    def SampleRate(self):
        return float(self.ask(':ACQuire:SRATe?'))
    @SampleRate.setter
    def SampleRate(self, sample_rate):
        numpts = int(self.mem_depth())
        total_time = numpts / sample_rate
        t_per_div = total_time / 12   #12 divisions on screen...
        #
        min_ind = np.argmin(np.abs(np.array(self._allowed_time_divs) - t_per_div))
        self.time_per_division(self._allowed_time_divs[min_ind])

    @property
    def NumSamples(self):
        return int(self.mem_depth())
    @NumSamples.setter
    def NumSamples(self, num_points):
        self.write(':RUN')
        allowed_mem_depths = np.array(self._get_allowed_memory_depths())
        min_ind = np.argmin(np.abs(allowed_mem_depths - num_points))
        self.mem_depth(allowed_mem_depths[min_ind])
        self.write(':STOP')

    @property
    def ACQTriggerChannel(self):
        return self.trigger_edge_source()
    @ACQTriggerChannel.setter
    def ACQTriggerChannel(self, ch_id):
        self.trigger_edge_source(ch_id)

    @property
    def ACQTriggerSlope(self):
        return self.trigger_edge_slope()
    @ACQTriggerSlope.setter
    def ACQTriggerSlope(self, slope_type):
        if slope_type == 'POS':
            self.trigger_edge_slope('positive')
        elif slope_type == 'NEG':
            self.trigger_edge_slope('negative')
        elif slope_type == 'BOTH':
            self.trigger_edge_slope('neither')

    @property
    def ACQTriggerVoltageLevel(self):
        return self.trigger_level()
    @ACQTriggerVoltageLevel.setter
    def ACQTriggerVoltageLevel(self, volt_level):
        self.trigger_level(volt_level)

    def get_data(self, **kwargs):
        self.write(':STOP')

        self.write(':SINGle')
        triggered = False
        for m in range(1000):
            if self.trigger_status() == 'STOP':
                triggered = True
                break
            time.sleep(0.01)
        assert triggered, "Timed out trying to find trigger."
        while (not self.ask('*OPC?')):
            pass
        time.sleep(0.5)

        cur_processor = kwargs.get('data_processor', None)

        data_pkt = {
                'parameters' : ['time'],
                'parameter_values' : {},
                'data' : {},
                'misc' : {}
            }
        num_chs = 0
        for cur_ch in self._input_channels:
            if self._input_channels[cur_ch].Enabled:
                data_pkt['data'][cur_ch] = self._input_channels[cur_ch]._get_full_trace()
                num_chs += 1
        data_pkt['parameter_values']['time'] = self._get_time_axis()
        data_pkt['misc']['SampleRates'] = [self.SampleRate]*num_chs

        cur_proc = kwargs.get('data_processor', None)
        if cur_proc:
            cur_proc.push_data(data_pkt['data'])
            data_pkt['data'] = cur_proc.get_all_data()
        return {'data': data_pkt}
        


if __name__ == '__main__':
    osc = DSO_DS1054Z('test','TCPIP::10.42.95.46::INSTR')
    data_pkt = osc.get_data()
    import matplotlib.pyplot as plt
    plt.plot(x_vals, data)
    plt.plot(x_vals, data2+10)
    # plt.plot(x_vals, data3+20)
    plt.show()
    input('test')
    a = 0