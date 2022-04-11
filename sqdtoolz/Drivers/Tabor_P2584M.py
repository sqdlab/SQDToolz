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

from copy import deepcopy

class AWG_TaborP2584M_channel(InstrumentChannel):
    """
    AWG Channel class for the Tabor Proteus RF Transceiver
    """
    def __init__(self, parent:Instrument, name:str, channel: int) -> None:
        """
        Class Constructor
        """
        super().__init__(parent, name)
        self._parent = parent
        self._channel = channel
        self._outputEnable = True
        self._amp = 1.0
        self._off = 0.0

        self.add_parameter(
            'amplitude', label='Amplitude', unit='Vpp',
            get_cmd=partial(self._get_cmd, ':SOUR:VOLT:AMPL?'),
            set_cmd=partial(self._set_cmd, ':SOUR:VOLT:AMPL'),
            vals=vals.Numbers(1e-3, 1.2),
            get_parser=lambda x : float(x),
            set_parser=lambda x: x)
        self.add_parameter(
            'offset', label='Offset', unit='V',
            get_cmd=partial(self._get_cmd, ':SOUR:VOLT:OFFS?'),
            set_cmd=partial(self._set_cmd, ':SOUR:VOLT:OFFS'),
            vals=vals.Numbers(-0.5, 0.5),
            inter_delay=0.0001,
            step=0.5,
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
        
        self.amplitude(1.2)

        #Marker parameters
        for cur_mkr in [1,2]:
            self.add_parameter(
                f'marker{cur_mkr}_output', label=f'Channel {channel} Marker {cur_mkr-1} output',
                get_cmd=partial(self._get_mkr_cmd, ':MARK?', cur_mkr),
                set_cmd=partial(self._set_mkr_cmd, ':MARK', cur_mkr),
                val_mapping={True: 'ON', False: 'OFF'})
            getattr(self, f'marker{cur_mkr}_output')(True)  #Default state is ON
            self._set_mkr_cmd(':MARK:VOLT:PTOP', cur_mkr, 1.2)

        #NOTE: Although the ramp-rate is technically software-based, there could be a source that provides actual precision rates - so it's left as a parameter in general instead of being a HAL-level feature...
        self.add_parameter('voltage_ramp_rate', unit='V/s',
                        label="Output voltage ramp-rate",
                        initial_value=2.5e-3/0.05,
                        vals=vals.Numbers(0.001, 1),
                        get_cmd=lambda : self.offset.step/self.offset.inter_delay,
                        set_cmd=self._set_ramp_rate)
        self.voltage_ramp_rate(1)


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

    @property
    def Voltage(self):
        return self.offset()
    @Voltage.setter
    def Voltage(self, val):
        self.offset(val)
        
    @property
    def RampRate(self):
        return self.voltage_ramp_rate()
    @RampRate.setter
    def RampRate(self, val):
        self.voltage_ramp_rate(val)

    def _set_ramp_rate(self, ramp_rate):
        if ramp_rate < 0.01:
            self.offset.step = 0.001
        elif ramp_rate < 0.1:
            self.offset.step = 0.010
        elif ramp_rate < 1.0:
            self.offset.step = 0.100
        else:
            self.offset.step = 1.0
        self.offset.inter_delay = self.offset.step / ramp_rate

class AWG_TaborP2584M_task:
    def __init__(self, seg_num, num_cycles, next_task_ind, trig_src='NONE'):
        self.seg_num = seg_num
        self.num_cycles = num_cycles
        self.next_task_ind = next_task_ind  #NOTE: Indexed from 1
        self.trig_src = trig_src

class TaborP2584M_AWG(InstrumentChannel):
    """
    Instrument class for the Tabor Proteus RF transceiver AWG side
    Inherits from InstrumentChannel 
    """
    def __init__(self, parent):
        super().__init__(parent, 'AWG')
        self._parent = parent

        # Reset memory in all output channels !CHECK!
        for m in range(4):
            self._parent._set_cmd(':INST:CHAN', m+1)
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
            cur_channel.marker1_output(True)
            cur_channel.marker2_output(True)
        self._used_memory_segments = [None]*2

        self._sequence_lens = [None]*4

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

    @property
    def MemoryRequirements(self):
        return {'MinSize' : 1024, 'Multiple' : 32}

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]  #!!!NOTE: Note from above in the initialiser regarding the parent storing the AWG channel submodule
        else:
            return None

    # def program_channel(self, chan_id, wfm_data, mkr_data = np.array([])):
    #     chan_ind = self._ch_list.index(chan_id)
    #     cur_chnl = self._get_channel_output(chan_id)

    #     #Condition the waveform
    #     cur_data = wfm_data
    #     cur_amp = cur_chnl.Amplitude/2
    #     cur_off = cur_chnl.Offset
    #     cur_data = (cur_data - cur_off)/cur_amp
        
    #     #So channels 1 and 2 share segment memory and channels 3 and 4 share a separate bank of segment memory
    #     #Idea is to use 1 segment for each waveform channel inside said bank...
        
    #     #Select channel
    #     self._parent._set_cmd(':INST:CHAN', chan_ind+1)
    #     #Delete and Define segment (noting that it's taken as 1 or 2 for channels 1|3 and 2|4 respectively...)
    #     seg_id = int(chan_ind % 2 + 1)
    #     self._parent._set_cmd('TRAC:DEL', seg_id)
    #     self._parent._send_cmd(f':TRAC:DEF {seg_id}, {cur_data.size}')
        
    #     # self._send_data_to_memory(seg_id, cur_data)
    #     self._send_data_to_memory(seg_id, cur_data, mkr_data)
    #     self._program_task_table(chan_ind+1, [AWG_TaborP2584M_task(seg_id, 1, 1, cur_chnl.trig_src())])
        
    #     self._parent._set_cmd('FUNC:MODE', 'TASK')

    def prepare_waveform_memory(self, chan_id, seg_lens, **kwargs):
        """
        Method to prepare waveform for Tabor memory
        @param chan_id: Id of teh channel to prepare memory for
        @param seg_lens: 
        """
        chan_ind = self._ch_list.index(chan_id)
        self._sequence_lens[chan_ind] = seg_lens
        self._banks_setup = False

    def _setup_memory_banks(self):
        """
        Method to prepare memory banks for programming
        For the Tabor, CH1 and CH2 share a memory bank
        and CH3 and CH3 share a memory bank
        """
        if self._banks_setup:
            return

        # Compute offsets of data if two channels sharing a memory banke are being used
        #I.e. store it as CH1-Data, then CH2-Data. Similarly in the other memory bank, it's CH3-Data, then CH4-Data
        if self._sequence_lens[0] != None:
            self._seg_off_ch2 = len(self._sequence_lens[0])
        else:
            self._seg_off_ch2 = 0
        if self._sequence_lens[2] != None:
            self._seg_off_ch4 = len(self._sequence_lens[2])
        else:
            self._seg_off_ch4 = 0

        #Settle Memory Bank 1 (shared among channels 1 and 2) and Memory Bank 2 (shared among channels 3 and 4)
        seg_id = 1
        reset_remaining = False
        for cur_ch_ind in range(4):
            if cur_ch_ind == 2:
                seg_id = 1      #Going to the next memory bank now...
                reset_remaining = False
            if self._sequence_lens[cur_ch_ind] != None:
                #Select current channel
                self._parent._set_cmd(':INST:CHAN', cur_ch_ind+1) #NOTE I'm assuming cur_ch_index is zero indexed adn teh command is 1 indexed, hence the +1
                for cur_len in self._sequence_lens[cur_ch_ind]:
                    self._parent._set_cmd(':TRACe:SEL', seg_id) # Select segment for clearing
                    cur_mem_len = self._parent._get_cmd(':TRAC:DEF:LENG?') # Find length of segment
                    if reset_remaining or cur_mem_len == '' or cur_len != int(cur_mem_len):
                        self._parent._set_cmd(':TRAC:DEL', seg_id) # Clear the current segment
                        reset_remaining = True #NOTE UNSURE OF THIS LOGIC
                    self._parent._send_cmd(f':TRAC:DEF {seg_id}, {cur_len}') # Specify a segment and its corresponding length
                    seg_id += 1
            self._sequence_lens[cur_ch_ind] = None

        self._banks_setup = True

    def program_channel(self, chan_id, dict_wfm_data):
        """
        Method to program channel
        @param chan_id: Id of channel to be programmed
        @param dict_wfm_data: wfm data to be programmed
        """
        chan_ind = self._ch_list.index(chan_id)
        cur_chnl = self._get_channel_output(chan_id)

        self._setup_memory_banks()
        if chan_ind == 1:
            seg_offset = self._seg_off_ch2
        elif chan_ind == 3:
            seg_offset = self._seg_off_ch4
        else:
            seg_offset = 0

        #Select channel
        self._parent._set_cmd(':INST:CHAN', chan_ind+1)

        #Program the memory banks
        for m in range(len(dict_wfm_data['waveforms'])):
            cur_data = dict_wfm_data['waveforms'][m]
            cur_amp = cur_chnl.Amplitude/2
            cur_off = cur_chnl.Offset * 0   #Don't compensate for offset...
            cur_data = (cur_data - cur_off)/cur_amp
            #TODO: Write an assert to ensure max(cur_data) < |cur_chnl.Amplitude + cur_chnl.Offset|
            self._send_data_to_memory(m+1 + seg_offset, cur_data, dict_wfm_data['markers'][m])
        #Program the task table...
        task_list = []
        for m, seg_id in enumerate(dict_wfm_data['seq_ids']):
            task_list += [AWG_TaborP2584M_task(seg_id+1 + seg_offset, 1, (m+1)+1)]
        task_list[0].trig_src = cur_chnl.trig_src()     #First task is triggered off the TRIG source
        task_list[-1].next_task_ind = 1                 #Last task maps back onto the first task
        self._program_task_table(chan_ind+1, task_list)
        
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
        self._parent._inst.timeout = 1000000
        #Send the binary-data with *OPC? added to the beginning of its prefix.
        #self._parent._inst.write_binary_data('*OPC?; :TRAC:DATA', final_data*0)
        #!!!There seems to be some API changes that basically breaks their code - removing OPC for now...
        if self._parent._debug:
            self._parent._debug_logs += 'BINARY-DATA-TRANSFER: :TRAC:DATA'
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
            if self._parent._debug:
                self._parent._debug_logs += 'BINARY-DATA-TRANSFER: :MARK:DATA'
            self._parent._inst.write_binary_data(':MARK:DATA', total_mkrs)
            # Read the response to the *OPC? query that was added to the prefix of the binary data
            #resp = inst.read()
            # Set normal timeout
            self._parent._inst.timeout = 10000
            self._parent._chk_err('after writing binary values to AWG marker memory.')

