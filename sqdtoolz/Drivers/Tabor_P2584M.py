from typing import List, Sequence, Dict, Union, Optional

import logging
from functools import partial

import os
import sys
import inspect
import clr
import ctypes
import numpy as np

from qcodes import Instrument, VisaInstrument, validators as vals
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.utils.validators import Validator
from broadbean.sequence import fs_schema, InvalidForgedSequenceError

import time

log = logging.getLogger(__name__)

##################################################
#
# SMALL HELPER FUNCTIONS
#


def _parse_string_response(input_str: str) -> str:
    """
    Remove quotation marks from string and return 'N/A'
    if the input is empty
    """
    output = input_str.replace('"', '')
    output = output if output else 'N/A'

    return output



class TaborAWGChannel(InstrumentChannel):
    """
    Class to hold a channel of the AWG.
    """

    def __init__(self,  parent: Instrument, name: str, channel: int) -> None:
        """
        Args:
            parent: The Instrument instance to which the channel is
                to be attached.
            name: The name used in the DataSet
            channel: The channel number, either 1 or 2.
        """
        self._parent = parent
        super().__init__(parent, name)

        self.channel = channel

        num_channels = self.root_instrument.num_channels

        fg = 'function generator'

        if channel not in list(range(1, num_channels+1)):
            raise ValueError('Illegal channel value.')

        self.add_parameter('state',
                           label='Channel {} state'.format(channel),
                           get_cmd=partial(self._get_state, channel),
                           set_cmd=partial(self._set_state, channel),
                           vals=vals.Ints(0, 1),
                           get_parser=int)

        self.add_parameter('amplitude',
                           label='Channel {} Vpp'.format(channel),
                           get_cmd=partial(self._get_vpp, channel),
                           set_cmd=partial(self._set_vpp, channel),
                           vals=vals.Numbers(0.05, 1.2),
                           get_parser=float)

        self.add_parameter('offset',
                           label='Channel {} Offset'.format(channel),
                           get_cmd=partial(self._get_off, channel),
                           set_cmd=partial(self._set_off, channel),
                           vals=vals.Numbers(-1.0, 1.0),
                           get_parser=float)

    def _get_state(self, channel):
        self._parent._TaborSendScpi(":INST:CHAN "+str(channel))
        return self._parent._TaborSendScpi(":OUTP?") == 'ON'
    def _set_state(self, channel, state : int):
        self._parent._TaborSendScpi(":INST:CHAN "+str(channel))
        self._parent._TaborSendScpi(":OUTP "+str(state))

    def _get_vpp(self, channel):
        self._parent._TaborSendScpi(":INST:CHAN "+str(channel))
        return float(self._parent._TaborSendScpi(':VOLT?'))
    def _set_vpp(self, channel, vpp_val : float):
        self._parent._TaborSendScpi(":INST:CHAN "+str(channel))
        self._parent._TaborSendScpi(":VOLT "+str(vpp_val))

    def _get_off(self, channel):
        self._parent._TaborSendScpi(":INST:CHAN "+str(channel))
        return float(self._parent._TaborSendScpi(':OFFS?'))
    def _set_off(self, channel, off_val : float):
        self._parent._TaborSendScpi(":INST:CHAN "+str(channel))
        self._parent._TaborSendScpi(":OFFS "+str(off_val))

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
        return self.state() == 1
    @Output.setter
    def Output(self, boolVal):
        if boolVal:
            self.state(1)
        else:
            self.state(0)



