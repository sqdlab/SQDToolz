import os
import sys
from sqdtoolz.Drivers.Dependencies.teproteus import TEProteusAdmin as TepAdmin
from sqdtoolz.Drivers.Dependencies.teproteus import TEProteusInst as TepInst

import numpy as np
import time

from qcodes import Instrument, InstrumentChannel, validators as vals
from qcodes.instrument.parameter import ManualParameter
import numpy as np
from functools import partial

class AWG_TaborP2584M_channel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, channel: int) -> None:
        super().__init__(parent, name)
        self._parent = parent
        self._channel = channel
        self._outputEnable = True
        self._amp = 1.0
        self._off = 0.0

        self.add_parameter(
            'amplitude', label='Amplitude', unit='V',
            get_cmd=partial(self._get_cmd, ':SOUR:VOLT:AMPL?'),
            set_cmd=partial(self._set_cmd, ':SOUR:VOLT:AMPL'),
            vals=vals.Numbers(1e-3, 1.2),
            get_parser=lambda x : 2*float(x),
            set_parser=lambda x: 0.5*x)
        self.add_parameter(
            'offset', label='Offset', unit='V',
            get_cmd=partial(self._get_cmd, ':SOUR:VOLT:OFFS?'),
            set_cmd=partial(self._set_cmd, ':SOUR:VOLT:OFFS'),
            vals=vals.Numbers(-0.5, 0.5),
            get_parser=float)
        self.add_parameter(
            'output', label='Output Enable',
            get_cmd=partial(self._get_cmd, ':OUTP?'),
            set_cmd=partial(self._set_cmd, ':OUTP'),
            val_mapping={True: 'ON', False: 'OFF'})

        self.add_parameter(
            'trig_src', label='Output Enable',
            parameter_class=ManualParameter,
            initial_value='NONE',
            vals=vals.Enum('NONE','TRG1','TRG2'))
        
        #Marker parameters
        for cur_mkr in [1,2]:
            self.add_parameter(
                f'marker{cur_mkr}_output', label=f'Channel {channel} Marker {cur_mkr-1} output',
                get_cmd=partial(self._get_mkr_cmd, ':MARK?', cur_mkr),
                set_cmd=partial(self._set_mkr_cmd, ':MARK', cur_mkr),
                val_mapping={True: 'ON', False: 'OFF'})
            self._set_mkr_cmd(':MARK:VOLT:PTOP', cur_mkr, 1.2)


    def _get_cmd(self, cmd):
        #Perform channel-select
        self._parent.parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Query command
        return self._parent.parent._inst.send_scpi_query(cmd)

    def _set_cmd(self, cmd, value):
        #Perform channel-select
        self._parent.parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Perform command
        self._parent.parent._inst.send_scpi_cmd(f'{cmd} {value}')

    def _get_mkr_cmd(self, cmd, mkr_num):
        #Perform channel-select
        self._parent.parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Perform marker-select
        self._parent.parent._inst.send_scpi_cmd(f':MARK:SEL {mkr_num}')
        #Perform command
        return self._parent.parent._inst.send_scpi_query(cmd)

    def _set_mkr_cmd(self, cmd, mkr_num, value):
        #Perform channel-select
        self._parent.parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Perform marker-select
        self._parent.parent._inst.send_scpi_cmd(f':MARK:SEL {mkr_num}')
        #Perform command
        self._parent.parent._inst.send_scpi_cmd(f'{cmd} {value}')


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
        return self.output()
    @Output.setter
    def Output(self, boolVal):
        self.output(boolVal)

class AWG_TaborP2584M_task:
    def __init__(self, seg_num, num_cycles, next_task_ind, trig_src='NONE'):
        self.seg_num = seg_num
        self.num_cycles = num_cycles
        self.next_task_ind = next_task_ind  #NOTE: Indexed from 1
        self.trig_src = trig_src

