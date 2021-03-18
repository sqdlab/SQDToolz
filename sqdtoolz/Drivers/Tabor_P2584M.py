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

    def _get_mkr_cmd(self, cmd, mkr_num):
        #Perform channel-select
        self._parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Perform marker-select
        self._parent._inst.send_scpi_cmd(f':MARK:SEL {mkr_num}')
        #Perform command
        return self._parent._inst.send_scpi_query(cmd)

    def _set_mkr_cmd(self, cmd, mkr_num, value):
        #Perform channel-select
        self._parent._inst.send_scpi_cmd(f':INST:CHAN {self._channel}')
        #Perform marker-select
        self._parent._inst.send_scpi_cmd(f':MARK:SEL {mkr_num}')
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

class TaborP2584M_AWG:
    def __init__(self, parent_instr):
        self.parent = parent_instr

        self.parent._set_cmd(':INST:CHAN', 1)
        self.parent._send_cmd(':TRAC:DEL:ALL')        

        #Get the DAC mode (8 bits or 16 bits)
        dac_mode = self.parent._get_cmd(':SYST:INF:DAC?')
        if dac_mode == 'M0':
            self._max_dac = 65535
            self._data_type = np.uint16 
        else:
            self._max_dac = 255
            self._data_type = np.uint8 
        self._half_dac = self._max_dac // 2.0

        #Get number of channels
        self._num_channels = int(self.parent._get_cmd(":INST:CHAN? MAX"))
        #Get the maximal number of segments
        self._max_seg_number = int(self.parent._get_cmd(":TRACe:SELect:SEGMent? MAX"))
        #Get the available memory in bytes of wavform-data (per DDR):
        self._arbmem_capacity_bytes = int(self.parent._get_cmd(":TRACe:FREE?"))
        
        self.parent.add_parameter(
            'sample_rate', label='Sample Rate', unit='Hz',
            get_cmd=partial(self.parent._get_cmd, ':SOUR:FREQ:RAST?'),
            set_cmd=partial(self.parent._set_cmd, ':SOUR:FREQ:RAST'),
            vals=vals.Numbers(1e9, 9e9),    #Note that this is a cheat using Nyquist trickery...
            get_parser=float)
            
        #Setup triggering
        # self._set_cmd(':TRIG:SOUR:ENAB', 'TRG1')
        self.parent._set_cmd(':TRIG:SEL', 'TRG1')
        self.parent._set_cmd(':TRIG:STAT', 'ON')
        self.parent._set_cmd(':TRIG:LEV', 0.3)
        self.parent._set_cmd(':TRIG:SEL', 'TRG2')
        self.parent._set_cmd(':TRIG:STAT', 'OFF')
        self.parent._set_cmd(':TRIG:SEL', 'INT')
        self.parent._set_cmd(':TRIG:STAT', 'OFF')
        # self._set_cmd(':INIT:CONT', 'OFF')

        self._trigger_edge = 1

        self._ch_list = ['CH1', 'CH2', 'CH3', 'CH4']
        # Output channels added to both the module for snapshots and internal Trigger Sources for the DDG HAL...
        #!!!NOTE!!! The submodules are added to the parent to keep things simple on the QCoDeS end.
        #TODO: Look into changing this? Perhaps submodules can be added as Instrument objects instead of channels? Could an AWG object be a channel and have its own sub-channel objects?
        for ch_ind, ch_name in enumerate(self._ch_list):
            cur_channel = AWG_TaborP2584M_channel(self.parent, ch_name, ch_ind+1)
            self.parent.add_submodule(ch_name, cur_channel)

    @property
    def SampleRate(self):
        return self.parent.sample_rate()
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self.parent.sample_rate(frequency_hertz)

    @property
    def TriggerInputEdge(self):
        return self._trigger_edge
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self._trigger_edge = pol

    def num_supported_markers(self, channel_name):
        return 2

    def _get_channel_output(self, identifier):
        if identifier in self.parent.submodules:
            return self.parent.submodules[identifier]  #!!!NOTE: Note from above in the initialiser regarding the parent storing the AWG channel submodule
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
        self.parent._set_cmd(':INST:CHAN', chan_ind+1)
        #Delete and Define segment (noting that it's taken as 1 or 2 for channels 1|3 and 2|4 respectively...)
        seg_id = int(chan_ind % 2 + 1)
        self.parent._set_cmd('TRAC:DEL', seg_id)
        self.parent._send_cmd(f':TRAC:DEF {seg_id}, {cur_data.size}')
        
        # self._send_data_to_memory(seg_id, cur_data)
        self._send_data_to_memory(seg_id, cur_data, mkr_data)
        self._program_task_table(chan_ind+1, [AWG_TaborP2584M_task(seg_id, 1, 1, cur_chnl.trig_src())])
        
        self.parent._set_cmd('FUNC:MODE', 'TASK')

    def _program_task_table(self, channel_index, tasks):
        #Select current channel
        self.parent._set_cmd(':INST:CHAN', channel_index)
        #Allocate a set number of rows for the task table
        self.parent._set_cmd(':TASK:COMP:LENG', len(tasks))

        #Check that there is at most one trigger source and record it if applicable
        cur_trig_src = ''
        for cur_task in tasks:
            if cur_task.trig_src != '' and cur_task.trig_src != 'NONE':
                assert cur_trig_src == '' or cur_trig_src == cur_task.trig_src, "Cannot have multiple trigger sources for a given Tabor channel input."
                cur_trig_src = cur_task.trig_src

        for task_ind, cur_task in enumerate(tasks):
            self.parent._set_cmd(':TASK:COMP:SEL', task_ind + 1)
            #Set the task to be solitary (i.e. not a part of an internal sequence inside Tabor...)
            self.parent._send_cmd(':TASK:COMP:TYPE SING')
            #Set task parameters...
            self.parent._set_cmd(':TASK:COMP:LOOP', cur_task.num_cycles)
            self.parent._set_cmd(':TASK:COMP:SEGM', cur_task.seg_num)
            self.parent._set_cmd(':TASK:COMP:NEXT1', cur_task.next_task_ind)
            self.parent._set_cmd(':TASK:COMP:ENAB', cur_task.trig_src)
      
        #Download task table to channel
        self.parent._send_cmd(':TASK:COMP:WRIT')
        # self._set_cmd(':FUNC:MODE', 'TASK')

        #Check for errors...
        resp = self.parent._get_cmd(':SYST:ERR?')
        resp = resp.rstrip()
        assert resp.startswith('0'), 'ERROR: "{0}" after writing task table'.format(resp)

        #Enable triggers if applicable to this channel
        if cur_trig_src != '':
            #Select current channel (just in case)
            self.parent._set_cmd(':INST:CHAN', channel_index)
            #Enable triggers...
            self.parent._set_cmd(':TRIG:SEL', cur_trig_src)
            self.parent._set_cmd(':TRIG:STAT', 'ON')
        
    def _send_data_to_memory(self, seg_ind, wfm_data_normalised, mkr_data):
        #Condition the data
        final_data = (wfm_data_normalised * self._half_dac + self._half_dac).astype(self._data_type)
        #Select the segment
        self.parent._set_cmd(':TRAC:SEL', seg_ind)
        #Increase the timeout before writing binary-data:
        self.parent._inst.timeout = 30000
        #Send the binary-data with *OPC? added to the beginning of its prefix.
        # self._inst.write_binary_data('*OPC?; :TRAC:DATA', final_data)
        #!!!There seems to be some API changes that basically breaks their code - removing OPC for now...
        self.parent._inst.write_binary_data(':TRAC:DATA', final_data)
        #Read the response to the *OPC? query that was added to the prefix of the binary data
        #resp = self._inst.()
        #Set normal timeout
        self.parent._inst.timeout = 10000
        #Check for errors...
        resp = self.parent._inst.send_scpi_query(':SYST:ERR?')
        resp = resp.rstrip()
        assert resp.startswith('0'), 'ERROR: "{0}" after writing binary values'.format(resp)

        total_mkrs = np.array([])
        for mkr_ind, cur_mkr_data in enumerate(mkr_data):
            if mkr_data[mkr_ind].size == 0:
                continue
            # self._set_cmd(':MARK:SEL', mkr_ind+1)

            if self._data_type == np.uint16:
                cur_mkrs = mkr_data[mkr_ind][::4].astype(np.uint8)
            else:
                cur_mkrs = mkr_data[mkr_ind][::8].astype(np.uint8)
            #Bit 1 for MKR1, Bit 2 for MKR2 - must perform bit-shifts if it's MKR3 or MKR4, but these outputs are not present in this module...
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
            #Increase the timeout before writing binary-data:
            self.parent._inst.timeout = 30000
            # Send the binary-data with *OPC? added to the beginning of its prefix.
            self.parent._inst.write_binary_data(':MARK:DATA', total_mkrs)
            # Read the response to the *OPC? query that was added to the prefix of the binary data
            #resp = inst.read()
            # Set normal timeout
            self.parent._inst.timeout = 10000
            resp = self.parent._get_cmd(':SYST:ERR?')
            resp = resp.rstrip()
            assert resp.startswith('0'), 'ERROR: "{0}" after writing binary values'.format(resp)

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

        self._subInst_AWG = TaborP2584M_AWG(self)

        
        ##################################################################
        ##########################INITIALISE ADC##########################
        # Setup the digitizer in two-channels mode
        self._set_cmd(':DIG:MODE', 'DUAL')
        self._set_cmd(':DIG:FREQ', 2.0e9)

        # Set Trigger level to 0.2V
        self._set_cmd(':DIG:TRIG:LEV1', 0.7)

        # Enable capturing data from channel 1
        self._set_cmd(':DIG:CHAN:SEL', 1)
        self._set_cmd(':DIG:CHAN:STATE', 'ENAB')
        # Select the external-trigger as start-capturing trigger:
        self._inst.send_scpi_cmd(':DIG:TRIG:SOURCE EXT')

        # Enable capturing data from channel 2
        self._inst.send_scpi_cmd(':DIG:CHAN:SEL 2')
        self._inst.send_scpi_cmd(':DIG:CHAN:STATE ENAB')
        # Select the external-trigger as start-capturing trigger:
        self._inst.send_scpi_cmd(':DIG:TRIG:SOURCE EXT')

        # Allocate four frames of 4800 samples
        numframes, framelen = 4, 4800
        cmd = ':DIG:ACQuire:FRAM:DEF {0},{1}'.format(numframes, framelen)
        self._inst.send_scpi_cmd(cmd)

        # Select the frames for the capturing 
        # (all the four frames in this example)
        capture_first, capture_count = 1, numframes
        cmd = ":DIG:ACQuire:FRAM:CAPT {0},{1}".format(capture_first, capture_count)
        self._inst.send_scpi_cmd(cmd)

        # Clean memory 
        self._inst.send_scpi_cmd(':DIG:ACQ:ZERO:ALL')

        resp = self._inst.send_scpi_query(':SYST:ERR?')
        print(resp)
        time.sleep(1)

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

    def get_AWG(self):
        return self._subInst_AWG

    def get_data(self):
        ##########Setup Digitizer
        # Stop the digitizer's capturing machine (to be on the safe side)
        self._inst.send_scpi_cmd(':DIG:INIT OFF')

        # Start the digitizer's capturing machine
        self._inst.send_scpi_cmd(':DIG:INIT ON')

        print('Waiting for status done bit ..')
        loopcount = 0
        done = 0
        while done == 0:
            resp = self._inst.send_scpi_query(":DIG:ACQuire:FRAM:STATus?")
            resp_items = resp.split(',')
            done = int(resp_items[1])
            print("{0}. {1}".format(done, resp_items))
            loopcount += 1
            if loopcount == 10:
                print("No Trigger was detected")
                done = 1  
        print("Capture Done")

        # Stop the digitizer's capturing machine (to be on the safe side)
        self._inst.send_scpi_cmd(':DIG:INIT OFF')

        resp = self._inst.send_scpi_query(':SYST:ERR?')
        print(resp)
        time.sleep(2)


        ################## Read all frames from Memory
        # Choose which frames to read (all in this example)
        self._inst.send_scpi_cmd(':DIG:DATA:SEL ALL')

        # Choose what to read 
        # (only the frame-data without the header in this example)
        self._inst.send_scpi_cmd(':DIG:DATA:TYPE FRAM')

        # Get the total data size (in bytes)
        resp = self._inst.send_scpi_query(':DIG:DATA:SIZE?')
        num_bytes = np.uint32(resp)
        print('Total size in bytes: ' + resp)
        print()

        # Read the data that was captured by channel 1:
        self._inst.send_scpi_cmd(':DIG:CHAN:SEL 1')

        wavlen = num_bytes // 2

        wav1 = np.zeros(wavlen, dtype=np.uint16)

        rc = self._inst.read_binary_data(':DIG:DATA:READ?', wav1, num_bytes)

        # Read the data that was captured by channel 2:
        self._inst.send_scpi_cmd(':DIG:CHAN:SEL 2')

        wavlen = num_bytes // 2

        wav2 = np.zeros(wavlen, dtype=np.uint16)

        rc = self._inst.read_binary_data(':DIG:DATA:READ?', wav2, num_bytes)

        resp = self._inst.send_scpi_query(':SYST:ERR?')
        print(resp)


        return (wav1, wav2)
