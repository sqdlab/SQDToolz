from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
import numpy as np

class AWG5014Cchannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, channel:int) -> None:
        super().__init__(parent, name)
        self.channel = channel
        self._parent = parent

        self.add_parameter('output', label='Output state',
                           docstring='State of the output (ON or OFF).', 
                           get_cmd='OUTPut' + str(self.channel) + ':STATe?',
                           set_cmd='OUTPut' + str(self.channel) + ':STATe {}',
                           set_parser=int,
                           val_mapping={'ON':  1, 'OFF': 0})
        self.add_parameter('amplitude', label='Amplitude Vpp', unit='V',
                           docstring='Output peak-to-peak voltage amplitude.', 
                           get_cmd='SOURce'+str(channel)+':VOLTage:LEVel:IMMediate:AMPLitude?',
                           set_cmd='SOURce'+str(channel)+':VOLTage:LEVel:IMMediate:AMPLitude {}',
                           get_parser=float, set_parser=float,
                           vals=vals.Numbers(0.05, 2))
        self.add_parameter('offset', label='Output voltage offset', unit='V',
                           docstring='Output voltage offset.', 
                           get_cmd='SOURce'+str(channel)+':VOLTage:LEVel:IMMediate:OFFSet?',
                           set_cmd='SOURce'+str(channel)+':VOLTage:LEVel:IMMediate:OFFSet {}',
                           get_parser=float, set_parser=float,
                           vals=vals.Numbers(-2.25, 2.25))

        #Marker parameters
        for cur_mkr in [1,2]:
            self.add_parameter(f'marker{cur_mkr}_low', label=f'Channel {channel} Marker {cur_mkr} Voltage Low', unit='V',
                           docstring=f'Channel {channel} Marker {cur_mkr} Voltage Low level', 
                           get_cmd=f'SOURce{channel}:MARKer{cur_mkr}:VOLTage:LEVel:IMMediate:LOW?',
                           set_cmd=f'SOURce{channel}:MARKer{cur_mkr}:VOLTage:LEVel:IMMediate:LOW'+' {}',
                           get_parser=float, set_parser=float,
                           vals=vals.Numbers(-2, 2))
            self.add_parameter(f'marker{cur_mkr}_high', label=f'Channel {channel} Marker {cur_mkr} Voltage High', unit='V',
                           docstring=f'Channel {channel} Marker {cur_mkr} Voltage High level', 
                           get_cmd=f'SOURce{channel}:MARKer{cur_mkr}:VOLTage:LEVel:IMMediate:HIGH?',
                           set_cmd=f'SOURce{channel}:MARKer{cur_mkr}:VOLTage:LEVel:IMMediate:HIGH'+' {}',
                           get_parser=float, set_parser=float,
                           vals=vals.Numbers(-2, 2))

    @property
    def Parent(self):
        return self._parent
        
    @property
    def Amplitude(self):
        return self.amplitude()
    @Amplitude.setter
    def Amplitude(self, val):
        self.amplitude(val)
        
    @property
    def Offset(self):
        return self.offset()
    @Offset.setter
    def Offset(self, val):
        self.offset(val)
        
    @property
    def Output(self):
        return self.output() == 1
    @Output.setter
    def Output(self, boolVal):
        if boolVal:
            self.output('ON')
            self._parent.run()
        else:
            self.output('OFF')

class AWG5014CdcChannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, channel:int) -> None:
        super().__init__(parent, name)
        self.channel = channel
        self._parent = parent

        #!!!
        #The output state is common for all DC outputs. Therefore, irrespective of the
        #value used for ‘n’ in the command, all DC outputs are switched on or switched off
        #at once
        self.add_parameter('output', label='Output DC voltage state',
                           docstring='State of the DC voltage output (ON or OFF).', 
                           get_cmd=f'AWGC:DC{self.channel}:STATE?',
                           set_cmd='AWGC:DC'+str(self.channel)+':STATE {}',
                           set_parser=int,
                           val_mapping={'ON':  1, 'OFF': 0})
        self.add_parameter('voltage', label='Output DC voltage offset', unit='V',
                           docstring='Output DC voltage offset.', 
                           get_cmd='AWGC:DC'+str(channel)+':VOLTAGE:OFFSET?',
                           set_cmd='AWGC:DC'+str(channel)+':VOLTAGE:OFFSET {}',
                           get_parser=float, set_parser=float,
                           vals=vals.Numbers(-3, 5))
        self.add_parameter('voltage_ramp_rate', unit='V/s',
                            label="Output voltage ramp-rate",
                            initial_value=2.5e-3/0.05,
                            vals=vals.Numbers(0.001, 1),
                            get_cmd=lambda : self.voltage.step/self.voltage.inter_delay,
                            set_cmd=self._set_ramp_rate)

    def _set_ramp_rate(self, ramp_rate):
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
    def Output(self):
        return self.output() == 'ON'
    @Output.setter
    def Output(self, boolVal):
        if boolVal:
            self.output('ON')
        else:
            self.output('OFF')
        
    @property
    def Voltage(self):
        while(True):
            try:
                ret_val = self.voltage()
                break
            except:
                continue
        return ret_val
    @Voltage.setter
    def Voltage(self, val):
        self.voltage(val)
        
    @property
    def RampRate(self):
        return self.voltage_ramp_rate()
    
    @RampRate.setter
    def RampRate(self, val):
        self.voltage_ramp_rate(val)

