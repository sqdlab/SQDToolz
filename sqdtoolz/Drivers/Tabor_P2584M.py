import os
import sys
from sqdtoolz.Drivers.Dependencies.teproteus import TEProteusAdmin as TepAdmin
from sqdtoolz.Drivers.Dependencies.teproteus import TEProteusInst as TepInst
from sqdtoolz.HAL.Processors.ProcessorFPGA import ProcessorFPGA
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDCFIR import FPGA_DDCFIR
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDC import FPGA_DDC
from sqdtoolz.HAL.Processors.FPGA.FPGA_Integrate import FPGA_Integrate
from sqdtoolz.HAL.Processors.FPGA.FPGA_Decimation import FPGA_Decimation
from sqdtoolz.HAL.Processors.FPGA.FPGA_FFT import FPGA_FFT

import numpy as np
import math
import time

from qcodes import Instrument, InstrumentChannel, validators as vals
from qcodes.instrument.parameter import ManualParameter

import numpy as np
from functools import partial

from copy import deepcopy
import scipy.signal
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
            #TODO: Maybe parametrise this? But it will be set to maximum range for now...  
            self._set_mkr_cmd(':MARKer:VOLTage:OFFSet', cur_mkr, 0.0)
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
        self._parent.parent._send_cmd(f':INST:CHAN {self._channel}')
        #Query command
        return self._parent.parent._inst.send_scpi_query(cmd)

    def _set_cmd(self, cmd, value):
        #Perform channel-select
        self._parent.parent._send_cmd(f':INST:CHAN {self._channel}')
        #Perform command
        self._parent.parent._send_cmd(f'{cmd} {value}')

    def _get_mkr_cmd(self, cmd, mkr_num):
        #Perform channel-select
        self._parent.parent._send_cmd(f':INST:CHAN {self._channel}')
        #Perform marker-select
        self._parent.parent._send_cmd(f':MARK:SEL {mkr_num}')
        #Perform command
        return self._parent.parent._inst.send_scpi_query(cmd)

    def _set_mkr_cmd(self, cmd, mkr_num, value):
        #Perform channel-select
        self._parent.parent._send_cmd(f':INST:CHAN {self._channel}')
        #Perform marker-select
        self._parent.parent._send_cmd(f':MARK:SEL {mkr_num}')
        #Perform command
        self._parent.parent._send_cmd(f'{cmd} {value}')


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
    def __init__(self, seg_num, num_cycles, next_task_ind, trig_src='NONE', trig_adc=False):
        self.seg_num = seg_num
        self.num_cycles = num_cycles
        self.next_task_ind = next_task_ind  #NOTE: Indexed from 1
        self.trig_src = trig_src
        self.trig_adc = trig_adc

