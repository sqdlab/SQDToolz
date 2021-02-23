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
        else:
            self.output('OFF')

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

        # Output channels added to both the module for snapshots and internal Trigger Sources for the DDG HAL...
        self._ch_list = ['CH1', 'CH2', 'CH3', 'CH4']
        for ch_ind, ch_name in enumerate(self._ch_list):
            cur_channel = AWG5014Cchannel(self, ch_name, ch_ind+1)
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

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]
        else:
            return None

    def run(self):
        self.write('AWGC:RUN:IMM')
    def stop(self):
        self.write('AWGC:STOP:IMM')

    def program_channel(self, chan_id, wfm_data, mkr_data = np.array([])):
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

        #Condition data
        cur_data = wfm_data
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
        self.write(f'WLISt:WAVeform:DELete {wfm_name}')
        #Allocate memory for the waveform
        #TODO: Could optimise this by checking waveform size and then not allocating... 
        self.write(f'WLIST:WAVEFORM:NEW \"{wfm_name}\", {wfm_data_normalised.size}, INTEGER')

        #Convert the waveform array into 14-bit format (see User Online Help in AWG5014C unit under: AWG Reference > Waveform General Information)
        data_ints = (wfm_data_normalised * 8191 + 8191).astype(np.int16)
        
        if mkr_data[0].size > 0:
            data_ints += mkr_data[0] * 2**14
        if mkr_data[1].size > 0:
            data_ints += mkr_data[1] * 2**15

        #TODO: Write multi-block for mega waveforms
        self.visa_handle.write_binary_values(f"WLIST:WAVEFORM:DATA \"{wfm_name}\",{0},{data_ints.size},", data_ints, datatype='H')
        

        

        