class TaborP2584M_AWG(InstrumentChannel):
    def __init__(self, parent):
        super().__init__(parent, 'AWG')
        self._parent = parent

        self._parent._set_cmd(':INST:CHAN', 1)
        self._parent._send_cmd(':TRAC:DEL:ALL')        

        #Get the DAC mode (8 bits or 16 bits)
        dac_mode = self._parent._get_cmd(':SYST:INF:DAC?')
        if dac_mode == 'M0':
            self._max_dac = 65535
            self._data_type = np.uint16 
        else:
            self._max_dac = 255
            self._data_type = np.uint8 
        self._half_dac = self._max_dac // 2.0

        #Get number of channels
        self._num_channels = int(self._parent._get_cmd(":INST:CHAN? MAX"))
        #Get the maximal number of segments
        self._max_seg_number = int(self._parent._get_cmd(":TRACe:SELect:SEGMent? MAX"))
        #Get the available memory in bytes of wavform-data (per DDR):
        self._arbmem_capacity_bytes = int(self._parent._get_cmd(":TRACe:FREE?"))
        
        self.add_parameter(
            'sample_rate', label='Sample Rate', unit='Hz',
            get_cmd=partial(self._parent._get_cmd, ':SOUR:FREQ:RAST?'),
            set_cmd=partial(self._parent._set_cmd, ':SOUR:FREQ:RAST'),
            vals=vals.Numbers(1e9, 9e9),    #Note that this is a cheat using Nyquist trickery...
            get_parser=float)
            
        #Setup triggering
        # self._set_cmd(':TRIG:SOUR:ENAB', 'TRG1')
        self._parent._set_cmd(':TRIG:SEL', 'TRG1')
        self._parent._set_cmd(':TRIG:STAT', 'ON')
        self._parent._set_cmd(':TRIG:LEV', 0.3)
        self._parent._set_cmd(':TRIG:SEL', 'TRG2')
        self._parent._set_cmd(':TRIG:STAT', 'OFF')
        self._parent._set_cmd(':TRIG:SEL', 'INT')
        self._parent._set_cmd(':TRIG:STAT', 'OFF')
        # self._set_cmd(':INIT:CONT', 'OFF')

        self._trigger_edge = 1

        self._ch_list = ['CH1', 'CH2', 'CH3', 'CH4']
        # Output channels added to both the module for snapshots and internal Trigger Sources for the DDG HAL...
        for ch_ind, ch_name in enumerate(self._ch_list):
            cur_channel = AWG_TaborP2584M_channel(self, ch_name, ch_ind+1)
            self.add_submodule(ch_name, cur_channel)
        self._used_memory_segments = [None]*2

        self._sequence_cache = {}
        for ch_name in self._ch_list:
            self._sequence_cache[ch_name] = {'seq_segs' : [], 'seq_ids' : [], 'mkr_data' : None}

    @property
    def SampleRate(self):
        return self.sample_rate()
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self.sample_rate(frequency_hertz)

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
        return {'Supported' : True, 'MinSize' : 1024, 'Multiple' : 32}

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]  #!!!NOTE: Note from above in the initialiser regarding the parent storing the AWG channel submodule
        else:
            return None

    def program_channel(self, chan_id, wfm_data, mkr_data = np.array([])):
        chan_ind = self._ch_list.index(chan_id)
        cur_chnl = self._get_channel_output(chan_id)

        #Condition the waveform
        cur_data = wfm_data
        cur_amp = cur_chnl.Amplitude/2
        cur_off = cur_chnl.Offset
        cur_data = (cur_data - cur_off)/cur_amp
        
        #So channels 1 and 2 share segment memory and channels 3 and 4 share a separate bank of segment memory
        #Idea is to use 1 segment for each waveform channel inside said bank...
        
        #Select channel
        self._parent._set_cmd(':INST:CHAN', chan_ind+1)
        #Delete and Define segment (noting that it's taken as 1 or 2 for channels 1|3 and 2|4 respectively...)
        seg_id = int(chan_ind % 2 + 1)
        self._parent._set_cmd('TRAC:DEL', seg_id)
        self._parent._send_cmd(f':TRAC:DEF {seg_id}, {cur_data.size}')
        
        # self._send_data_to_memory(seg_id, cur_data)
        self._send_data_to_memory(seg_id, cur_data, mkr_data)
        self._program_task_table(chan_ind+1, [AWG_TaborP2584M_task(seg_id, 1, 1, cur_chnl.trig_src())])
        
        self._parent._set_cmd('FUNC:MODE', 'TASK')

    def prepare_sequence(self, chan_id, seq_segs, seq_ids, mkr_data = np.array([])):
        self._sequence_cache[chan_id]['seq_segs'] = seq_segs
        self._sequence_cache[chan_id]['seq_ids'] = seq_ids
        self._sequence_cache[chan_id]['mkr_data'] = mkr_data
        self._banks_setup = False

    def _setup_memory_banks(chan_id):

        self._banks_setup = True

    def finalise_waveforms(self, chan_id):
        chan_ind = self._ch_list.index(chan_id)
        cur_chnl = self._get_channel_output(chan_id)

        #Select channel
        self._parent._set_cmd(':INST:CHAN', chan_ind+1)

        #A function that needs to be called once - it'll be done on the first channel to be programmed...
        if not self._banks_setup:
            self._setup_memory_banks()

        if chan_ind+1 == 1:
            #The first few segments are free realestate.




    def program_channel_sequence(self, chan_id, seq_segs, seq_ids, mkr_data = np.array([])):
        

        #Condition the waveform
        cur_amp = cur_chnl.Amplitude/2
        cur_off = cur_chnl.Offset
        for m in range(len(seq_segs)):
            seq_segs[m] = (seq_segs[m] - cur_off)/cur_amp
        
        #So channels 1 and 2 share segment memory and channels 3 and 4 share a separate bank of segment memory
        #Idea is to use 1 segment for each waveform channel inside said bank...
        
        #Select channel
        self._parent._set_cmd(':INST:CHAN', chan_ind+1)
        #Delete and Define segment (noting that it's taken as 1 or 2 for channels 1|3 and 2|4 respectively...)
        seg_id = int(chan_ind % 2 + 1)
        self._parent._set_cmd('TRAC:DEL', seg_id)
        self._parent._send_cmd(f':TRAC:DEF {seg_id}, {cur_data.size}')
        
        # self._send_data_to_memory(seg_id, cur_data)
        self._send_data_to_memory(seg_id, cur_data, mkr_data)
        self._program_task_table(chan_ind+1, [AWG_TaborP2584M_task(seg_id, 1, 1, cur_chnl.trig_src())])
        
        self._parent._set_cmd('FUNC:MODE', 'TASK')

    def _program_task_table(self, channel_index, tasks):
        #Select current channel
        self._parent._set_cmd(':INST:CHAN', channel_index)
        #Allocate a set number of rows for the task table
        self._parent._set_cmd(':TASK:COMP:LENG', len(tasks))

        #Check that there is at most one trigger source and record it if applicable
        cur_trig_src = ''
        for cur_task in tasks:
            if cur_task.trig_src != '' and cur_task.trig_src != 'NONE':
                assert cur_trig_src == '' or cur_trig_src == cur_task.trig_src, "Cannot have multiple trigger sources for a given Tabor channel input."
                cur_trig_src = cur_task.trig_src

        for task_ind, cur_task in enumerate(tasks):
            self._parent._set_cmd(':TASK:COMP:SEL', task_ind + 1)
            #Set the task to be solitary (i.e. not a part of an internal sequence inside Tabor...)
            self._parent._send_cmd(':TASK:COMP:TYPE SING')
            #Set task parameters...
            self._parent._set_cmd(':TASK:COMP:LOOP', cur_task.num_cycles)
            self._parent._set_cmd(':TASK:COMP:SEGM', cur_task.seg_num)
            self._parent._set_cmd(':TASK:COMP:NEXT1', cur_task.next_task_ind)
            self._parent._set_cmd(':TASK:COMP:ENAB', cur_task.trig_src)
      
        #Download task table to channel
        self._parent._send_cmd(':TASK:COMP:WRIT')
        # self._set_cmd(':FUNC:MODE', 'TASK')

        #Check for errors...
        self._parent._chk_err('after writing task table.')

        #Enable triggers if applicable to this channel
        if cur_trig_src != '':
            #Select current channel (just in case)
            self._parent._set_cmd(':INST:CHAN', channel_index)
            #Enable triggers...
            self._parent._set_cmd(':TRIG:SEL', cur_trig_src)
            self._parent._set_cmd(':TRIG:STAT', 'ON')
        
    def _send_data_to_memory(self, seg_ind, wfm_data_normalised, mkr_data):
        #Condition the data
        final_data = (wfm_data_normalised * self._half_dac + self._half_dac).astype(self._data_type)
        #Select the segment
        self._parent._set_cmd(':TRAC:SEL', seg_ind)
        #Increase the timeout before writing binary-data:
        self._parent._inst.timeout = 30000
        #Send the binary-data with *OPC? added to the beginning of its prefix.
        # self._inst.write_binary_data('*OPC?; :TRAC:DATA', final_data)
        #!!!There seems to be some API changes that basically breaks their code - removing OPC for now...
        self._parent._inst.write_binary_data(':TRAC:DATA', final_data)
        #Read the response to the *OPC? query that was added to the prefix of the binary data
        #resp = self._inst.()
        #Set normal timeout
        self._parent._inst.timeout = 10000
        #Check for errors...
        self._parent._chk_err('after writing binary values to AWG waveform memory.')

        total_mkrs = np.array([])
        for mkr_ind, cur_mkr_data in enumerate(mkr_data):
            if mkr_data[mkr_ind].size == 0:
                continue
            # self._set_cmd(':MARK:SEL', mkr_ind+1)

            if self._data_type == np.uint16:
                cur_mkrs = mkr_data[mkr_ind][::2].astype(np.uint8)
            else:
                #cur_mkrs = mkr_data[mkr_ind][::4].astype(np.uint8)
                assert False, "Unsupported format! Why is it not even 16-bit anyway? Read the manual to support this format..."
            #Bit 0 for MKR1, Bit 1 for MKR2 - must perform bit-shifts if it's MKR3 or MKR4, but these outputs are not present in this module...
            if mkr_ind == 0:
                cur_mkrs *= 1
            elif mkr_ind == 1:
                cur_mkrs *= 2
            #
            if total_mkrs.size == 0:
                total_mkrs = cur_mkrs
            else:
                total_mkrs += cur_mkrs
        #
        if total_mkrs.size > 0:            
            #The arrangement four MSBs are for the even marker segments while the four LSBs are for the odd marker segments (starting the count at 1)
            total_mkrs = total_mkrs[0::2] + np.left_shift(total_mkrs[1::2], 4)
            #Increase the timeout before writing binary-data:
            self._parent._inst.timeout = 30000
            # Send the binary-data with *OPC? added to the beginning of its prefix.
            self._parent._inst.write_binary_data(':MARK:DATA', total_mkrs)
            # Read the response to the *OPC? query that was added to the prefix of the binary data
            #resp = inst.read()
            # Set normal timeout
            self._parent._inst.timeout = 10000
            self._parent._chk_err('after writing binary values to AWG marker memory.')

