from typing import Any

import numpy as np
from qcodes import (ChannelList, InstrumentChannel, ParameterWithSetpoints,
                    VisaInstrument)
from qcodes.utils.validators import Arrays, Enum, Numbers


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

        self.add_parameter("trace",
                           get_cmd=self._get_full_trace,
                           vals=Arrays(shape=(self.parent.waveform_npoints,)),
                           setpoints=(self.parent.time_axis,),
                           unit='V',
                           parameter_class=ParameterWithSetpoints,
                           snapshot_value=False
                           )

    def _get_full_trace(self) -> np.ndarray:
        y_raw = self._get_raw_trace()*1.0
        preamble = self.ask(':WAVeform:PREamble?').split(',')
        y_ori = float(preamble[8])
        y_increm = float(preamble[7])
        y_ref = float(preamble[9])
        return (y_raw - y_ori - y_ref) * y_increm

    def _get_raw_trace(self) -> np.ndarray:
        # set the channel from where data will be obtained
        self.root_instrument.data_source(f"ch{self.channel}")

        # set the out type from oscilloscope channels to BYTE
        self.root_instrument.write(':WAVeform:FORMat BYTE')
        self.root_instrument.write(':WAVeform:MODE RAW')

        def get_raw_data():
            return self.root_instrument.visa_handle.query_binary_values(
                    'WAV:DATA?',
                    datatype='B',   #Unsigned Char
                    is_big_endian=False,
                    expect_termination=False)

        # Obtain the trace
        numPts = self.root_instrument.waveform_npoints()
        if numPts < 250000:
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


class DS1054Z(VisaInstrument):
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
                           vals=Numbers()
                           )

        self.add_parameter('trigger_edge_source',
                           label='Source channel for the edge trigger',
                           get_cmd=':TRIGger:EDGE:SOURce?',
                           set_cmd=':TRIGger:EDGE:SOURce {}',
                           val_mapping={'ch1': 'CHAN1',
                                        'ch2': 'CHAN2',
                                        'ch3': 'CHAN3',
                                        'ch4': 'CHAN4'
                                        }
                           )

        self.add_parameter('trigger_edge_slope',
                           label='Slope of the edge trigger',
                           get_cmd=':TRIGger:EDGE:SLOPe?',
                           set_cmd=':TRIGger:EDGE:SLOPe {}',
                           vals=Enum('positive', 'negative', 'neither')
                           )

        self.add_parameter('data_source',
                           label='Waveform Data source',
                           get_cmd=':WAVeform:SOURce?',
                           set_cmd=':WAVeform:SOURce {}',
                           val_mapping={'ch1': 'CHAN1',
                                        'ch2': 'CHAN2',
                                        'ch3': 'CHAN3',
                                        'ch4': 'CHAN4'
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

        for channel_number in range(1, 5):
            channel = RigolDS1054ZChannel(self,
                                          f"ch{channel_number}",
                                          channel_number
                                          )
            channels.append(channel)

        channels.lock()
        self.add_submodule('channels', channels)

        self.connect_message()

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


# osc = DS1054Z('test','TCPIP::...::INSTR')
# data = osc.channels.ch1.trace()
# data2 = osc.channels.ch2.trace()
# data3 = osc.channels.ch3.trace()
# x_vals = osc._get_time_axis()
# import matplotlib.pyplot as plt
# plt.plot(x_vals, data)
# plt.plot(x_vals, data2+10)
# plt.plot(x_vals, data3+20)
# plt.show()
# input('test')
# a = 0