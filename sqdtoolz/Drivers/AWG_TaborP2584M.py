import os
import sys
from sqdtoolz.Drivers.Dependencies.teproteus import TEProteusAdmin as TepAdmin
from sqdtoolz.Drivers.Dependencies.teproteus import TEProteusInst as TepInst

import numpy as np
import time

from qcodes import Instrument, InstrumentChannel, validators as vals
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
            val_mapping={True:  1, False: 0})

    def _get_cmd(self, cmd):
        #Perform channel-select
        self._parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Query command
        return self._parent._inst.send_scpi_query(cmd)

    def _set_cmd(self, cmd, value):
        #Perform channel-select
        self._parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Perform command
        self._parent._inst.send_scpi_cmd(f'{cmd} {value}')

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


class AWG_TaborP2584M(Instrument):
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
        self._inst.send_scpi_cmd( ":INST:CHAN 1")
        self._inst.send_scpi_cmd( ":TRAC:DEL:ALL")        
            
        #Get the DAC mode (8 bits or 16 bits)
        dac_mode = self._inst.send_scpi_query(':SYST:INF:DAC?')
        if dac_mode == 'M0':
            self._max_dac = 65535
            self._data_type = np.uint16 
        else:
            self._max_dac = 255
            self._data_type = np.uint8 
        self._half_dac = self._max_dac // 2.0

        #Get number of channels
        self._num_channels = int(self._inst.send_scpi_query(":INST:CHAN? MAX"))
        #Get the maximal number of segments
        self._max_seg_number = int(self._inst.send_scpi_query(":TRACe:SELect:SEGMent? MAX"))
        #Get the available memory in bytes of wavform-data (per DDR):
        self._arbmem_capacity_bytes = int(self._inst.send_scpi_query(":TRACe:FREE?"))
        
        self.add_parameter(
            'sample_rate', label='Sample Rate', unit='Hz',
            get_cmd=partial(self._get_cmd, ':SOUR:FREQ:RAST?'),
            set_cmd=partial(self._set_cmd, ':SOUR:FREQ:RAST'),
            vals=vals.Numbers(1e9, 9e9),    #Note that this is a cheat using Nyquist trickery...
            get_parser=float)
            
            
        #Setup triggering
        # self._set_cmd(':TRIG:SOUR:ENAB', 'TRG1')
        self._set_cmd(':TRIG:SEL', 'TRG1')
        self._set_cmd(':TRIG:STAT', 'ON')
        self._set_cmd(':TRIG:LEV', 0.3)
        self._set_cmd(':TRIG:SEL', 'TRG2')
        self._set_cmd(':TRIG:STAT', 'OFF')
        self._set_cmd(':TRIG:SEL', 'INT')
        self._set_cmd(':TRIG:STAT', 'OFF')
        # self._set_cmd(':INIT:CONT', 'OFF')

        self._trigger_edge = 1

        self._ch_list = ['CH1', 'CH2', 'CH3', 'CH4']
        # Output channels added to both the module for snapshots and internal Trigger Sources for the DDG HAL...
        for ch_ind, ch_name in enumerate(self._ch_list):
            cur_channel = AWG_TaborP2584M_channel(self, ch_name, ch_ind+1)
            self.add_submodule(ch_name, cur_channel)

    def close():
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

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]
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
        self._set_cmd(':INST:CHAN', chan_ind+1)
        #Delete and Define segment (noting that it's taken as 1 or 2 for channels 1|3 and 2|4 respectively...)
        seg_id = int(chan_ind % 2 + 1)
        self._set_cmd('TRAC:DEL', seg_id)
        self._send_cmd(f':TRAC:DEF {seg_id}, {cur_data.size}')
        
        # self._send_data_to_memory(seg_id, cur_data)
        self._send_data_to_memory(seg_id, cur_data)
        self._send_cmd(f':TRAC:DEF {seg_id+1}, {cur_data.size}')
        self._send_data_to_memory(seg_id+1, -cur_data)

        self._program_task_table(chan_ind+1, [AWG_TaborP2584M_task(seg_id, 1, 2, 'TRG1'),AWG_TaborP2584M_task(seg_id+1, 1, 1, 'NONE')])
        self._set_cmd(':SOUR:FUNC:MODE:TASK', 1)
        self._set_cmd(':SOUR:FUNC:MODE:TYPE', 'TASK')        

    def _program_task_table(self, channel_index, tasks):
        #Select current channel
        self._set_cmd(':INST:CHAN', channel_index)
        #Allocate a set number of rows for the task table
        self._set_cmd(':TASK:COMP:LENG', len(tasks))

        for task_ind, cur_task in enumerate(tasks):
            self._set_cmd(':TASK:COMP:SEL', task_ind + 1)
            #Set the task to be solitary (i.e. not a part of an internal sequence inside Tabor...)
            self._send_cmd(':TASK:COMP:TYPE SING')
            #Set task parameters...
            self._set_cmd(':TASK:COMP:LOOP', cur_task.num_cycles)
            self._set_cmd(':TASK:COMP:SEGM', cur_task.seg_num)
            self._set_cmd(':TASK:COMP:NEXT1', cur_task.next_task_ind)
            self._set_cmd(':TASK:COMP:ENAB', cur_task.trig_src)
      
        #Download task table to channel
        self._send_cmd(':TASK:COMP:WRIT')
        # self._set_cmd(':FUNC:MODE', 'TASK')

        #Check for errors...
        resp = self._inst.send_scpi_query(':SYST:ERR?')
        resp = resp.rstrip()
        assert resp.startswith('0'), 'ERROR: "{0}" after writing task table'.format(resp)

    def _send_data_to_memory(self, seg_ind, wfm_data_normalised):
        #Condition the data
        final_data = (wfm_data_normalised * self._half_dac + self._half_dac).astype(self._data_type)
        
        #Select the segment
        self._set_cmd(':TRAC:SEL', seg_ind)
        #Increase the timeout before writing binary-data:
        self._inst.timeout = 30000
        #Send the binary-data with *OPC? added to the beginning of its prefix.
        # self._inst.write_binary_data('*OPC?; :TRAC:DATA', final_data)
        #!!!There seems to be some API changes that basically breaks their code - removing OPC for now...
        self._inst.write_binary_data(':TRAC:DATA', final_data)
        #Read the response to the *OPC? query that was added to the prefix of the binary data
        #resp = self._inst.()
        #Set normal timeout
        self._inst.timeout = 10000
        #Check for errors...
        resp = self._inst.send_scpi_query(':SYST:ERR?')
        resp = resp.rstrip()
        assert resp.startswith('0'), 'ERROR: "{0}" after writing binary values'.format(resp)