class TaborP2584M_ACQ(InstrumentChannel):
    """
    Tabor Acquisition class for Proteus RF Transceiver
    Device has 2 input channels CH1 and CH2 and either 
    digitizes in dual mode or single mode. For now, 
    this driver only operates in dual mode (separate signals on each acquistion channel)
    """
    def __init__(self, parent):
        super().__init__(parent, 'ACQ')
        self._parent = parent
        self._ch_states = [False, False] # Stores which channels are enabled.
        self._active_channel = "CH1"

        self.add_parameter(
            'activeChannel', label='Currently Selected Channel', 
            get_cmd=partial(self._parent._get_cmd, ':DIG:CHAN?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:CHAN'), 
            vals = vals.Enum(1, 2))

        # Add all channel dependent parameters
        for i in range(2) :
            self.add_parameter(
                f'channel{i + 1}State', label='Currently Selected Channel', 
                get_cmd=partial(self._chan_get_cmd, i + 1, ':DIG:CHAN:STAT?'),
                set_cmd=partial(self._chan_set_cmd, i + 1,':DIG:CHAN:STAT'),
                val_mapping = {0 : "DIS", 1 : "ENAB"})
            
            self.add_parameter(
                f'channel{i + 1}Range', label='Input Range of Acquisition Channels', unit = "mVpp",
                get_cmd=partial(self._chan_get_cmd, i + 1, ':DIG:CHAN:RANG?'),
                set_cmd=partial(self._chan_set_cmd, i + 1, ':DIG:CHAN:RANG'),
                val_mapping={250 : "LOW", 400 : "MED", 500 : "HIGH"})

            # TODO : FIGURE OUT HOW TO ADD IN TASK SELECTION HERE
            self.add_parameter(
                f'trigger{i + 1}Source', label='Source of trigger for selected channel',
                get_cmd=partial(self._chan_get_cmd, i + 1, ':DIG:TRIG:SOUR?'),
                set_cmd=partial(self._chan_set_cmd, i + 1, ':DIG:TRIG:SOUR'),
                val_mapping = {"CPU" : "CPU", "EXT" : "EXT"})

            self.add_parameter(
                f'channel{i + 1}Offset', label='Input Offset of Acquisition Channels', unit = "V",
                get_cmd=partial(self._chan_get_cmd, i + 1, ':DIG:CHAN:OFFS?'),
                set_cmd=partial(self._chan_set_cmd, i + 1, ':DIG:CHAN:OFFS'),
                vals=vals.Numbers(-2.0, 2.0))

            self.add_parameter(
                f'trigger{i + 1}Level', label='Input level required to trigger', unit = "V",
                get_cmd=partial(self._parent._get_cmd, f':DIG:TRIG:LEV{i+1}?'),
                set_cmd=partial(self._parent._set_cmd, f':DIG:TRIG:LEV{i+1}'),
                vals=vals.Numbers(-5.0, 5.0))

            

        self.add_parameter(
            'sample_rate', label='Sample Rate', unit='Hz',
            get_cmd=partial(self._parent._get_cmd, ':DIG:FREQ?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:FREQ'),
            vals=vals.Numbers(800e6, 2.7e9),
            get_parser=float)

        self.add_parameter('trigPolarity', label='Trigger Input Polarity', 
            docstring='Polarity of the trigger input. Use with care.',
            get_cmd=partial(self._parent._get_cmd, ':DIG:TRIG:SLOP?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:TRIG:SLOP'),
            val_mapping={1: 'POS', 0: 'NEG'})

        self.add_parameter(
            'blocksize', label='Blocksize',
            parameter_class=ManualParameter,
            initial_value=2**6,
            vals=vals.Numbers())

        self.add_parameter(
            'mode', label='Mode of the Digitizer',
            get_cmd=partial(self._parent._get_cmd, ':DIG:MODE?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:MODE'),
            val_mapping = {"DUAL" : "DUAL", "SING" : "SING"})
        
        self.add_parameter(
            'extTriggerType', label='type of trigger that will be derived from the external trigger of the digitizer',
            get_cmd=partial(self._parent._get_cmd, ':DIG:TRIG:TYPE?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:TRIG:TYPE'),
            val_mapping = {"EDGE" : "EDGE", "GATE" : "GATE", "WEDGE" : "WEDGE", "WGATE" : "WGATE"})

        # Setup the digitizer in two-channels mode
        #self._parent._set_cmd(':DIG:MODE', 'DUAL')
        self.mode('DUAL')
        self.sample_rate(2.0e9)

        # Set Trigger level to 0.5V
        self.trigger1Level(0.1)
        self.trigger2Level(0.1)
        #self._parent._set_cmd(':DIG:TRIG:LEV1', 0.1)
        #self._parent._set_cmd(':DIG:TRIG:LEV2', 0.1)
        
        # Set Channel range to max
        self.channel1Range(500)
        self.channel2Range(500)

        # Set Channel offset to minimum
        self.channel1Offset(0.0)
        self.channel2Offset(0.0)

        # Enable capturing data from channel 1
        self.channel1State(1)
        #self._parent._set_cmd(':DIG:CHAN:SEL', 1)
        #self._parent._set_cmd(':DIG:CHAN:STATE', 'ENAB')
        self._ch_states[0] = True

        # Select the external-trigger as start-capturing trigger:
        self.trigger1Source("EXT")
        self.trigger2Source("EXT")
        #self._parent._set_cmd(':DIG:TRIG:SOURCE', 'EXT')
        self.extTriggerType("EDGE")
        #self._parent._set_cmd(':DIG:TRIG:TYPE', 'EDGE')

        # Enable capturing data from channel 2
        self.channel2State(1)
        #self._parent._set_cmd(':DIG:CHAN:SEL', 2)
        #self._parent._set_cmd(':DIG:CHAN:STATE', 'ENAB')
        self._ch_states[1] = True

        self._dsp_channels = {"DDC1" : "OFF", "DDC2" : "OFF"}


        # Select the external-trigger as start-capturing trigger:
        self._parent._set_cmd(':DIG:TRIG:SOURCE', 'EXT')

        self._num_samples = 4800 # Number of samples per frame
        self._num_segs = 4 # Number of frames per repetition
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

    @property
    def AvailableChannels(self):
        return 2

    @property
    def ChannelStates(self):
        return self._ch_states
    @ChannelStates.setter
    def ChannelStates(self, ch_states):
        TABOR_DIG_CHANNEL_STATES = ['DIS', 'ENAB']
        assert len(ch_states) == 2, "There are 2 channel states that must be specified."
        for i, state in enumerate(ch_states):
            self._parent._set_cmd(':DIG:CHAN:SEL', i+1)
            self._parent._set_cmd(':DIG:CHAN:STATE', TABOR_DIG_CHANNEL_STATES[state])
            self._ch_states[i] = state
            #TODO: If using both channels, then ensure it does the DUAL-mode setting here!

    def _chan_get_cmd(self, ch, cmd):
        """
        Methods to manage switching to acive channel before running get command
        """
        #Perform channel-select
        self.activeChannel(ch)
        #Query command
        return self._parent._inst.send_scpi_query(cmd)

    def _chan_set_cmd(self, ch, cmd, value):
        """
        Method to manage switching to active channel before running set command
        """
        #Perform channel-select
        self.activeChannel(ch) #self._parent._inst.send_scpi_cmd(f':DIG:CHAN {self._active_channel}')
        #Perform command
        self._parent._inst.send_scpi_cmd(f'{cmd} {value}')

    def _allocate_frame_memory(self):
        """
        Method that allocates memory for digitizer (acquisition) 
        In DUAL mode the number of samples per frame should be a multiple of 48
        (96 for SINGLE mode)
        """
        # Allocate four frames of self.NumSample (defaults to 48000) 
        cmd = ':DIG:ACQuire:FRAM:DEF {0},{1}'.format(self.NumRepetitions*self.NumSegments, self.NumSamples) #NOTE Unsure as to where these members are set
        self._parent._send_cmd(cmd)

        # Select the frames for the capturing 
        # (all the four frames in this example)
        #TODO: Optimise for repetitions!
        capture_first, capture_count = 1, self.NumRepetitions*self.NumSegments
        cmd = ":DIG:ACQuire:FRAM:CAPT {0},{1}".format(capture_first, capture_count)
        self._parent._send_cmd(cmd)

        self._last_mem_frames_samples = (self.NumRepetitions, self.NumSegments, self.NumSamples)
        self._parent._chk_err('after allocating readout ACQ memory.')

    def get_frame_data(self):
        #Read all frames from Memory
        #
        #Choose which frames to read (all in this example)
        self._parent._set_cmd(':DIG:DATA:SEL', 'ALL')
        #Choose what to read (only the frame-data without the header in this example)
        self._parent._set_cmd(':DIG:DATA:TYPE', 'HEAD')
        header_size = 72
        number_of_frames = self.NumSegments*self.NumRepetitions
        num_bytes = number_of_frames * header_size

        wav2 = np.zeros(num_bytes, dtype=np.uint8)
        rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav2, num_bytes)
        self._parent._chk_err('in reading frame data.')

        #print(wav2)

        trig_loc = np.zeros(number_of_frames,np.uint32)
        I_dec= np.zeros(number_of_frames,np.int32)
        Q_dec= np.zeros(number_of_frames,np.int64)
        for i in range(number_of_frames):
            idx = i* header_size
            trigPos = wav2[idx]
            gateLen = wav2[idx+1]
            minVpp = wav2[idx+2] & 0xFFFF
            maxVpp = wav2[idx+2] & 0xFFFF0000 >> 16
            timeStamp = wav2[idx+3] + wav2[idx+4] << 32
            decisionReal =  (wav2[idx+20]) + (wav2[idx+21] <<8) + \
                            (wav2[idx+22] << 16) + (wav2[idx+23] <<24) + \
                            (wav2[idx+24] << 32) + (wav2[idx+25] <<40) + \
                            (wav2[idx+26] << 48)+ (wav2[idx+27] << 56)
            Q_dec[i]= decisionReal
            decisionIm = (wav2[idx+28]) + (wav2[idx+29] <<8) + (wav2[idx+30] << 16) + (wav2[idx+31] << 24)
            I_dec[i]= decisionIm
            outprint = 'header# {0}\n'.format(i)
            outprint += 'TriggerPos: {0}\n'.format(trigPos)
            outprint += 'GateLength: {0}\n'.format(gateLen)
            outprint += 'Min Amp: {0}\n'.format(minVpp)
            outprint += 'Max Amp: {0}\n'.format(maxVpp)
            outprint += 'Min TimeStamp: {0}\n'.format(timeStamp)
            outprint += 'Decision: {0} + j* {1}\n'.format(decisionReal,decisionIm)
            print(outprint)
            
        dec_vals = Q_dec + 1j*I_dec #No idea about the inversion...
        return dec_vals

    def process_block(self, block_idx, cur_processor, blocksize):
        if block_idx == 0:
            #Choose what to read (only the frame-data without the header in this example)
            self._parent._set_cmd(':DIG:DATA:TYPE', 'FRAM')
            #Choose which frames to read (all in this example)
            self._parent._set_cmd(':DIG:DATA:SEL', 'FRAM')
            

            self._parent._set_cmd(':DIG:DATA:FRAM', f'{1},{blocksize*self.NumSegments}')
            #
            # Get the total data size (in bytes)
            resp = self._parent._get_cmd(':DIG:DATA:SIZE?')
            # self.num_bytes = 4176*np.uint64(resp)
            # self.num_bytes = np.uint64(resp)
            # print(resp, self.num_bytes, 'hi', self._parent._get_cmd(':DIG:DATA:FRAM?'))

            # wavlen = int(self.num_bytes // 2)
            wavlen = int(blocksize*self.NumSegments*self.NumSamples)
            # print(self.num_bytes)
            wav1 = np.zeros(wavlen, dtype=np.uint16)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
            wav1 = wav1.reshape(blocksize, self.NumSegments, self.NumSamples)
            wav2 = np.zeros(wavlen, dtype=np.uint16)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
            wav2 = wav2.reshape(blocksize, self.NumSegments, self.NumSamples)
            self.wav1 = wav1
            self.wav2 = wav2

        resp = self._parent._get_cmd(':DIG:DATA:SIZE?')
        num_bytes = np.uint64(resp)

        # Select the frames to read
        self._parent._set_cmd(':DIG:DATA:FRAM', f'{1+block_idx*blocksize},{blocksize}')
        # Read from channel 1
        self._parent._set_cmd(':DIG:CHAN:SEL', 1)
        rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', self.wav1, num_bytes)
        # read from channel 2
        self._parent._set_cmd(':DIG:CHAN:SEL', 2)
        rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', self.wav2, num_bytes)
        # Check errors
        self._parent._chk_err('after downloading the ACQ data from the FGPA DRAM.')

        #TODO: Write some blocked caching code here (like with the M4i)...
        ret_val = {
                    'parameters' : ['repetition', 'segment', 'sample'],
                    'data' : {
                                'ch1' : self.wav1.astype(np.int32),
                                'ch2' : self.wav2.astype(np.int32),
                                },
                    'misc' : {'SampleRates' : [self.SampleRate]*2}  #NOTE!!! DIVIDE SAMPLERATE BY /16 IF USING DECIMATION STAGES!
                }
        cur_processor.push_data(ret_val)

    
    def setup_filter(self, filter_file, **kwargs) :
        """
        Method to initialise filter on Tabor
        """
        # Select to store the DSP1 data
        inst.send_scpi_cmd(':DSP:STOR1 DSP1')
        resp = inst.send_scpi_query(':SYST:ERR?')
        print(resp)

        # dsp decision frame
        inst.send_scpi_cmd(':DSP:DEC:FRAM {0}'.format(DSP_DEC_LEN))
        resp = inst.send_scpi_query(':SYST:ERR?')
        print(resp)

        # DSP1 IQ demodulation kernel data
        KL = 10240
        COE_FILE = filter_file
        ki,kq = iq_kernel(fs=DIG_SCLK,flo=DDC_NCO,kl=KL,coe_file_path=COE_FILE)
        mem = pack_kernel_data(ki,kq)

        inst.send_scpi_cmd(':DSP:IQD:SEL IQ4')           # DBUG | IQ4 | IQ5 | IQ6 | IQ7
        inst.write_binary_data(':DSP:IQD:KER:DATA', mem)
        resp = inst.send_scpi_query(':SYST:ERR?')
        print(resp)

        #define decision DSP1 path SVM
        inst.send_scpi_cmd(':DSP:DEC:IQP:SEL DSP1')
        inst.send_scpi_cmd(':DSP:DEC:IQP:OUTP SVM')
        inst.send_scpi_cmd(':DSP:DEC:IQP:LINE 1,-0.625,-5')
        inst.send_scpi_cmd(':DSP:DEC:IQP:LINE 2,1.0125,0.5')
        inst.send_scpi_cmd(':DSP:DEC:IQP:LINE 3,0,0')

    def get_data(self, **kwargs):
        self.blocksize(self.NumRepetitions)
        #TODO:
        #Currently:
        #  - It starts reading. Once a block-size B has been read, it stops checking
        #  - Then it reads B frames and processes them. However, it does not process the case where Reps = q*B + r with r=/=0
        #  - Also, it SHOULD CHECK whether the Tabor has indeed captured m*B frames when processing block m. It assumes that the processing overhead
        #    exceeds the capture time - MAKE SURE TO IMPLEMENT THIS. For now, the hack is to set B = R
        # question is just in the above, it says it reads a block size B, then reads B frames, just a bit confused by terminology, as a thought there would be a certain
        # number of frames within a block?
        #Tentative yes. The processing mostly operates on repetitions. So you usually feed the processor full repetitions 
        # So basically a Repetition is a collection of segemtns and samples. You opt to measure a total of Reps repetitions. RN wanted to take it in blocks
        # of B repetitions to then process - except he didn't check all edge cases and forgot about what is highlighted above...
        # I think the idea is that you want to choose B optimally such that it doesn't use up too much RAM and processes everything in a timely manner...
        """
        Acquisitions are defined in terms of sampling rate, record length (number of samples to be 
        captured for each trigger event), and position (the location of the closest sample to the trigger 
        event). Multiple frame acquisitions (or Multi-Frame) require the definition of the number of 
        frames to be captured.
        """
        blocksize = min(self.blocksize(), self.NumRepetitions)

        assert self.NumSamples % 48 == 0, "The number of samples must be divisible by 48 if in DUAL mode."

        cur_processor = kwargs.get('data_processor', None)
        # print(cur_processor)

        if self._last_mem_frames_samples[0] != self.NumRepetitions or self._last_mem_frames_samples[1] != self.NumSegments or self._last_mem_frames_samples[2] != self.NumSamples:
            self._allocate_frame_memory()

        # Clean memory 
        self._parent._send_cmd(':DIG:ACQ:ZERO:ALL')

        self._parent._chk_err('after clearing memory.')

        self._parent._chk_err('before')
        self._parent._set_cmd(':DIG:INIT', 'ON')
        self._parent._chk_err('dig:on')
        
        #Poll for status bit
        loopcount = 0
        captured_frame_count = 0
        while captured_frame_count < blocksize:
            resp = self._parent._get_cmd(":DIG:ACQuire:FRAM:STATus?")
            resp_items = resp.split(',')
            captured_frame_count = int(resp_items[3])
            done = int(resp_items[1])
            #print("{0}. {1}".format(done, resp_items))
            loopcount += 1
            if loopcount > 100000 and captured_frame_count == 0:    #As in nothing captured over 1000 check-loops...
                #print("No Trigger was detected")
                assert False, "No trigger detected during the acquisiton sniffing window."
                done = 1

        if cur_processor:
            self.process_block(0, cur_processor, blocksize)
            block_idx = 1
            while block_idx*blocksize < self.NumRepetitions*self.NumSegments:
                self.process_block(block_idx, cur_processor, blocksize)
                block_idx += 1
            return cur_processor.get_all_data()
        else:
            done = 0
            while not done:
                done = int(self._parent._get_cmd(":DIG:ACQuire:FRAM:STATus?").split(',')[3])
            # Stop the digitizer's capturing machine (to be on the safe side)
            self._parent._set_cmd(':DIG:INIT', 'OFF')

            self._parent._chk_err('after actual acquisition.')
            #Choose which frames to read (all in this example)
            self._parent._set_cmd(':DIG:DATA:SEL', 'ALL')
            #Choose what to read (only the frame-data without the header in this example)
            self._parent._set_cmd(':DIG:DATA:TYPE', 'FRAM')
            
            # Get the total data size (in bytes)
            resp = self._parent._get_cmd(':DIG:DATA:SIZE?')
            num_bytes = np.uint64(resp)
            print(num_bytes, 'hi', self._parent._get_cmd(':DIG:DATA:FRAM?'))

            wavlen = int(num_bytes // 2)
            wav1 = np.zeros(wavlen, dtype=np.uint16)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
            wav1 = wav1.reshape(self.NumRepetitions, self.NumSegments, self.NumSamples)
            wav2 = np.zeros(wavlen, dtype=np.uint16)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
            wav2 = wav2.reshape(self.NumRepetitions, self.NumSegments, self.NumSamples)

            # Read from channel 1
            self._parent._set_cmd(':DIG:CHAN:SEL', 1)
            rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav1, num_bytes)
            # read from channel 2
            self._parent._set_cmd(':DIG:CHAN:SEL', 2)
            rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav2, num_bytes)
            # Check errors
            self._parent._chk_err('after downloading the ACQ data from the FGPA DRAM.')

            #TODO: Write some blocked caching code here (like with the M4i)...
            ret_val = {
                        'parameters' : ['repetition', 'segment', 'sample'],
                        'data' : {
                                    'ch1' : wav1.astype(np.int32),
                                    'ch2' : wav2.astype(np.int32),
                                    },
                        'misc' : {'SampleRates' : [self.SampleRate]*2}
                    }
            return ret_val

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

        #ENSURE THAT THE REF-IN IS CONNECTED TO Rb Oven if using EXT 10MHz source!
        self.add_parameter(
            'ref_osc_src', label='Reference Oscillator Source',
            get_cmd=partial(self._get_cmd, ':ROSC:SOUR?'),
            set_cmd=partial(self._set_cmd, ':ROSC:SOUR'),
            val_mapping={'INT': 'INT', 'EXT': 'EXT'}
            )
        self.add_parameter(
            'ref_osc_freq', label='Reference Oscillator Frequency', unit='Hz',
            get_cmd=partial(self._get_cmd, ':ROSC:FREQ?'),
            set_cmd=partial(self._set_cmd, ':ROSC:FREQ'),
            val_mapping={10e6: '10M', 100e6: '100M'}
            )

        self._debug_logs = ''
        self._debug = True

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
        if self._debug:
            self._debug_logs += cmd + '\n'
        return self._inst.send_scpi_query(cmd)
    def _set_cmd(self, cmd, value):
        if self._debug:
            self._debug_logs += f"{cmd} {value}\n"
        self._inst.send_scpi_cmd(f"{cmd} {value}")
    
    def _chk_err(self, msg):
        resp = self._get_cmd(':SYST:ERR?')
        resp = resp.rstrip()
        assert resp.startswith('0'), 'ERROR: "{0}" {1}.'.format(resp, msg)