class P2584M(Instrument):
    """
    The QCoDeS driver for Tabor P2584M DAC/AWG module.
    """

    def __init__(self, name: str, pxi_chassis: int,  pxi_slot: int,
                 timeout: float=10, **kwargs) -> None:
        """
        Args:
            name: The name used internally by QCoDeS in the DataSet
            address: The VISA resource name of the instrument
            timeout: The VISA timeout time (in seconds)
        """

        self.num_channels = 4

        super().__init__(name, **kwargs)

        #Attempt to initialise the PXI DLL
        try:
            winpath = os.environ['WINDIR'] + "\\System32\\"
            clr.AddReference(winpath + R'TEPAdmin.dll')  
            from TaborElec.Proteus.CLI.Admin import CProteusAdmin
            from TaborElec.Proteus.CLI.Admin import IProteusInstrument
            tabor_admin = CProteusAdmin(self._TaborOnLoggerEvent)        
        except Exception as e: 
            print("Failed to load TaborElec TEPAdmin DLL")
            print(e)
            return
        #Attempt to get the device slot
        try:
            rc = tabor_admin.Open()
            self._TaborValidate(rc,__name__,inspect.currentframe().f_back.f_lineno)
            slotIds = tabor_admin.GetSlotIds()
            slotId = -1
            for i in range(0,slotIds.Length,1):
                slotInfo = tabor_admin.GetSlotInfo(slotIds[i])
                #Their library inserts random (nonexistent) assortment of their devices
                if slotInfo and not slotInfo.IsDummySlot and slotInfo.ChassisIndex == pxi_chassis and slotInfo.SlotNumber == pxi_slot:
                    slotId = pxi_slot
                    break
            assert slotId != -1, "Could not find device on chassis {0} slot {1}".format(pxi_chassis, pxi_slot)
            slotId = np.uint32(slotId)
        except Exception as e: 
            print("Failed to find Proteus P2584M on PXI rack")
            print(e)
        #Open a Tabor instrument
        self._tabor_inst = tabor_admin.OpenInstrument(slotId) 
        if not self._tabor_inst:
            print("Failed to Open instrument with slot-Id {0}".format(slotId))
            print("\n")
        #Initialise Tabor-related parameters
        self._tabor_instId = self._tabor_inst.InstrId
        self._tabor_admin = tabor_admin
        self._tabor_maxScpiResponse = 65535

        #Add global instrument parameters
        self.add_parameter('sample_rate',
                           label='Sample Rate',
                           get_cmd=partial(self._get_freq),
                           set_cmd=partial(self._set_freq),
                           get_parser=float)

        #Add the output channel modules
        chanlist = ChannelList(self, 'Channels', TaborAWGChannel, snapshotable=False)
        for ch_num in range(1, self.num_channels+1):
            ch_name = 'ch{}'.format(ch_num)
            channel = TaborAWGChannel(self, ch_name, ch_num)
            self.add_submodule(ch_name, channel)
            if self.num_channels > 2:
                chanlist.append(channel)
        chanlist.lock()
        self.add_submodule('channels', chanlist)

        #TODO: Setup trigger sources to be a parameter...
        self._TaborSendScpi(":TRIG:SOUR:ENAB TRG1")
        for cur_ch in [1,2,3,4]:
            self._TaborSendScpi(":INST:CHAN " + str(cur_ch))
            self._TaborSendScpi(":TRIG:SOUR:ENAB TRG1") # Set tigger enable signal to TRIG1 (CH specific)
            self._TaborSendScpi(":TRIG:SEL EXT1") # Select trigger for programming (CH specific)
            self._TaborSendScpi(":TRIG:LEV 0") # Set trigger level
            self._TaborSendScpi(":TRIG:COUN 1") # Set number of waveform cycles (1) to generate (CH specific)
            self._TaborSendScpi(":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
            # trig_lev = getSclkTrigLev(inst)

            # self._TaborSendScpi(":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)
            self._TaborSendScpi(":TRIG:STAT ON") # Enable trigger state (CH specific)
            self._TaborSendScpi(":INIT:CONT OFF") # Enable trigger mode (CH specific)

    def _TaborOnLoggerEvent(self,sender,e):
        print(e.Message.Trim())
        if (e.Level <= LogLevel.Warning):
            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            print(e.Message.Trim())
            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    def _TaborValidate(self,rc,condExpr,funcName = "",lineNumber = 0):
        '''
        A return-value results checker when calling functions in the Tabor API
        '''
        cond = (rc==0)
        if (False == cond):
            errMsg = "Tabor API Assertion \"{0}\" Failed at line {1} of {2}.".format(rc,lineNumber,funcName)
            raise Exception(errMsg)

    def _TaborSendScpi(self,command: str):
        '''
        Sends SCPI command to the Tabor instrument. Note that a new-line will be automatically added to the string before it is sent.
        If no exceptions were found, the return value is the response string (if applicable to the SCPI command).
        '''
        try:
            command = command + "\n"
            inBinDat = bytearray(command, "utf8")
            inBinDatSz = np.uint64(len(inBinDat))
            outBinDatSz = np.uint64([self._tabor_maxScpiResponse])
            outBinDat = bytearray(outBinDatSz[0])
            res = self._tabor_inst.ProcessScpi(inBinDat, inBinDatSz, outBinDat, outBinDatSz)
            if (res.ErrCode != 0):
                print("Error {0} ".format(res.ErrCode))
            return res.RespStr
        except Exception as e: 
            print(e)
            return res

    def _TaborUploadWaveformSegment(self, channel_num, segNum, voltVals, bank_no):
        '''
        channel_num - Just there for reference to scale the values.
        segNum      - Unique integer Waveform segment ID. Note that the channel pairs 1&2 and 3&4 share the same blocks of memory (but they are separate).
        voltVals    - Numpy array of raw voltage values
        bank_no     - If using channels 1 and 2, set this to 1. If using channels 3 and 4, set this to 3. Or just set it to the intended channel destination while
                      being mindful of the segNum for the current bank of memory...
        '''
        #Set to channel number and get amplitude
        cur_amp = 0.5*self.channels[channel_num-1].amplitude()
        voltVals = np.clip(voltVals, -cur_amp, cur_amp)
        #Bank number is 1 or 3 - i.e. for 1|2 or 3|4 as it seems to split the memory banks...
        self._TaborSendScpi(":INST:CHAN " + str(bank_no))
        #Convert floats into 16-bit integers (assuming zero-offset)...
        #TODO: Check for offset correction
        bin_dat = voltVals*32768.0/cur_amp + 32768.0
        bin_dat = bin_dat.astype(dtype=np.uint16)
        bin_dat = bin_dat.view(dtype=np.uint8)
        seg_len = int(len(bin_dat) / 2)

        self._TaborSendScpi(":TRAC:DEL " + str(segNum))
        self._TaborSendScpi(":TRACe:DEF {0},{1}".format(segNum, seg_len))
        self._TaborSendScpi(":TRACe:SEL {0}".format(segNum))
        inDatLength = len(bin_dat)
        inDatOffset = 0
        res = self._tabor_inst.WriteBinaryData(":TRAC:DATA 0,#", bin_dat, inDatLength, inDatOffset)
        
        if (res.ErrCode != 0):
            print("Error {0} ".format(res.ErrCode))
        else:
            if (len(res.RespStr) > 0):
                print("{0}".format(res.RespStr))

    def _TaborAddTaskSingle(self, chan_num, task_num, wfm_segment, next_task_num, num_loops = 1):
        #task_num must be 1 or greater...
        self._TaborSendScpi(":INST:CHAN " + str(chan_num))
        self._TaborSendScpi(":TASK:SEL " + str(task_num))
        self._TaborSendScpi(":TASK:DEF:TYPE SING")
        self._TaborSendScpi(":TASK:DEF:LOOP " + str(num_loops))
        self._TaborSendScpi(":TASK:DEF:SEQ 1")
        self._TaborSendScpi(":TASK:DEF:SEGM " + str(wfm_segment))
        self._TaborSendScpi(":TASK:DEF:IDLE FIRS")
        self._TaborSendScpi(":TASK:DEF:IDLE:DC 0")
        self._TaborSendScpi(":TASK:DEF:ENAB TRG1")   #No triggers for now; TODO: MAKE THIS GENERAL FOR TRIGGER SOURCES
        self._TaborSendScpi(":TASK:DEF:ABOR NONE")   #No exit triggers for now
        self._TaborSendScpi(":TASK:DEF:JUMP EVEN")   #Finish current loop before going to next loop (not relevant without external triggers anyway)
        self._TaborSendScpi(":TASK:DEF:DEST NEXT")   #Jump to NEXT1 on finishing current task
        self._TaborSendScpi(":TASK:DEF:NEXT1 " + str(next_task_num))
        self._TaborSendScpi(":TASK:DEF:NEXT2 0")     #No conditional branching, so NEXT2 is just set to 0

    def _TaborCommitToTaskMode(self, chan_num):
        self._TaborSendScpi(":INST:CHAN " + str(chan_num))
        self._TaborSendScpi(":SOUR:FUNC:MODE TASK")

    def reset_all(self):
        self._TaborSendScpi("*RST")
        # delete all segments in RAM
        self._TaborSendScpi(":TRAC:DEL:ALL")

    def _get_freq(self):
        return float(self._TaborSendScpi(":FREQ:RAST?"))
    def _set_freq(self, freq : float):
        self._TaborSendScpi(":FREQ:RAST "+str(freq))

    def load_sequence_direct_limited(self, waveforms, markers=None):
        '''
        For each channel upload the entire waveform as a segment and load it into the relevant channel
        waveforms  : list of waveforms sorted by channels.
                     number of data points must be divisible by 32 
        markers    : list of markers by channel
                     not yet being written since there are no connectors for marker ports
        '''        
        num_channels_wf = len(waveforms)
        assert num_channels_wf == self.num_channels, \
                "Sequence has a different number of channels ({0}) than the device ({1}).".format(num_channels_wf, self.num_channels)

        # load sequence for each channel
        for i in range(num_channels_wf):
            self.channels[i].state(0)
            channel_num = i+1
            channel_wf = waveforms[i]
            if(channel_wf.shape[0] == 1): 
                channel_wf = channel_wf[0]

            # bank_num = i+1 if channel_num < 3 else i-1 # should be 1, 2 for ch 1, 2 and 1, 2 for ch 3, 4
            bank_num = channel_num
            seg_num = channel_num
            # for now naming each bank same as channel
            self._TaborUploadWaveformSegment(channel_num, seg_num, channel_wf, bank_num)
            # do these need to be in different loops? 
            self._TaborAddTaskSingle(channel_num, task_num=1, wfm_segment=seg_num, next_task_num=1, num_loops = 1)
            # next_task_num 1 bec comiting each time
            self._TaborCommitToTaskMode(channel_num)
            self.channels[i].state(1)

    def load_sequence_direct(self, waveforms, markers=None):
        '''
        For each channel upload the entire waveform as a segment and load it into the relevant channel
        waveforms  : list of waveforms sorted by channels.
                     the number of points should be a multiple of 32, if this is not the case padding will be added
                     to not add padding see other versions of load_sequence_direct
        markers    : list of markers by channel
                     not yet being written since there are no connectors for marker ports
        '''
        num_channels_wf = len(waveforms)
        assert num_channels_wf == self.num_channels, \
                "Sequance has a different number of channels ({0}) than the device ({1}).".format(num_channels_wf, self.num_channels)
        
        # two banks need to be indexed separately
        seg_num_1 = 1
        seg_num_2 = 1
        # load sequence for each channel
        for i in range(num_channels_wf):
            self.channels[i].state(0)
            channel_num = i+1
            channel_wf = waveforms[i]
            if(channel_wf.shape[0] == 1): 
                channel_wf = channel_wf[0]
            
            # bank_num = i+1 if channel_num < 3 else i-1 # should be 1, 2 for ch 1, 2 and 1, 2 for ch 3, 4
            bank_num =  bank_num = 1 if channel_num < 3 else 3
            seg_num = seg_num_1 if bank_num==1 else seg_num_2
            
            # smallest devisions are 32 points (see manual)
            div = 32
            if(len(channel_wf)%div !=0):
                log.warning("The waveform length is not a multiple of {0}, adding padding".format(div))
                seg_wf = np.zeros((len(channel_wf)//div)*div+div)
                seg_wf[0:len(channel_wf)] = channel_wf
                channel_wf = seg_wf

            # for now naming each bank same as channel
            self._TaborUploadWaveformSegment(channel_num, seg_num, channel_wf, bank_num)
            self._TaborAddTaskSingle(channel_num, task_num=1, wfm_segment=seg_num, next_task_num=1, num_loops = 1)
            # next_task_num is 1 because commiting each time
            self._TaborCommitToTaskMode(channel_num)
            self.channels[i].state(1)
            if(bank_num==1): 
                seg_num_1+=1
            else: 
                seg_num_2+=1
 
    def load_sequence_direct_segmented(self, waveforms, markers=None):
        '''
        For each channel upload the entire waveform as a segment and load it.
        This version of the function will load the segment in 2048 data point blocks as a work around for 
        the error thrown by the AWG when loading more.  This is not neccessary and depreciated

        waveforms  : list of waveforms sorted by channels.
        markers    : list of markers by channel
                     not yet being written since there are no connectors for marker ports
        '''
        num_channels_wf = len(waveforms)
        assert num_channels_wf == self.num_channels, \
                "Sequance has a different number of channels ({0}) than the device ({1}).".format(num_channels_wf, self.num_channels)
        
        # load sequence for each channel
        seg_num_1 = 1
        seg_num_2 = 1

        for i in range(num_channels_wf):
            channel_num = i+1
            channel_wf = waveforms[i]
            if(channel_wf.shape[0] == 1): 
                channel_wf = channel_wf[0]
            
            bank_num =  bank_num = 1 if channel_num < 3 else 3
            if(len(channel_wf)>2048):
                log.warning("Waveform exceeds length.")
                for j in range(int(np.ceil(len(channel_wf)/2048))):
                    seg_num = seg_num_1 if bank_num==1 else seg_num_2
                    # pad any left overs with 0s. Why is this necessary even though del in uploadWaveformSegment
                    # because if set one segment length can't override it with larger length
                    # whatever else is in that last part of the segment will stay so the other option is to zero the segment before writing to it
                    seg_wf = np.zeros(2048)
                    seg_wf[0:len(channel_wf[j*2048:j*2048+2048])] = channel_wf[j*2048:j*2048+2048]
                    self._TaborUploadWaveformSegment(channel_num, seg_num, seg_wf, bank_num)
                    self._TaborAddTaskSingle(channel_num, task_num=j, wfm_segment=seg_num, next_task_num=(j+1)%4, num_loops = 1)
                    if(bank_num==1): 
                        seg_num_1+=1
                    else: 
                        seg_num_2+=1

            else:
                seg_num = seg_num_1 if bank_num==1 else seg_num_2
                # bank_num = i+1 if channel_num < 3 else i-1 # should be 1, 2 for ch 1, 2 and 1, 2 for ch 3, 4
                # for now naming each bank same as channel
                seg_wf = np.zeros((len(channel_wf)//32)*32+32)
                seg_wf[0:len(channel_wf)] = channel_wf[:]
                self._TaborUploadWaveformSegment(channel_num, seg_num, seg_wf, bank_num)
                self._TaborAddTaskSingle(channel_num, task_num=1, wfm_segment=seg_num, next_task_num=1, num_loops = 1)
                # next_task_num 1 beausec commiting each time
                if(bank_num==1): 
                    seg_num_1+=1
                else: 
                    seg_num_2+=1
            self._TaborCommitToTaskMode(channel_num)
            self.channels[i].state(1)  
                 
    
    def write_raw(self, cmd):
        '''  
        Wrapper for _TaborSendScpi function to accommodate for required overrides of write_raw
        cmd     : string command to sent to awg
        
        '''
        self._TaborSendScpi(cmd)

    def ask_raw(self, cmd):
        '''  
        Wrapper for _TaborSendScpi function to accommodate for required overrides of ask_raw
        cmd     : string command to sent to awg
        returns:  response from the device

        
        '''
        return self._TaborSendScpi(cmd)

    @property
    def SampleRate(self):
        return self.sample_rate()
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self.sample_rate(frequency_hertz)

    @property
    def TriggerInputEdge(self):
        return 1#self._trigger_edge #TODO: Look into the actual trigger edge for this instrument
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        pass
        #self._trigger_edge = pol

    def supports_markers(self, channel_name):
        return True

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]
        else:
            return None

    def program_channel(self, chan_id, wfm_data, mkr_data = np.array([])):       
        #TODO: Check the state and put that instead of just turning it off and then on
        if chan_id == 'ch1':
            self.channels[0].state(0)
            self._TaborUploadWaveformSegment(1, 1, wfm_data, 1)
            self._TaborAddTaskSingle(1, task_num=1, wfm_segment=1, next_task_num=1, num_loops = 1)
            self._TaborCommitToTaskMode(1)
            self.channels[0].state(1)
        elif chan_id == 'ch2':
            self.channels[1].state(0)
            self._TaborUploadWaveformSegment(2, 2, wfm_data, 1)
            self._TaborAddTaskSingle(2, task_num=1, wfm_segment=2, next_task_num=1, num_loops = 1)
            self._TaborCommitToTaskMode(2)
            self.channels[1].state(1)
        elif chan_id == 'ch3':
            self.channels[2].state(0)
            self._TaborUploadWaveformSegment(3, 1, wfm_data, 3)
            self._TaborAddTaskSingle(3, task_num=1, wfm_segment=1, next_task_num=1, num_loops = 1)
            self._TaborCommitToTaskMode(3)
            self.channels[2].state(1)
        elif chan_id == 'ch4':
            self.channels[3].state(0)
            self._TaborUploadWaveformSegment(4, 2, wfm_data, 3)
            self._TaborAddTaskSingle(4, task_num=1, wfm_segment=2, next_task_num=1, num_loops = 1)
            self._TaborCommitToTaskMode(4)
            self.channels[3].state(1)

















    def run(self):
        ''' 
        Contracted function that's requried in all awgs.
        Start generating output. Not sure if this is neccessary or if it can be empty
            for this awg.
        '''
        # Took out channels.state(1) from load_sequence_direct and put it here
        # alternatively a wrapper for play? I think this makes sense as in other awg also equivlent to run button
        for i in range(self.num_channels):
            self.channels[i].state(1)


    def close(self):
        rc = self._tabor_admin.CloseInstrument(self._tabor_instId)
        self._TaborValidate(rc,__name__,inspect.currentframe().f_back.f_lineno)
        rc = self._tabor_admin.Close()
        self._TaborValidate(rc,__name__,inspect.currentframe().f_back.f_lineno)
        super.close()


    def force_triggerA(self):
        """
        Force a trigger A event
        """
        self.write('TRIGger:IMMediate ATRigger')

    def force_triggerB(self):
        """
        Force a trigger B event
        """
        self.write('TRIGger:IMMediate BTRigger')

    def wait_for_operation_to_complete(self):
        """
        Waits for the latest issued overlapping command to finish
        """
        self.ask('*OPC?')

    def play(self, wait_for_running: bool=True, timeout: float=10) -> None:
        """
        Run the AWG/Func. Gen. This command is equivalent to pressing the
        play button on the front panel.

        Args:
            wait_for_running: If True, this command is blocking while the
                instrument is getting ready to play
            timeout: The maximal time to wait for the instrument to play.
                Raises an exception is this time is reached.
        """
        # There is no play button on the front pannel?
        # Yes this function seems to come from the code for another AWG as the 'AWGControl:RUN' command isn't
        # in the list of commands in the programming manual. Might be a good idea to through a warning if that's the case
        # either way play isn't required, run is.
        log.warning('Instrument {} has not overwritten a play method. Nothing was done.'.format(type(self).__name__)) 
        # self.write('AWGControl:RUN')
        # if wait_for_running:
        #     start_time = time.perf_counter()
        #     running = False
        #     while not running:
        #         time.sleep(0.1)
        #         running = self.run_state() in ('Running',
        #                                        'Waiting for trigger')
        #         waited_for = start_time - time.perf_counter()
        #         if waited_for > timeout:
        #             raise RuntimeError(f'Reached timeout ({timeout} s) '
        #                                'while waiting for instrument to play.'
        #                                ' Perhaps some waveform or sequence is'
        #                                ' corrupt?')

    def stop(self) -> None:
        """
        Stop the output of the instrument. This command is equivalent to
        pressing the stop button on the front panel.
        """
        # Like play, this is not a command for this awg.
        # There also doesn't seem to be equivlent commands
        # self.write('AWGControl:STOP')
        log.info('Setting channel states to 0.'.format(type(self).__name__))
        for i in range(self.num_channels):
            self.channels[i].state(0)

    @property
    def sequenceList(self) -> List[str]:
        """
        Return the sequence list as a list of strings
        """
        # There is no SLISt:LIST command, so we do it slightly differently
        N = int(self.ask("SLISt:SIZE?"))
        slist = []
        for n in range(1, N+1):
            resp = self.ask("SLISt:NAME? {}".format(n))
            resp = resp.strip()
            resp = resp.replace('"', '')
            slist.append(resp)

        return slist

    @property
    def waveformList(self) -> List[str]:
        """
        Return the waveform list as a list of strings
        """
        respstr = self.ask("WLISt:LIST?")
        respstr = respstr.strip()
        respstr = respstr.replace('"', '')
        resp = respstr.split(',')

        return resp

    def delete_sequence_from_list(self, seqname: str) -> None:
        """
        Delete the specified sequence from the sequence list

        Args:
            seqname: The name of the sequence (as it appears in the sequence
                list, not the file name) to delete
        """
        self.write(f'SLISt:SEQuence:DELete "{seqname}"')

    def clearSequenceList(self):
        """
        Clear the sequence list
        """
        log.warning('Instrument {} has not implimented clearSequenceList.'.format(type(self).__name__)) 
        # this is for another awg, commenting for clarity
        self.write('SLISt:SEQuence:DELete ALL')

    def clearWaveformList(self):
        """
        Clear the waveform list
        """
        log.warning('Instrument {} has not implimented clearWaveformList.'.format(type(self).__name__)) 
        # this is for another awg, commenting for clarity
        self.write('WLISt:WAVeform:DELete ALL')

    def clearSegmentList(self):
        '''
        Clear all segments in memory
        '''
        self.write(":TRAC:DEL:ALL")

    def get_error(self):
        ''' 
        Asks for errors and returns the response. 
        '''
        return self._TaborSendScpi(":SYST:ERR?")
        