class TaborP2584M_ACQ(InstrumentChannel):
    def __init__(self, parent):
        super().__init__(parent, 'ACQ')
        self._parent = parent

        self.add_parameter(
            'sample_rate', label='Sample Rate', unit='Hz',
            get_cmd=partial(self._parent._get_cmd, ':DIG:FREQ?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:FREQ'),
            vals=vals.Numbers(100e6, 2.0e9),
            get_parser=float)

        self.add_parameter('trigPolarity', label='Trigger Input Polarity', 
            docstring='Polarity of the trigger input. Use with care.',
            get_cmd=partial(self._parent._get_cmd, ':DIG:TRIG:SLOP?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:TRIG:SLOP'),
            val_mapping={1: 'POS', 0: 'NEG'})

        # Setup the digitizer in two-channels mode
        self._parent._set_cmd(':DIG:MODE', 'DUAL')
        self.sample_rate(2.0e9)

        # Set Trigger level to 0.5V
        self._parent._set_cmd(':DIG:TRIG:LEV1', 0.0)

        # Enable capturing data from channel 1
        self._parent._set_cmd(':DIG:CHAN:SEL', 1)
        self._parent._set_cmd(':DIG:CHAN:STATE', 'ENAB')
        # Select the external-trigger as start-capturing trigger:
        self._parent._set_cmd(':DIG:TRIG:SOURCE', 'EXT')

        # Enable capturing data from channel 2
        self._parent._set_cmd(':DIG:CHAN:SEL', 2)
        self._parent._set_cmd(':DIG:CHAN:STATE', 'ENAB')
        # Select the external-trigger as start-capturing trigger:
        self._parent._set_cmd(':DIG:TRIG:SOURCE', 'EXT')

        self._num_samples = 4800
        self._num_segs = 4
        self._num_repetitions = 1
        self._last_mem_frames_samples = (-1,-1)

    @property
    def NumSamples(self):
        return self._num_samples
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self._num_samples = num_samples

    @property
    def SampleRate(self):
        return self.sample_rate()
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self.sample_rate(frequency_hertz)

    @property
    def NumSegments(self):
        return self._num_segs
    @NumSegments.setter
    def NumSegments(self, num_segs):
        self._num_segs = num_segs

    @property
    def NumRepetitions(self):
        return self._num_repetitions
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps):
        self._num_repetitions = num_reps

    @property
    def TriggerInputEdge(self):
        return self.trigPolarity()
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self.trigPolarity(pol)

    def _allocate_frame_memory(self):
        # Allocate four frames of 4800 samples
        cmd = ':DIG:ACQuire:FRAM:DEF {0},{1}'.format(self.NumRepetitions*self.NumSegments, self.NumSamples)
        self._parent._send_cmd(cmd)

        # Select the frames for the capturing 
        # (all the four frames in this example)
        #TODO: Optimise for repetitions!
        capture_first, capture_count = 1, self.NumRepetitions*self.NumSegments
        cmd = ":DIG:ACQuire:FRAM:CAPT {0},{1}".format(capture_first, capture_count)
        self._parent._send_cmd(cmd)

        self._last_mem_frames_samples = (self.NumRepetitions, self.NumSegments, self.NumSamples)
        self._parent._chk_err('after allocating readout ACQ memory.')

    def get_data(self):
        assert self.NumSamples % 48 == 0, "The number of samples must be divisible by 48 if in DUAL mode."

        if self._last_mem_frames_samples[0] != self.NumRepetitions or self._last_mem_frames_samples[1] != self.NumSegments or self._last_mem_frames_samples[2] != self.NumSamples:
            self._allocate_frame_memory()

        # Clean memory 
        self._parent._send_cmd(':DIG:ACQ:ZERO:ALL')

        self._parent._chk_err('after clearing memory.')

        #Fudged sleep required to keep Tabor happy?!
        time.sleep(1)

        # Stop the digitizer's capturing machine (to be on the safe side)
        self._parent._set_cmd(':DIG:INIT', 'OFF')
        # Start the digitizer's capturing machine
        self._parent._set_cmd(':DIG:INIT', 'ON')

        #Poll for status bit
        loopcount = 0
        done = 0
        while done == 0:
            resp = self._parent._get_cmd(":DIG:ACQuire:FRAM:STATus?")
            resp_items = resp.split(',')
            done = int(resp_items[1])
            #print("{0}. {1}".format(done, resp_items))
            loopcount += 1
            if loopcount == 1000:
                #print("No Trigger was detected")
                assert False, "No trigger detected during the acquisiton sniffing window."
                done = 1  

        # Stop the digitizer's capturing machine (to be on the safe side)
        self._parent._set_cmd(':DIG:INIT', 'OFF')

        self._parent._chk_err('after actual acquisition.')
        
        #May require fudge wait to keep Tabor happy
        #time.sleep(1)

        #Read all frames from Memory
        #
        #Choose which frames to read (all in this example)
        self._parent._set_cmd(':DIG:DATA:SEL', 'ALL')
        #Choose what to read (only the frame-data without the header in this example)
        self._parent._set_cmd(':DIG:DATA:TYPE', 'FRAM')
        #
        # Get the total data size (in bytes)
        resp = self._parent._get_cmd(':DIG:DATA:SIZE?')
        num_bytes = np.uint32(resp)
        #print('Total size in bytes: ' + resp)
        #
        # Read the data that was captured by channel 1:
        self._parent._set_cmd(':DIG:CHAN:SEL', 1)
        wavlen = num_bytes // 2
        wav1 = np.zeros(wavlen, dtype=np.uint16)
        rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav1, num_bytes)
        #
        # Read the data that was captured by channel 2:
        self._parent._set_cmd(':DIG:CHAN:SEL', 2)
        wavlen = num_bytes // 2
        wav2 = np.zeros(wavlen, dtype=np.uint16)
        rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav2, num_bytes)

        self._parent._chk_err('after downloading the ACQ data from the FGPA DRAM.')

        return [wav1.reshape(self.NumRepetitions, self.NumSegments, self.NumSamples), wav2.reshape(self.NumRepetitions, self.NumSegments, self.NumSamples)]