class AWG5014C(VisaInstrument):
    '''
    Dummy driver to emulate an AWG instrument.
    '''
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        # #A 10ns output SYNC
        # self.add_submodule('SYNC', SyncTriggerPulse(10e-9, lambda : True, lambda x:x))

        self._num_samples = 10
        self._sample_rate = 10e9
        self._trigger_edge = 1

        self.add_parameter('AWG_run_state', label='Output state',
                    docstring='State of the output (ON or OFF).', 
                    get_cmd='AWGControl:RSTate?',
                    set_parser=int,
                    val_mapping={'AWG has stopped':  0,
                                 'AWG is waiting for trigger': 1,
                                 'AWG is running' : 2})
        self.add_parameter('run_mode',
                           get_cmd='AWGControl:RMODe?',
                           set_cmd='AWGControl:RMODe {}',
                           vals=vals.Enum('CONT', 'TRIG', 'SEQ', 'GAT'))

        self.add_parameter('clock_source',
                           label='Clock source',
                           get_cmd='AWGControl:CLOCk:SOURce?',
                           set_cmd='AWGControl:CLOCk:SOURce {}',
                           vals=vals.Enum('INT', 'EXT'))
        self.add_parameter('ref_clock_source',
                           label='Reference clock source',
                           get_cmd='SOURce1:ROSCillator:SOURce?',
                           set_cmd='SOURce1:ROSCillator:SOURce ' + '{}',
                           vals=vals.Enum('INT', 'EXT'))
        self.add_parameter('DC_Offset_Status',
                           label='Reference clock source',
                           get_cmd='AWGC:DC:STATE?',
                           set_cmd='AWGC:DC:STATE ' + '{}',
                           vals=vals.Enum('INT', 'EXT'))

        # Output channels added to both the module for snapshots and internal Trigger Sources for the DDG HAL...
        self._ch_list = ['CH1', 'CH2', 'CH3', 'CH4']
        for ch_ind, ch_name in enumerate(self._ch_list):
            cur_channel = AWG5014Cchannel(self, ch_name, ch_ind+1)
            self.add_submodule(ch_name, cur_channel)

        self._dc_ch_list = ['DC1', 'DC2', 'DC3', 'DC4']
        for ch_ind, ch_name in enumerate(self._dc_ch_list):
            cur_channel = AWG5014CdcChannel(self, ch_name, ch_ind+1)
            self.add_submodule(ch_name, cur_channel)

    @property
    def SampleRate(self):
        return self._sample_rate
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self._sample_rate = frequency_hertz

    @property
    def TriggerInputEdge(self):
        return self._trigger_edge
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self._trigger_edge = pol

    def num_supported_markers(self, channel_name):
        return 2

    @property
    def AutoCompressionSupport(self):
        return {'Supported' : False, 'MinSize' : 1024, 'Multiple' : 32}

    @property
    def MemoryRequirements(self):
        return {'MinSize' : 1, 'Multiple' : 1}

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]
        else:
            return None

    def run(self):
        self.write('AWGC:RUN:IMM')
    def stop(self):
        self.write('AWGC:STOP:IMM')

    def prepare_waveform_memory(self, chan_id, seg_lens, **kwargs):
        pass
        #TODO: Actually implement this...

    def program_channel(self, chan_id, dict_wfm_data):
        assert chan_id in self._ch_list, chan_id + " is an invalid channel ID for the AWG5014C."
        chan_ind = self._ch_list.index(chan_id)
        cur_chnl = self._get_channel_output(chan_id)

        default_mem_names = ['ch1_wfm','ch2_wfm','ch3_wfm','ch4_wfm','ch5_wfm','ch6_wfm','ch7_wfm','ch8_wfm']

        #Stop the AWG if it's running
        isRunning = self.AWG_run_state()
        if (isRunning != 0):
            self.stop()
        
        #Turn off the channel output if it is on
        prev_on = cur_chnl.Output
        if prev_on:
            cur_chnl.Output = False

        mkr_data = dict_wfm_data['markers'][0]
        #TODO: Setup sequence compression etc...

        #Condition data
        cur_data = dict_wfm_data['waveforms'][0]
        cur_amp = cur_chnl.Amplitude/2
        cur_off = cur_chnl.Offset
        cur_data = (cur_data - cur_off)/cur_amp

        self._send_wfm_to_memory(default_mem_names[chan_ind], cur_data, mkr_data)
        self.write(f'SOURce{chan_ind+1}:WAVeform \"{default_mem_names[chan_ind]}\"')

        #Turn on the channel output if it was previous on
        if prev_on:
            cur_chnl.Output = prev_on

        #Run AWG if it was previously running
        if (isRunning != 0):
            self.run()
    
    def _send_wfm_to_memory(self, wfm_name, wfm_data_normalised, mkr_data):
        #Delete the waveform (by name) if it already exists...
        # if self.ask(f'WLIST:WAVEFORM:PREDEFINED? \"{wfm_name}\"') == 0:
        self.write(f'WLISt:WAVeform:DELete \"{wfm_name}\"')
        #Allocate memory for the waveform
        #TODO: Could optimise this by checking waveform size and then not allocating... 
        self.write(f'WLIST:WAVEFORM:NEW \"{wfm_name}\", {wfm_data_normalised.size}, INTEGER')

        #Convert the waveform array into 14-bit format (see User Online Help in AWG5014C unit under: AWG Reference > Waveform General Information)
        data_ints = (wfm_data_normalised * 8191 + 8191).astype(np.ushort)
        data_ints = np.clip(data_ints, 0, 8191 + 8191)  #TODO: Check this arithmetic - shouldn't it be one more than this? Check actual zero value in manual
        
        if mkr_data[0].size > 0:
            data_ints += mkr_data[0].astype(np.ushort) * 2**14
        if mkr_data[1].size > 0:
            data_ints += mkr_data[1].astype(np.ushort) * 2**15

        #TODO: Write multi-block for mega waveforms
        self.visa_handle.write_binary_values(f"WLIST:WAVEFORM:DATA \"{wfm_name}\",{0},{data_ints.size},", data_ints, datatype='H')
        

        

        