class TaborP2584M_AWG(InstrumentChannel):
    """
    Instrument class for the Tabor Proteus RF transceiver AWG side
    Inherits from InstrumentChannel 
    """
    def __init__(self, parent):
        super().__init__(parent, 'AWG')
        self._parent = parent

        self.add_parameter(
            'activeChannel', label='Currently Selected Channel', 
            get_cmd=partial(self._parent._get_cmd, ':INST:CHAN?'),
            set_cmd=partial(self._parent._set_cmd, ':INST:CHAN'), 
            vals = vals.Enum(1, 2, 3, 4))

        self.add_parameter(
            'sample_rate', label='Sample Rate', unit='Hz',
            get_cmd=partial(self._parent._get_cmd, ':SOUR:FREQ:RAST?'),
            set_cmd=partial(self._parent._set_cmd, ':SOUR:FREQ:RAST'),
            vals=vals.Numbers(1e9, 9e9),    #Note that this is a cheat using Nyquist trickery...
            get_parser=float)

        # Reset memory in all output channels !CHECK!
        for m in range(4):
            self.activeChannel(m + 1)
            #self._parent._set_cmd(':INST:CHAN', m+1)
            self._parent._send_cmd(':TRAC:DEL:ALL')      
            self._parent._send_cmd(':TASK:ZERO:ALL')       #Does this need to be run per channel?!

        #Get the DAC mode (8 bits or 16 bits)
        dac_mode = self._parent._get_cmd(':SYST:INF:DAC?')
        if dac_mode == 'M0' :
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
        self._cur_internal_trigs = [False]*4

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
        return 3

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

    def prepare_waveform_memory(self, chan_id, seg_lens, **kwargs):
        """
        Method to prepare waveform for Tabor memory
        @param chan_id: Id of the channel to prepare memory for
        @param seg_lens: length of segments to program
        """
        chan_ind = self._ch_list.index(chan_id)
        self._sequence_lens[chan_ind] = seg_lens
        dict_wfm_data = kwargs['raw_data']
        if dict_wfm_data['markers'][0][2].size > 0:
            assert len(dict_wfm_data['seq_ids']) == 1, "Currently internal triggers are only supported for non-compression mode."   #TODO: Fix this...
            #Build the task list as per the ADC triggers...
            int_mkrs = dict_wfm_data['markers'][0][2].astype(np.int8)
            diffs = np.concatenate([[int_mkrs[0]-int_mkrs[-1]], int_mkrs[1:]-int_mkrs[:-1]])
            if self._parent.ACQ.TriggerInputEdge == 1:
                edges = np.where(diffs==1)[0]
            else:
                edges = np.where(diffs==-1)[0]
            if edges[0] != 0:
                edges = np.concatenate([[0], edges])
            if edges[-1] != edges.size-1:
                edges = np.concatenate([edges, [dict_wfm_data['markers'][0][2].size]])
            self._sequence_lens[chan_ind] = np.diff(edges).tolist()
            self._cur_internal_trigs[chan_ind] = True
        else:
            self._cur_internal_trigs[chan_ind] = False
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
        # I.e. store it as CH1-Data, then CH2-Data. Similarly in the other memory bank, it's CH3-Data, then CH4-Data
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
        done_reset_remaining = False
        for cur_ch_ind in range(4):
            if cur_ch_ind == 2:
                seg_id = 1      #Going to the next memory bank now...
                reset_remaining = False
                done_reset_remaining = False
            if self._sequence_lens[cur_ch_ind] != None:
                #Select current channel
                self._parent._set_cmd(':INST:CHAN', cur_ch_ind+1) #NOTE I'm assuming cur_ch_index is zero indexed adn the command is 1 indexed, hence the +1
                for m, cur_len in enumerate(self._sequence_lens[cur_ch_ind]):
                    assert cur_len >= 1024, f"The partitions created for the internal marker have made segments (segment index {m} in this case) that are less than 1024 samples in size."
                    assert cur_len % 32 == 0, f"The partitions created for the internal marker have made segments (segment index {m} in this case) that are not divisible by 32 samples."
                    self._parent._set_cmd(':TRACe:SEL', seg_id) # Select segment for clearing
                    cur_mem_len = self._parent._get_cmd(':TRAC:DEF:LENG?') # Find length of segment
                    if reset_remaining or cur_mem_len == '' or cur_len != int(cur_mem_len):
                        if not done_reset_remaining:
                            self._parent._send_cmd(':TRAC:DEL:ALL') # Clear the current segment
                        done_reset_remaining = True
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

        # Setup segment offsets
        if chan_ind == 1:
            seg_offset = self._seg_off_ch2
        elif chan_ind == 3:
            seg_offset = self._seg_off_ch4
        else:
            seg_offset = 0

        #Select channel
        self._parent._set_cmd(':INST:CHAN', chan_ind+1)

        #Split the waveform into task segments if there are internally triggered markers...
        if dict_wfm_data['markers'][0][2].size > 0:
            assert np.abs(self.SampleRate / self._parent.ACQ.SampleRate - 0.8) < 1e-5, "AWG sample rate must be 80% the ACQ sample rate when using internal trigger."
            assert len(dict_wfm_data['seq_ids']) == 1, "Currently internal triggers are only supported for non-compression mode."   #TODO: Fix this...
            #Build the task list as per the ADC triggers...
            int_mkrs = dict_wfm_data['markers'][0][2].astype(np.int8)
            diffs = np.concatenate([[int_mkrs[0]-int_mkrs[-1]], int_mkrs[1:]-int_mkrs[:-1]])
            if self._parent.ACQ.TriggerInputEdge == 1:
                edges = np.where(diffs==1)[0]
            else:
                edges = np.where(diffs==-1)[0]
            #Split waveforms based on internal trigger edges
            dict_wfm_data['waveforms'] = [x for x in np.split(dict_wfm_data['waveforms'][0], edges) if x.size > 0]
            #Split all markers based on internal trigger edges
            if dict_wfm_data['markers'][0][0].size > 0:
                mkr1 = [x for x in np.split(dict_wfm_data['markers'][0][0], edges) if x.size > 0]
            else:
                mkr1 = [np.array([]) for x in range(len(dict_wfm_data['waveforms']))]
            if dict_wfm_data['markers'][0][1].size > 0:
                mkr2 = [x for x in np.split(dict_wfm_data['markers'][0][1], edges) if x.size > 0]
            else:
                mkr2 = [np.array([]) for x in range(len(dict_wfm_data['waveforms']))]
            mkrInt = [x for x in np.split(dict_wfm_data['markers'][0][2], edges) if x.size > 0]
            dict_wfm_data['markers'] = [[mkr1[x], mkr2[x], mkrInt[x]] for x in range(len(dict_wfm_data['waveforms']))]
            #Create task table
            task_list = []
            cur_ind = 0
            for seg_id in range(len(dict_wfm_data['waveforms'])):
                task_list += [AWG_TaborP2584M_task(seg_id+1 + seg_offset, 1, (seg_id+1)+1, trig_adc=cur_ind in edges)]
                cur_ind += dict_wfm_data['waveforms'][seg_id].size
            task_list[0].trig_src = cur_chnl.trig_src()     #First task is triggered off the TRIG source
            task_list[-1].next_task_ind = 1                 #Last task maps back onto the first task
            self._parent.ACQ.trigger1Source(f'TASK{chan_ind+1}')
            self._parent.ACQ.trigger2Source(f'TASK{chan_ind+1}')
            # Set Trigger AWG delay to 0 - ?????
            self._parent._send_cmd(':DIG:TRIG:AWG:TDEL {0}'.format(4e-9))
        else:
            self._parent.ACQ.trigger1Source('EXT')
            self._parent.ACQ.trigger2Source('EXT')
            task_list = []
            for m, seg_id in enumerate(dict_wfm_data['seq_ids']):
                task_list += [AWG_TaborP2584M_task(seg_id+1 + seg_offset, 1, (m+1)+1)]
            task_list[0].trig_src = cur_chnl.trig_src()     #First task is triggered off the TRIG source
            task_list[-1].next_task_ind = 1                 #Last task maps back onto the first task

        #Program the memory banks
        for m in range(len(dict_wfm_data['waveforms'])):
            cur_data = dict_wfm_data['waveforms'][m]
            cur_amp = cur_chnl.Amplitude/2
            cur_off = cur_chnl.Offset   #Don't compensate for offset... # NOTE: this used to be multiplied by 0
            cur_data = (cur_data - cur_off)/cur_amp
            assert (max(cur_data) < np.abs(cur_chnl.Amplitude + cur_chnl.Offset)), "The Amplitude and Offset are too large, output will be saturated"
            self._send_data_to_memory(m+1 + seg_offset, cur_data, dict_wfm_data['markers'][m])
        #Program the task table...            
        self._program_task_table(chan_ind+1, task_list)
        
        self._parent._set_cmd('FUNC:MODE', 'TASK')
        # Ensure all previous commands have been executed
        while not self._parent._get_cmd('*OPC?'):
            pass

    def _program_task_table(self, channel_index, tasks):
        #Select current channel
        self._parent._set_cmd(':INST:CHAN', channel_index)
        #Allocate a set number of rows for the task table
        assert len(tasks) < 64*10e3, "The maximum amount of tasks that can be programmed is 64K"
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
            if cur_task.trig_adc:
                self._parent._set_cmd(':TASK:COMP:DTRigger', 'ON')
            self._parent._set_cmd(':TASK:COMP:NEXT1', cur_task.next_task_ind)
            self._parent._set_cmd(':TASK:COMP:ENAB', cur_task.trig_src)
      
        #Download task table to channel
        self._parent._send_cmd(':TASK:COMP:DTR 1')
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
        for mkr_ind, cur_mkr_data in enumerate(mkr_data[:2]):   #3rd marker is internal
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
                val_mapping = {"CPU" : "CPU", "EXT" : "EXT", "CH1" : "CH1", "CH2" : "CH2", "TASK1" : "TASK1"},
                initial_value = "EXT")

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
            'acq_mode', label='Mode of the Digitizer',
            get_cmd=partial(self._parent._get_cmd, ':DIG:MODE?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:MODE'),
            val_mapping = {"DUAL" : "DUAL", "SING" : "SING"})

        self.add_parameter(
            'ddc_mode', label='DDC Mode of the Digitizer',
            get_cmd=partial(self._parent._get_cmd, ':DIG:DDC:MODE?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:DDC:MODE'),
            val_mapping = {"REAL" : "REAL", "COMP" : "COMP", "COMPlex" : "COMP", "N/A" : "N/A"},
            initial_value = "REAL")

        self.add_parameter(
            'fft_input', label='FFT input in the DSP chain',
            get_cmd=partial(self._parent._get_cmd, ':DSP:FFT:INPut?'),
            set_cmd=partial(self._parent._set_cmd, ':DSP:FFT:INPut'),
            val_mapping = {"IQ1" : "IQ1", "COMP" : "COMP", "DBUG" : "DBUG", "DSP1" : "DSP1", "DEBUG" : "DEBUG"}, #TODO: Check again after firmware update
            initial_value = "DBUG")

        self.add_parameter(
            'ddr_store', label='Data path to be stored in DDR1',
            get_cmd=lambda : self._parent._get_cmd(':DSP:STOR?').split(',')[0],
            set_cmd=partial(self._parent._set_cmd, ':DSP:STOR'),
            val_mapping = {"DIR" : "DIR", "DSP":"DSP", "FFT":"FFT"},
            initial_value = "DIR")

        self.add_parameter(
            'iq_demod', label='Select IQ demodulation block to configure (REAL mode)',
            get_cmd=partial(self._parent._get_cmd, ':DSP:IQD:SEL?'),
            set_cmd=partial(self._parent._set_cmd, ':DSP:IQD:SEL'),
            val_mapping = {"DBUG":"DBUG", "IQ4":"IQ4", "IQ5":"IQ5", "IQ6":"IQ6",\
                "IQ7":"IQ7", "IQ8":"IQ8", "IQ9":"IQ9", "IQ10":"IQ10", "IQ11":"IQ11",\
                "IQ12":"IQ12", "IQ13":"IQ13"})

        self.add_parameter(
            f'averageEnable', label=f'Enable Averages',
            get_cmd=partial(self._parent._get_cmd, ':DIG:ACQuire:AVERage:STAT?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:ACQuire:AVERage:STAT'),
            val_mapping={True: 'ON', False: 'OFF'})

        self.add_parameter(
            f'ddcBindChannels', label=f'Whether all DDCs are fed from CH1',
            get_cmd=partial(self._parent._get_cmd, ':DIG:DDC:BIND?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:DDC:BIND'),
            val_mapping={True: 'ON', False: 'OFF'})

        """
        self.add_parameter(
            'iq_path', label='Select IQ input path to configure',
            get_cmd=partial(self._parent._get_cmd, ':DSP:IQP:SEL?'),
            set_cmd=partial(self._parent._set_cmd, ':DSP:IQP:SEL'),
            val_mapping = {"DSP1":"DSP1", "DSP2":"DSP2", "DSP3":"DSP3", "DSP4":"DSP4"},
            initial_value = "DSP1")
        """

        self.add_parameter(
            'fir_block', label='Select FIR block to configure',
            get_cmd=partial(self._parent._get_cmd, ':DSP:FIR:SEL?'),
            set_cmd=partial(self._parent._set_cmd, ':DSP:FIR:SEL'),
            val_mapping = {"I1":"I1", "Q1":"Q1", "I2":"I2", "Q2":"Q2", \
                "DBUGI":"DBUGI", "DBUGQ":"DBUGQ"})

        self.add_parameter(
            'extTriggerType', label='type of trigger that will be derived from the external trigger of the digitizer',
            get_cmd=partial(self._parent._get_cmd, ':DIG:TRIG:TYPE?'),
            set_cmd=partial(self._parent._set_cmd, ':DIG:TRIG:TYPE'),
            val_mapping = {"EDGE" : "EDGE", "GATE" : "GATE", "WEDGE" : "WEDGE", "WGATE" : "WGATE"})

        # Setup the digitizer in two-channels mode
        self.acq_mode('DUAL')
        self.sample_rate(2.0e9)

        # Set Trigger level to 0.5V
        self.trigger1Level(0.1)
        self.trigger2Level(0.1)
        
        # Set Channel range to max
        self.channel1Range(500)
        self.channel2Range(500)

        # Set Channel offset to minimum
        self.channel1Offset(0.0)
        self.channel2Offset(0.0)

        # Enable capturing data from channel 1
        self.channel1State(1)
        self._ch_states[0] = True

        # Enable capturing data from channel 2
        self.channel2State(1)
        self._ch_states[1] = True

        # Select the external-trigger as start-capturing trigger:
        self.trigger1Source("EXT")
        self.trigger2Source("EXT")
        # self.trigger1Source("TASK1")
        # self.trigger2Source("TASK1")
        self.extTriggerType("EDGE")
        self.acq_mode("DUAL")
        self.ddc_mode("REAL")
        self.ddr_store("DIR")
        self._dsp_channels = {"DDC1" : "OFF", "DDC2" : "OFF"}


        self._num_samples = 4800 # Number of samples per frame
        self._num_segs = 4 # Number of frames per repetition
        self._num_repetitions = 1 
        self._last_mem_frames_segs_samples_avg = (-1,-1,-1, False)
        #
        self._last_dsp_state = {}
        self._last_dsp_order = None

        self._dsp_kernel_coefs = [None]*10

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
            if (self.ChannelStates[0] and self.ChannelStates[1]) :
                # If using both channels, then ensure it does the DUAL-mode setting here!
                self.acq_mode("DUAL")

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
        self.activeChannel(ch) #self._parent._send_cmd(f':DIG:CHAN {self._active_channel}')
        #Perform command
        self._parent._send_cmd(f'{cmd} {value}')



    def _allocate_frame_memory(self, final_dsp_order):
        """
        Method that allocates memory for digitizer (acquisition) 
        In DUAL mode the number of samples per frame should be a multiple of 48
        (96 for SINGLE mode)
        """
        num_frames = self.NumRepetitions*self.NumSegments
        if final_dsp_order['avRepetitions']:
            num_frames = 1
        num_samples = self.NumSamples
        if final_dsp_order['dsp_active']:
            num_samples = int(self.NumSamples*12/10)

        if self._last_mem_frames_segs_samples_avg[0] == self.NumRepetitions and self._last_mem_frames_segs_samples_avg[1] == self.NumSegments and self._last_mem_frames_segs_samples_avg[2] == num_samples and self._last_mem_frames_segs_samples_avg[3] == final_dsp_order['avRepetitions']:
            return

        if not final_dsp_order['dsp_active']:
            if (self.acq_mode() == "DUAL") :
                assert (num_samples % 48) == 0, \
                    "In DUAL mode, number of samples must be an integer multiple of 48"
            else :
                assert (num_samples % 96) == 0, \
                    "In SINGLE mode, number of samples must be an integer multiple of 96"
        #Allocate four frames of self.NumSample (defaults to 48000) 
        cmd = ':DIG:ACQuire:FRAM:DEF {0},{1}'.format(num_frames, num_samples)
        self._parent._send_cmd(cmd)

        #Select the frames for the capturing
        capture_first, capture_count = 1, num_frames
        cmd = ":DIG:ACQuire:FRAM:CAPT {0},{1}".format(capture_first, capture_count)
        self._parent._send_cmd(cmd)

        self._last_mem_frames_segs_samples_avg = (self.NumRepetitions, self.NumSegments, num_samples, final_dsp_order['avRepetitions'])
        self._parent._chk_err('after allocating readout ACQ memory.')

    def set_svm(self) :
        # inst.send_scpi_cmd(':DSP:DEC:IQP:SEL DSP1')
        # inst.send_scpi_cmd(':DSP:DEC:IQP:OUTP SVM')
        # inst.send_scpi_cmd(':DSP:DEC:IQP:LINE 1,-0.625,-5')
        # inst.send_scpi_cmd(':DSP:DEC:IQP:LINE 2,1.0125,0.5')
        # inst.send_scpi_cmd(':DSP:DEC:IQP:LINE 3,0,0')
        Frame_len = 960
        DSP_DEC_LEN = Frame_len / 2 - 10

        self._parent._set_cmd(':DSP:STOR1', 'DSP1')
        self._parent._set_cmd(f':DSP:DEC:FRAM', f'{DSP_DEC_LEN}')
        
        # % DSP1 IQ demodulation kernel data
        # COE_FILE = 'sfir_51_tap.csv';
        # [ki,kq] = pfunc.iq_kernel(DIG_SCLK,DDC_NCO,COE_FILE);
        # mem = pfunc.pack_kernel_data(ki,kq,true);
        # mem = uint32(mem);
        # mem = typecast(mem, 'uint8');
        self._parent._set_cmd(':DSP:IQD:SEL', 'IQ4')
        self._parent._set_cmd(':DSP:DEC:IQP:SEL', 'DSP1')
        
        #res = inst.WriteBinaryData(':DSP:IQD:KER:DATA ', mem)
        self._parent._set_cmd(':DSP:DEC:IQP:SEL', 'DSP1')
        self._parent._set_cmd(':DSP:DEC:IQP:OUTP', 'SVM')
        #self._parent._set_cmd(':DSP:DEC:MAPP', '1,DEC1')  
        # Line, Slope, Intercept
        self._parent._set_cmd(':DSP:DEC:IQP:LINE', '1,0,0')
        self._parent._set_cmd(':DSP:DEC:IQP:LINE', '2,1,0')
        self._parent._set_cmd(':DSP:DEC:IQP:LINE', '3,-1,0')

    def _get_captured_header(self, N=1,buf=[]):
        header_size=72
        number_of_frames = N
        num_bytes = number_of_frames * header_size
        Proteus_header = []

        # create sets of header classes
        for i in range(number_of_frames):
            Proteus_header.append({})

        for i in range(number_of_frames):
            idx = i* header_size
            Proteus_header[i]['TriggerPos'] = buf[idx+0]*(1 << 0) + buf[idx+1]*(1 << 8) + buf[idx+2]*(1 << 16) + buf[idx+3]*(1 << 24)
            Proteus_header[i]['GateLength'] = buf[idx+4]*(1 << 0) + buf[idx+5]*(1 << 8) + buf[idx+6]*(1 << 16) + buf[idx+7]*(1 << 24)
            Proteus_header[i]['minVpp']     = buf[idx+8]*(1 << 0) + buf[idx+9]*(1 << 8)
            Proteus_header[i]['maxVpp']     = buf[idx+10]*(1 << 0) + buf[idx+11]*(1 << 8)
            
            timeStamp1 = buf[idx+12]*(1 << 0)
            timeStamp2 = buf[idx+13]*(1 << 8)  
            timeStamp3 = buf[idx+14]*(1 << 16) 
            timeStamp4 = buf[idx+15]*(1 << 32) / 256
            timeStamp5 = buf[idx+16]*(1 << 32) 
            timeStamp6 = buf[idx+17]*(1 << 40) 
            timeStamp7 = buf[idx+18]*(1 << 48) 
            timeStamp8 = buf[idx+19]*(1 << 56)

            Proteus_header[i]['TimeStamp'] = timeStamp1 + timeStamp2 + timeStamp3 + timeStamp4 + timeStamp5 + timeStamp6 + timeStamp7 + timeStamp8
            
            decisionRe1 = buf[idx+20]*(1 << 0) + buf[idx+21]*(1 << 8) + buf[idx+22]*(1 << 16) + buf[idx+23]*(1 << 24)
            decisionIm1 = buf[idx+24]*(1 << 0) + buf[idx+25]*(1 << 8) + buf[idx+26]*(1 << 16) + buf[idx+27]*(1 << 24)
            decisionRe2 = buf[idx+28]*(1 << 0) + buf[idx+29]*(1 << 8) + buf[idx+30]*(1 << 16) + buf[idx+31]*(1 << 24)
            decisionIm2 = buf[idx+32]*(1 << 0) + buf[idx+33]*(1 << 8) + buf[idx+34]*(1 << 16) + buf[idx+35]*(1 << 24)
            decisionRe3 = buf[idx+36]*(1 << 0) + buf[idx+37]*(1 << 8) + buf[idx+38]*(1 << 16) + buf[idx+39]*(1 << 24)
            decisionIm3 = buf[idx+40]*(1 << 0) + buf[idx+41]*(1 << 8) + buf[idx+42]*(1 << 16) + buf[idx+43]*(1 << 24)
            decisionRe4 = buf[idx+44]*(1 << 0) + buf[idx+45]*(1 << 8) + buf[idx+46]*(1 << 16) + buf[idx+47]*(1 << 24)
            decisionIm4 = buf[idx+48]*(1 << 0) + buf[idx+49]*(1 << 8) + buf[idx+50]*(1 << 16) + buf[idx+51]*(1 << 24)
            decisionRe5 = buf[idx+52]*(1 << 0) + buf[idx+53]*(1 << 8) + buf[idx+54]*(1 << 16) + buf[idx+55]*(1 << 24)
            decisionIm5 = buf[idx+56]*(1 << 0) + buf[idx+57]*(1 << 8) + buf[idx+58]*(1 << 16) + buf[idx+59]*(1 << 24)


            Proteus_header[i]['real1_dec'] = decisionRe1
            Proteus_header[i]['im1_dec'] = decisionIm1
            Proteus_header[i]['real2_dec'] = decisionRe2
            Proteus_header[i]['im2_dec'] = decisionIm2
            Proteus_header[i]['real3_dec'] = decisionRe3
            Proteus_header[i]['im3_dec'] = decisionIm3
            Proteus_header[i]['real4_dec'] = decisionRe4
            Proteus_header[i]['im4_dec'] = decisionIm4
            Proteus_header[i]['real5_dec'] = decisionRe5
            Proteus_header[i]['im5_dec'] = decisionIm5
            
            state1 = buf[idx+60]*(1 << 0)
            state2 = buf[idx+61]*(1 << 0)
            state3 = buf[idx+62]*(1 << 0)
            state4 = buf[idx+63]*(1 << 0)
            state5 = buf[idx+64]*(1 << 0)
            
            Proteus_header[i]['state1'] = state1
            Proteus_header[i]['state2'] = state2
            Proteus_header[i]['state3'] = state3
            Proteus_header[i]['state4'] = state4
            Proteus_header[i]['state5'] = state5
            
        return Proteus_header

    def get_header_data(self, ddr_num):
        #Read all frames from Memory
        # 
        self._parent._set_cmd(':DIG:CHAN:SEL', ddr_num)
        #Choose what to read (only the frame-data without the header in this example)
        self._parent._set_cmd(':DIG:DATA:TYPE', 'HEAD')
        if (self.acq_mode() == "DUAL") :
            header_size = 72 # Header size taken from PG118 of manual 
        else : 
            header_size = 96 # Header size taken from PG118 of manual
        number_of_frames = self.NumSegments*self.NumRepetitions
        num_bytes = number_of_frames * header_size

        wav2 = np.zeros(num_bytes, dtype=np.uint8)
        rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav2, num_bytes)
        print(self._parent._get_cmd(":DIG:ACQ:STAT?")) # Perhaps check that second bit is set to 1 (all frames done)

        # Ensure all previous commands have been executed
        while (not self._parent._get_cmd('*OPC?')):
            pass
        self._parent._chk_err('in reading frame data.')

        return self._get_captured_header(N=number_of_frames, buf=wav2) #dec_vals

    def process_block(self, block_idx, cur_processor, blocksize):
        if block_idx == 0:
            #Choose what to read (only the frame-data without the header in this example)
            self._parent._set_cmd(':DIG:DATA:TYPE', 'FRAM')
            #Choose which frames to read (One or more frames in this case)
            self._parent._set_cmd(':DIG:DATA:SEL', 'FRAM') 
            
            self._parent._set_cmd(':DIG:DATA:FRAM', f'{1},{blocksize*self.NumSegments}')

            # Get the total data size (in bytes)
            resp = self._parent._get_cmd(':DIG:DATA:SIZE?')
            # self.num_bytes = 4176*np.uint64(resp)
            # self.num_bytes = np.uint64(resp)
            # print(resp, self.num_bytes, 'hi', self._parent._get_cmd(':DIG:DATA:FRAM?'))

            # wavlen = int(self.num_bytes // 2)
            wavlen = int(blocksize*self.NumSegments*self.NumSamples)
            # print(self.num_bytes)
            #TODO : Run a check on DSP before setting up the waves, NEED TO KNOW WHAT CHANNEL AS WELL
            if (self.ddr1_store() == "DIR") :
                wav1 = np.zeros(wavlen, dtype=np.uint16)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
                wav1 = wav1.reshape(blocksize, self.NumSegments, self.NumSamples)
            else :
                wav1 = np.zeros(wavlen, dtype=np.uint32)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
                wav1 = wav1.reshape(blocksize, self.NumSegments, self.NumSamples)

            if (self.ddr2_store() == "DIR") :
                wav2 = np.zeros(wavlen, dtype=np.uint16)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
                wav2 = wav2.reshape(blocksize, self.NumSegments, self.NumSamples)
            else :
                wav2 = np.zeros(wavlen, dtype=np.uint32)   #NOTE!!! FOR DSP, THIS MUST BE np.uint32 - SO MAKE SURE TO SWITCH/CHANGE (uint16 otherwise)
                wav2 = wav2.reshape(blocksize, self.NumSegments, self.NumSamples)

            self.wav1 = wav1
            self.wav2 = wav2

        resp = self._parent._get_cmd(':DIG:DATA:SIZE?')
        num_bytes = np.uint64(resp)

        # Select the frames to read
        self._parent._set_cmd(':DIG:DATA:FRAM', f'{1+block_idx*blocksize},{blocksize}')
        if (self.ChannelStates[0]) :
            # Read from channel 1
            self._parent._set_cmd(':DIG:CHAN:SEL', 1)
            rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', self.wav1, num_bytes)
        if (self.ChannelStates[1]) :
            # read from channel 2
            self._parent._set_cmd(':DIG:CHAN:SEL', 2)
            rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', self.wav2, num_bytes)
        # Check errors
        self._parent._chk_err('after downloading the ACQ data from the FGPA DRAM.')
        sampleRates = []
        
        # Adjust Sample Rates for DDC stages if in DSP Mode
        # if (self.ddr1_store() == "DIR1") :
        #     sampleRates.append(self.SampleRate)
        # elif (self.ddc_mode() == "REAL") :
        #     # We are in non-direct REAL mode = DSP is enabled
        #     sampleRates.append(self.SampleRate/16)
        # else :
        #     sampleRates.append(self.SampleRate)

        # if (self.ddr2_store() == "DIR2") :
        #     sampleRates = sampleRates.append(self.SampleRate)
        # elif (self.ddc_mode() == "REAL") :
        #     # We are in non-direct REAL mode = DSP is enabled
        #     sampleRates.append(self.SampleRate/16)
        # else :
        #     sampleRates.append(self.SampleRate)

        #TODO: Write some blocked caching code here (like with the M4i)... 
        """ 
        ret_val = {
                    'parameters' : ['repetition', 'segment', 'sample'],
                    'data' : {
                                'CH1' : self.wav1.astype(np.int32),
                                'CH2' : self.wav2.astype(np.int32),
                                },
                    'misc' : {'SampleRates' : [self.SampleRate] * 2}  #NOTE!!! DIVIDE SAMPLERATE BY /16 IF USING DECIMATION STAGES! # sampleRates
                }
        """
        ret_val = {
                        'parameters' : ['repetition', 'segment', 'sample'],
                        'data' : {},
                        'misc' : {'SampleRates' : [self.SampleRate]*2}
                    }
        # Only return data which matches channels that are active
        if (self.ChannelStates[0]) :
            ret_val['data']['CH1'] = self.wav1.astype(np.int32)
        if (self.ChannelStates[1]) :
            ret_val['data']['CH2'] = self.wav2.astype(np.int32)

        cur_processor.push_data(ret_val)

    def convert_IQ_to_sample(self, inp_i,inp_q,size):
        """
        Convert the signed number into 12bit FIX1_11 presentation
        """
        out_i = np.zeros(inp_i.size)
        out_i = out_i.astype(np.uint32)
        
        out_q = np.zeros(inp_q.size)
        out_q = out_q.astype(np.uint32)

        max_i = np.amax(abs(inp_i))
        max_q = np.amax(abs(inp_q))
        
        max = np.maximum(max_i,max_q)
        
        if max < 1:
            max = 1
        
        inp_i = inp_i / max
        inp_q = inp_q / max
        
        M = 2**(size-1)
        A = 2**(size)
        
        for i in range(inp_i.size):
            if(inp_i[i] < 0):
                out_i[i] = int(inp_i[i]*M) + A
            else:
                out_i[i] = int(inp_i[i]*(M-1))
                
        for i in range(inp_q.size):
            if(inp_q[i] < 0):
                out_q[i] = int(inp_q[i]*M) + A
            else:
                out_q[i] = int(inp_q[i]*(M-1))

        return out_i , out_q

    def pack_kernel_data(self, ki,kq) :
        """
        Method to pack kernel data 
        """
        out_i = []
        out_q = []
        L = int(ki.size/5)
        
        b_ki = np.zeros(ki.size)
        b_kq = np.zeros(ki.size)
        kernel_data = np.zeros(L*4)
        
        b_ki = b_ki.astype(np.uint16)
        b_kq = b_kq.astype(np.uint16)
        kernel_data = kernel_data.astype(np.uint32)
        
        # convert the signed number into 12bit FIX1_11 presentation
        b_ki,b_kq = self.convert_IQ_to_sample(ki,kq,12)
        
        # convert 12bit to 15bit because of FPGA memory structure
        for i in range(L):
            s1 = (b_ki[i*5+1]&0x7) * 4096 + ( b_ki[i*5]               )
            s2 = (b_ki[i*5+2]&0x3F) * 512 + ((b_ki[i*5+1]&0xFF8) >> 3 )
            s3 = (b_ki[i*5+3]&0x1FF) * 64 + ((b_ki[i*5+2]&0xFC0) >> 6 )
            s4 = (b_ki[i*5+4]&0xFFF) *  8 + ((b_ki[i*5+3]&0xE00) >> 9 )
            out_i.append(s1)
            out_i.append(s2)
            out_i.append(s3)
            out_i.append(s4)
        
        out_i = np.array(out_i)
        
        for i in range(L):
            s1 = (b_kq[i*5+1]&0x7) * 4096 + ( b_kq[i*5]               )
            s2 = (b_kq[i*5+2]&0x3F) * 512 + ((b_kq[i*5+1]&0xFF8) >> 3 )
            s3 = (b_kq[i*5+3]&0x1FF) * 64 + ((b_kq[i*5+2]&0xFC0) >> 6 )
            s4 = (b_kq[i*5+4]&0xFFF) *  8 + ((b_kq[i*5+3]&0xE00) >> 9 )
            out_q.append(s1)
            out_q.append(s2)
            out_q.append(s3)
            out_q.append(s4)

        out_q = np.array(out_q)

        fout_i = np.zeros(out_i.size,dtype=np.uint16)
        fout_q = np.zeros(out_q.size,dtype=np.uint16)

        for i in range(out_i.size):
            if(out_i[i] >16383):
                fout_i[i] = out_i[i] #- 32768
            else:
                fout_i[i] = out_i[i]

        for i in range(out_q.size):
            if(out_q[i] >16383):
                fout_q[i] = out_q[i] #- 32768
            else:
                fout_q[i] = out_q[i]

        for i in range(L*4):
            kernel_data[i] = out_q[i]*(1 << 16) + out_i[i]
        sim_kernel_data = []

        for i in range(kernel_data.size):
            sim_kernel_data.append(hex(kernel_data[i])[2:])

        return kernel_data

    def setup_filter(self, filter_channel, filter_array, **kwargs) :
        """
        Method to set coefficients for specific FIR filter on Tabor
        @param filter_channel:
        """
        valid_real_channels = ["DBUQI", "DBUGQ"]
        valid_complex_channels = ["I1", "Q1", "I2", "Q2"]
        # Check that the requested block is valid for the current ddc mode
        # NOTE: could remove this check and rely on user to know what blocks are being used when
        print("DDC mode is: ", self.ddc_mode())
        if (self.ddc_mode() == "REAL" and filter_channel in valid_real_channels) :
            self.fir_block(filter_channel)
        elif (self.ddc_mode() == "COMP" and filter_channel in valid_complex_channels) :
            self.fir_block(filter_channel)
        else :
            print("Not a vaild filter channel for current DDC mode")

        # Check array size is valid
        if (len(filter_array) > int(self._parent._inst.send_scpi_query(':DSP:FIR:LENG?'))) :
            print("filter array contains too many coefficients, limit is {0}".format(self._parent._inst.send_scpi_query(':DSP:FIR:LENG?')))
            return

        # dsp decision frame
        # TODO: what is the frame size of the calculation
        self._parent._send_cmd(':DSP:DEC:FRAM {0}'.format(1024))
        resp = self._parent._inst.send_scpi_query(':SYST:ERR?')
        print(resp)

        # Load in filter coefficients
        for i in range(0, len(filter_array)) :
            self._parent._send_cmd(':DSP:FIR:COEF {},{}'.format(i, filter_array[i]))
            
        # self._parent._send_cmd(':DSP:IQD:SEL IQ4')           # DBUG | IQ4 | IQ5 | IQ6 | IQ7
        # self._parent._send_cmd(':DSP:IQD:KER:DATA', mem)
        # resp =  self._parent._inst.send_scpi_query(':SYST:ERR?')
        # print(resp)

        # define decision DSP1 path SVM
        # self._parent._send_cmd(':DSP:DEC:IQP:SEL DSP1')
        # self._parent._send_cmd(':DSP:DEC:IQP:OUTP SVM')
        # self._parent._send_cmd(':DSP:DEC:IQP:LINE 1,-0.625,-5')
        # self._parent._send_cmd(':DSP:DEC:IQP:LINE 2,1.0125,0.5')
        # self._parent._send_cmd(':DSP:DEC:IQP:LINE 3,0,0')

    def settle_dsp_processors(self, cur_processor):
        final_dsp_order = {
            'dsp_active' : False,
            'kernels' : [],
            'read_IQ': True,
            'doFFT': False,
            'final_scale_factor' : 1
        }

        kernel_settled = False
        decimation = False
        final_dsp_order['avSamples'] = False
        final_dsp_order['avRepetitions'] = False

        if isinstance(cur_processor, ProcessorFPGA) and len(cur_processor.pipeline) == 0:
            return final_dsp_order
        else:
            final_dsp_order['dsp_active'] = True

        for m, cur_node in enumerate(cur_processor.pipeline):
            if isinstance(cur_node, FPGA_DDCFIR) or isinstance(cur_node, FPGA_DDC):
                assert not kernel_settled, "The P2584M only supports one kernel stage (e.g. variants of DDCs)."
                assert not decimation, "The P2584M only supports kernel stages (e.g. variants of DDCs) before decimation."
                assert not final_dsp_order['avSamples'], "The P2584M only supports kernel stages (e.g. variants of DDCs) before averaging."
                assert not final_dsp_order['avRepetitions'], "The P2584M only supports kernel stages (e.g. variants of DDCs) before averaging."
                final_dsp_order['kernels'], final_dsp_order['final_scale_factor'] = cur_node.get_params(sample_rate = [self.SampleRate]*2,  num_samples = self.NumSamples)
                kernel_settled = True
            elif isinstance(cur_node, FPGA_Decimation):
                assert not final_dsp_order['avSamples'], "The P2584M only supports decimation before averaging."
                assert not final_dsp_order['avRepetitions'], "The P2584M only supports decimation before averaging."
                param, fac = cur_node.get_params()
                assert param == 'sample', "The P2584M only supports mandatory 10x decimation on the samples."
                assert fac == 10, "The P2584M only supports mandatory 10x decimation on the samples."
                decimation = True
            elif isinstance(cur_node, FPGA_FFT):
                assert not final_dsp_order['avSamples'], "The P2584M only supports FFT before averaging."
                assert not final_dsp_order['avRepetitions'], "The P2584M only supports FFT before averaging."
                assert decimation, "The P2584M only supports FFT after a 10x mandatory decimation (do it via an \'FPGA_Decimation\' stage)."
                assert len(final_dsp_order['kernels'][0]) == 1 and len(final_dsp_order['kernels'][1]) == 0, "The P2584M only supports FFT when using 1 DDC channel and that only on channel 1."
                param = cur_node.get_params()
                assert param[0] == 0 and param[1] == 1, "The FFT IQ indices must be 0 and 1 for the P2584M."
                assert self.NumSamples == 10080, "NumSamples must be 10080 when using FFT processing on the P2584M."
                final_dsp_order['doFFT'] = True
            elif isinstance(cur_node, FPGA_Integrate):
                assert decimation, "The P2584M only supports averaging after a 10x mandatory decimation (do it via an \'FPGA_Decimation\' stage)."
                param = cur_node.get_params()
                if param == 'sample':
                    assert not final_dsp_order['avSamples'], "There is already a sample averaging stage."
                    assert not final_dsp_order['avRepetitions'], "Cannot average samples after averaging over repetitions."
                    final_dsp_order['avSamples'] = True
                elif param == 'repetition':
                    assert not final_dsp_order['avRepetitions'], "There is already a repetition averaging stage."
                    assert self.NumSegments == 1, "The P2584M does not currently support repetition averaging over multiple segments."
                    #TODO: Modify in a future firmware release...
                    if len(final_dsp_order['kernels']) == 1:
                        assert len(final_dsp_order['kernels'][0]) <= 2, "The current firmware on the P2584M does not support averaging on more than 2 channels. Wait for a future release."
                    elif len(final_dsp_order['kernels']) == 2:
                        assert len(final_dsp_order['kernels'][0]) + len(final_dsp_order['kernels'][1]) <= 2, "The current firmware on the P2584M does not support averaging on more than 2 channels. Wait for a future release."
                    final_dsp_order['avRepetitions'] = True
                else:
                    assert False, f"Cannot average over \'{param}\'"
        #If no Kernel, it's just a passthrough...
        if len(final_dsp_order['kernels']) == 0:
            if self.ChannelStates[0]:
                final_dsp_order['kernels'] += [[(np.ones(self.NumSamples), np.zeros(self.NumSamples))]]
            if self.ChannelStates[1]:
                final_dsp_order['kernels'] += [[(np.ones(self.NumSamples), np.zeros(self.NumSamples))]]
            final_dsp_order['read_IQ'] = False
        return final_dsp_order

                

    def process_dsp_kernel(self, kernelIQs, is_DBUG_line = False):
        if len(kernelIQs) == 2:
            assert len(kernelIQs[0]) <= 5, "The Tabor P2584M does not support more than 5 demodulations per channel when demodulating across 2 channels."
            assert len(kernelIQs[1]) <= 5, "The Tabor P2584M does not support more than 5 demodulations per channel when demodulating across 2 channels."
            self.ddcBindChannels(False)
            num_ch_divs = (len(kernelIQs[0]), len(kernelIQs[1]))
        else:
            self.ddcBindChannels(True)
            num_ch_divs = (len(kernelIQs[0]), 0)                    
        curIQpath = 4
        for cur_ch in kernelIQs:
            for k, cur_kernel_IQ in enumerate(cur_ch):
                kI, kQ = cur_kernel_IQ
                mem = self.pack_kernel_data(kI, kQ)
                if is_DBUG_line:
                    self._parent._set_cmd(':DSP:IQD:SEL', 'DBUG')
                else:
                    self._parent._set_cmd(':DSP:IQD:SEL', f"IQ{curIQpath}")
                self._parent._chk_err("after trying to setup the IQ path.")
                self._parent._inst.write_binary_data(':DSP:IQD:KER:DATA', mem)
                self._parent._chk_err("after trying to setup the IQ kernel.")
                curIQpath += 1
            curIQpath = 9   #CH2 starts from IQ9 onwards
        return num_ch_divs

    def _perform_data_capture(self, cur_processor, final_dsp_order, blocksize):
        num_frames = self.NumRepetitions*self.NumSegments
        if final_dsp_order['avRepetitions']:
            num_frames = 1

        self._parent._chk_err('before')
        self._parent._set_cmd(':DIG:INIT', 'ON')
        self._parent._chk_err('dig:on')
        
        #Poll for status bit
        loopcount = 0
        captured_frame_count = 0
        while captured_frame_count < num_frames:
            resp = self._parent._get_cmd(":DIG:ACQuire:FRAM:STATus?")
            resp_items = resp.split(',')
            captured_frame_count = int(resp_items[3])
            done = int(resp_items[1])
            #print("{0}. {1}".format(done, resp_items))
            loopcount += 1
            if loopcount > 100000 and captured_frame_count == 0:    #As in nothing captured over 100000 check-loops...
                #print("No Trigger was detected")
                assert False, "No trigger detected during the acquisiton sniffing window."

        #TODO: Write some blocked caching code here (like with the M4i)...
        # If processor is supplied apply it
        #The blocks are for the GPU - i.e. it cannot process it all in one go at times...
        if cur_processor and not isinstance(cur_processor, ProcessorFPGA):
            self.process_block(0, cur_processor, blocksize)
            block_idx = 1
            while block_idx*blocksize < self.NumRepetitions*self.NumSegments: # NOTE : some strange logic, perhaps tied to the logic above
                self.process_block(block_idx, cur_processor, blocksize)
                block_idx += 1
            return cur_processor.get_all_data()
        else:
            # No processor supplied
            done = 0
            while not done:
                done = int(self._parent._get_cmd(":DIG:ACQuire:FRAM:STATus?").split(',')[3])
            # Stop the digitizer's capturing machine (to be on the safe side)
            self._parent._set_cmd(':DIG:INIT', 'OFF')
            self._parent._chk_err('after actual acquisition.')

    def NormalAVGSignal(self, wav,AvgCount,is_dsp,ADCFS=1000,BINOFFSET=False):
        def getAvgDivFactor(AvgCount=1000,is_dsp=False):
            AvgDivFactor = int(np.log2(AvgCount))
            if not is_dsp:
                AvgDivFactor = 0 if (AvgDivFactor + 12 <= 28) else AvgDivFactor + 12 - 28
            else:
                AvgDivFactor = 0 if (AvgDivFactor + 15 <= 28) else AvgDivFactor + 15 - 28
            return AvgDivFactor
        def convert_binoffset_to_signed(inp,bitnum):
            return inp - 2**(bitnum-1)
        def convertTimeSignedDataTomV(x,adcfs=1000,bitnum=15):
            maxadc = 2**(bitnum-1) - 1
            return adcfs * (x / maxadc)

        AvgDivFactor = getAvgDivFactor(AvgCount,is_dsp)
        # taking into acount the 28bit position inside the 36bit word inside the FPGA
        AvgCount = AvgCount // 2**AvgDivFactor
        
        if not is_dsp:
            BITNUM = 12
        else:
            BITNUM = 15
        if BINOFFSET == False:    
            signed_wav = np.zeros(wav.shape, dtype=np.int32)
            # convert binary offset to signed presentation
            signed_wav = convert_binoffset_to_signed(wav*1.0,28)
            # Normaling
            wavNorm = signed_wav // AvgCount
            # convert to mV
            ADCFS=1    #Making ADFS=1 for V instead of 1V
            mVwavNorm = convertTimeSignedDataTomV(wavNorm,ADCFS,bitnum=BITNUM)
        
            return mVwavNorm
        else:
            wav = wav // AvgCount
            
            return wav

    def conv_data(self, data, final_dsp_order, fac=2**15):
        if final_dsp_order['avRepetitions']:
            return self.NormalAVGSignal(data, self.NumRepetitions, final_dsp_order['dsp_active'])*1.0
        else:
            return (data*1.0 - fac) / fac

    def _read_data_frames(self, final_dsp_order):
        #Choose to read all frames
        self._parent._set_cmd(':DIG:DATA:SEL', 'ALL')
        #Read frame-data without the header
        self._parent._set_cmd(':DIG:DATA:TYPE', 'FRAM')
        
        #Get the total data size (in bytes)
        self._parent._set_cmd(':DIG:CHAN:SEL', 1)
        resp = self._parent._get_cmd(':DIG:DATA:SIZE?')
        num_bytes = np.uint64(resp)

        if final_dsp_order['avRepetitions']:
            wavlen = int(num_bytes // 4)    #32bits as it's a 28bit counter...
            fin_shape = (1, self.NumSegments, int(self.NumSamples*12/10))
        else:
            wavlen = int(num_bytes // 2)
            if final_dsp_order['dsp_active']:
                fin_shape = (self.NumRepetitions, self.NumSegments, int(self.NumSamples*12/10))
            else:
                fin_shape = (self.NumRepetitions, self.NumSegments, self.NumSamples)
        # Ensure all previous commands have been executed
        while (not self._parent._get_cmd('*OPC?')):
            pass
        if self.ChannelStates[0]:
            # Read from channel 1
            self._parent._set_cmd(':DIG:CHAN:SEL', 1)
            if final_dsp_order['avRepetitions']:
                wav1 = np.zeros(wavlen, dtype=np.uint32)
            else:
                wav1 = np.zeros(wavlen, dtype=np.uint16)
            rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav1, num_bytes)
            wav1 = wav1.reshape(*fin_shape)
            # Ensure all previous commands have been executed
            while (not self._parent._get_cmd('*OPC?')):
                pass
        if self.ChannelStates[1]:
            # read from channel 2
            self._parent._set_cmd(':DIG:CHAN:SEL', 2)
            if final_dsp_order['avRepetitions']:
                wav2 = np.zeros(wavlen, dtype=np.uint32)
            else:
                wav2 = np.zeros(wavlen, dtype=np.uint16)
            rc = self._parent._inst.read_binary_data(':DIG:DATA:READ?', wav2, num_bytes)
            wav2 = wav2.reshape(*fin_shape)
            # Ensure all previous commands have been executed
            while (not self._parent._get_cmd('*OPC?')):
                pass
        # Check errors
        self._parent._chk_err('after downloading the ACQ data from the FGPA DRAM.')
        
        ret_val = {
                    'data' : {},
                    'misc' : {}
                }
        if final_dsp_order['avRepetitions']:
            ret_val['parameters'] = ['sample']
        else:
            ret_val['parameters'] = ['repetition', 'sample']
        #TODO: Change after new firmware release...
        ret_val['parameters'].pop(-1)        
        leSampleRates = []
        num_ch_divs = final_dsp_order['num_ch_divs']
        final_scale = final_dsp_order['final_scale_factor']
        if not final_dsp_order['dsp_active']:
            # Only return data which matches channels that are active
            if (self.ChannelStates[0]) :
                ret_val['data']['CH1'] = self.conv_data(wav1) * final_scale
                leSampleRates += [self.SampleRate]
            if (self.ChannelStates[1]) :
                ret_val['data']['CH2'] = self.conv_data(wav2) * final_scale
                leSampleRates += [self.SampleRate]
            ret_val['misc']['SampleRates'] = leSampleRates
        else:
            if num_ch_divs[0] > 0:
                wav1 = self.conv_data(wav1, final_dsp_order)
            if final_dsp_order['doFFT']:
                ret_val['data']['fft_real'] = wav1[:,:,int(2*5+1)::12] * final_scale
                ret_val['data']['fft_imag'] = wav1[:,:,int(2*5)::12] * final_scale
                #
                wav2 = self.conv_data(wav2, final_dsp_order)
                ret_val['data']['debug_time_I'] = wav2[:,:,int(2*5+1)::12] * final_scale
                ret_val['data']['debug_time_Q'] = wav2[:,:,int(2*5)::12] * final_scale
            else:
                offset = 0
                for m in range(num_ch_divs[0]):
                    if final_dsp_order['avRepetitions']:
                        ret_val['data'][f'CH1_{m}_I'] = wav1[0,:,int(2*(m+offset)+1)::2][:,:int(self.NumSamples/10)] * final_scale*self.NumRepetitions  #TODO: Review after new firmware release
                        ret_val['data'][f'CH1_{m}_Q'] = wav1[0,:,int(2*(m+offset))::2][:,:int(self.NumSamples/10)] * final_scale*self.NumRepetitions    #TODO: Review after new firmware release
                        #TODO: Change after new firmware release...
                        if final_dsp_order['avSamples']:
                            ret_val['data'][f'CH1_{m}_I'] = np.array([np.sum(ret_val['data'][f'CH1_{m}_I'])])*2.0
                            ret_val['data'][f'CH1_{m}_Q'] = np.array([np.sum(ret_val['data'][f'CH1_{m}_Q'])])*2.0
                        #TODO: Change after new firmware release...
                        wav1 =self.conv_data(wav2, final_dsp_order)
                        offset = -1
                    else:
                        ret_val['data'][f'CH1_{m}_I'] = wav1[:,:,int(2*(m+offset)+1)::12] * final_scale
                        ret_val['data'][f'CH1_{m}_Q'] = wav1[:,:,int(2*(m+offset))::12] * final_scale
                    leSampleRates += [self.SampleRate / 10]*2
                    if m == 4:
                        wav1 = self.conv_data(wav2, final_dsp_order)    #This is relevant in the BIND mode...
                        offset = -5
                if num_ch_divs[1] > 0:
                    wav2 =self.conv_data(wav2, final_dsp_order)
                for m in range(num_ch_divs[1]):
                    if final_dsp_order['avRepetitions']:
                        ret_val['data'][f'CH2_{m}_I'] = wav2[0,:,int(2*m+1)::10] * final_scale*self.NumRepetitions
                        ret_val['data'][f'CH2_{m}_Q'] = wav2[0,:,int(2*m)::10] * final_scale*self.NumRepetitions
                        #TODO: Change after new firmware release...
                        if final_dsp_order['avSamples']:
                            ret_val['data'][f'CH2_{m}_I'] = np.array([np.sum(ret_val['data'][f'CH2_{m}_I'])])*2.0
                            ret_val['data'][f'CH2_{m}_Q'] = np.array([np.sum(ret_val['data'][f'CH2_{m}_Q'])])*2.0
                    else:
                        ret_val['data'][f'CH2_{m}_I'] = wav2[:,:,int(2*m+1)::12] * final_scale
                        ret_val['data'][f'CH2_{m}_Q'] = wav2[:,:,int(2*m)::12] * final_scale
                    leSampleRates += [self.SampleRate / 10]*2
                ret_val['misc']['SampleRates'] = leSampleRates
        return ret_val

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

        #Settle Triggers
        #TODO: Currently, by design, the Trigger1 and Trigger 2 Sources are from the same task - it doesn't have to be :\ Would this imply multiple ACQ modules?
        assert self._parent.AWG._cur_internal_trigs.count(True) <= 1, "Only one internal trigger is allowed to trigger both ADC channels. Separate triggering is not yet supported."
        if self._parent.AWG._cur_internal_trigs.count(True) > 0:
            chan_ind = self._parent.AWG._cur_internal_trigs.index(True)
            self._parent.ACQ.trigger1Source(f'TASK{chan_ind+1}')
            self._parent.ACQ.trigger2Source(f'TASK{chan_ind+1}')
        else:
            self._parent.ACQ.trigger1Source('EXT')
            self._parent.ACQ.trigger2Source('EXT')

        blocksize = min(self.blocksize(), self.NumRepetitions)


        cur_processor = kwargs.get('data_processor', None)
        if not isinstance(cur_processor, ProcessorFPGA):
            assert self.NumSamples % 48 == 0, "The number of samples must be divisible by 48 if in DUAL mode."
            final_dsp_order = self.settle_dsp_processors(cur_processor)
        else:
            if not cur_processor.compare_pipeline_state(self._last_dsp_state):
                final_dsp_order = self.settle_dsp_processors(cur_processor)
                reprogram_dsps = True
            else:
                final_dsp_order = self._last_dsp_order
                reprogram_dsps = False

        self._allocate_frame_memory(final_dsp_order)

        #Clean memory 
        self._parent._send_cmd(':DIG:ACQ:ZERO:ALL')
        self._parent._chk_err('after clearing memory.')

        #Setup DSP blocks if applicable
        num_ch_divs = []
        #Idea is that the DSP functions (e.g. average or kernel) should only be touched by this API. Thus, the states should remain concurrent...
        if final_dsp_order['dsp_active'] and reprogram_dsps:
            assert self.ChannelStates[0]==1 and self.ChannelStates[1]==1, "Must be in DUAL-mode (i.e. both channels active) to use DSP."
            assert (self.NumSamples) % 360 == 0, "If using FPGA DSP blocks, the number of samples must be divisible by 360. Note that it is 10x decimated."
            assert self.NumSamples <= 10240, "If using FPGA DSP blocks, the number of samples must be limited to 10240."

            #It's DSP time
            if final_dsp_order['doFFT']:
                filt_coeffs = scipy.signal.firwin(51, 100e6, fs=2.5e9)
                self.ddr_store('FFT')
                self.fft_input('DBUG')
                self.fir_block('DBUGI')
                self._parent._set_cmd(':DSP:FIR:BYPass','OFF')
                self._parent._inst.write_binary_data(':DSP:FIR:DATA', filt_coeffs)       
                self.fir_block('DBUGQ')
                self._parent._set_cmd(':DSP:FIR:BYPass','OFF') 
                self._parent._inst.write_binary_data(':DSP:FIR:DATA', filt_coeffs)
                final_dsp_order['num_ch_divs'] = self.process_dsp_kernel(final_dsp_order['kernels'], True)
            else:
                self.ddr_store('DSP')
                self._parent._chk_err('after setting to DSP.')
                Frame_len = self.NumSamples
                DSP_DEC_LEN = Frame_len / 10# - 10
                self._parent._set_cmd(f':DSP:DEC:FRAM', f'{int(DSP_DEC_LEN)}')
                self._parent._set_cmd(':DSP:STOR', 'DSP')
                self._parent._chk_err('after setting up DSP.')
                #Setup kernel block
                final_dsp_order['num_ch_divs'] = self.process_dsp_kernel(final_dsp_order['kernels'])

            #Setup repetition averaging if requested
            if final_dsp_order['avRepetitions']:
                self.averageEnable(True)
                self._parent._set_cmd(':DIG:ACQuire:AVERage:COUNt', self.NumRepetitions)
            else:
                self.averageEnable(False)

            self._last_dsp_state = cur_processor.get_pipeline_state()
            self._last_dsp_order = final_dsp_order

        self._perform_data_capture(cur_processor, final_dsp_order, blocksize)

        if final_dsp_order['avSamples'] and not final_dsp_order['avRepetitions']:   #TODO: Change after firmware update (i.e. read header for average)
            ret_val = {
                    'parameters' : ['repetition'],
                    'data' : {},
                    'misc' : {}
                }
            if final_dsp_order['avRepetitions']:
                ret_val['parameters'].pop(0)
            leSampleRates = []
            num_ch_divs = final_dsp_order['num_ch_divs']
            #
            headers1 = self.get_header_data(1)
            if final_dsp_order['num_ch_divs'][0] > 5 or final_dsp_order['num_ch_divs'][1] > 0:
                headers2 = self.get_header_data(2)
            else:
                headers2 = []
            def proc_data(data, final_dsp_order, ret_val):
                if final_dsp_order['avRepetitions']:
                    #TODO: Later make this read straight off decision block changes in their newer firmware releases
                    return np.array([np.sum(data)])*final_dsp_order['final_scale_factor']
                else:
                    return self.conv_data(np.array([data])*final_dsp_order['final_scale_factor'], final_dsp_order, 2**14)*2.0   #x2 as the DSP takes the 15 MSBs
            offset = 0
            for m in range(num_ch_divs[0]):
                ret_val['data'][f'CH1_{m}_I'] = proc_data( np.array([x[f'real{m-offset+1}_dec'] for x in headers1])*1.0, final_dsp_order, ret_val )
                ret_val['data'][f'CH1_{m}_Q'] = proc_data( np.array([x[f'im{m-offset+1}_dec'] for x in headers1]), final_dsp_order, ret_val )
                leSampleRates += [self.SampleRate / 10]*2
                if m == 4:
                    headers1 = headers2    #This is relevant in the BIND mode...
                    offset = -5
            for m in range(num_ch_divs[1]):
                ret_val['data'][f'CH2_{m}_I'] = proc_data( np.array([x[f'real{m+1}_dec'] for x in headers2]), final_dsp_order, ret_val )
                ret_val['data'][f'CH2_{m}_Q'] = proc_data( np.array([x[f'im{m+1}_dec'] for x in headers2]), final_dsp_order, ret_val )
                leSampleRates += [self.SampleRate / 10]*2
            ret_val['misc']['SampleRates'] = leSampleRates
            return ret_val
        else:
            return self._read_data_frames(final_dsp_order)


class Tabor_P2584M(Instrument):
    def __init__(self, name, pxi_chassis: int,  pxi_slot: int, **kwargs):
        super().__init__(name, **kwargs) #No address...
        #Currently Tabor doesn't seem to use pxi_chassis in their newer drivers - curious...

        # Use lib_dir_path = None 
        # for default location (C:\Windows\System32)
        # Change it only if you know what you are doing
        lib_dir_path = None
        self._admin = TepAdmin(lib_dir_path)
        self._admin.open_inst_admin()
        self._inst = self._admin.open_instrument(slot_id=pxi_slot, reset_hot_flag=True)
        assert self._inst != None, "Failed to load the Tabor AWG instrument - check slot ID perhaps or whether the Tabor unit is being used in another Python instance."

        #Tabor's driver will print error messages if any are present after every command - it is an extra query, but provides security
        self._inst.default_paranoia_level = 2

        self._debug_logs = ''
        self._debug = True

        resp = self._inst.send_scpi_query('*IDN?')
        print('Connected to: ' + resp)
        resp = self._inst.send_scpi_query(":SYST:iNF:MODel?")
        print("Model: " + resp)

        #Get HW options
        # self._inst.send_scpi_query("*OPT?")
        #Reset - must!
        self._send_cmd( "*CLS")
        self._send_cmd( "*RST")

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
        if self._debug:
            self._debug_logs += cmd + '\n'
        self._inst.send_scpi_query(cmd)
    
    def _get_cmd(self, cmd):
        if self._debug:
            self._debug_logs += cmd + '\n'
        return self._inst.send_scpi_query(cmd)
    def _set_cmd(self, cmd, value):
        if self._debug:
            self._debug_logs += f"{cmd} {value}\n"
        self._inst.send_scpi_query(f"{cmd} {value}")
    
    def _chk_err(self, msg):
        resp = self._get_cmd(':SYST:ERR?')
        resp = resp.rstrip()
        assert resp.startswith('0'), 'ERROR: "{0}" {1}.'.format(resp, msg)