class Tabor_P2584M(Instrument):
    def __init__(self, name, pxi_chassis: int,  pxi_slot: int, **kwargs):
        super().__init__(name, **kwargs) #No address...
        #Currently Tabor doesn't seem to use pxi_chassis in their newer drivers - curious...

        # Use lib_dir_path = None 
        # for default location (C:\Windows\System32)
        # Change it only if you know what you are doing
        lib_dir_path = None
        self._admin = TepAdmin(lib_dir_path)

        self._inst = self._admin.open_instrument(slot_id=pxi_slot)
        assert self._inst != None, "Failed to load the Tabor AWG instrument - check slot ID perhaps."

        #Tabor's driver will print error messages if any are present after every command - it is an extra query, but provides security
        self._inst.default_paranoia_level = 2

        #Get HW options
        # self._inst.send_scpi_query("*OPT?")
        #Reset - must!
        self._inst.send_scpi_cmd( "*CLS")
        self._inst.send_scpi_cmd( "*RST")

        #Add the AWG and ACQ submodules to cordon off the different sub-instrument properties...
        self.add_submodule('AWG', TaborP2584M_AWG(self))    #!!!NOTE: If this name is changed from 'AWG', make sure to change it in the TaborP2584M_AWG class initializer!
        self.add_submodule('ACQ', TaborP2584M_ACQ(self))    #!!!NOTE: If this name is changed from 'ACQ', make sure to change it in the TaborP2584M_ACQ class initializer!

    def close(self):
        #Override QCoDeS function to ensure proper resource release
        #close connection
        self._inst.close_instrument()
        self._admin.close_inst_admin()
        super().close()

    def _send_cmd(self, cmd):
        self._inst.send_scpi_cmd(cmd)
    def _get_cmd(self, cmd):
        return self._inst.send_scpi_query(cmd)
    def _set_cmd(self, cmd, value):
        self._inst.send_scpi_cmd(f"{cmd} {value}")
    def _chk_err(self, msg):
        resp = self._get_cmd(':SYST:ERR?')
        resp = resp.rstrip()
        assert resp.startswith('0'), 'ERROR: "{0}" {1}.'.format(resp, msg)
