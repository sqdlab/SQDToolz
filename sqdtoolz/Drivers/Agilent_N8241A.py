from ctypes import *
import logging
import os
import numpy as np
import re

from qcodes import Instrument, Parameter, InstrumentChannel
from qcodes.utils import validators as vals

from sqdtoolz.Drivers.Dependencies.Agilent_N8241A_constants_python3 import *

def basestring(s):
    return bytes(str(s), encoding='ascii')

ViUInt32 = c_uint
ViInt32 = c_int
ViUInt16 = c_ushort
ViInt16 = c_short
ViUInt8 = c_ubyte
ViInt8 = c_byte
ViChar = c_char
ViPChar = c_char_p
ViByte = c_ubyte
ViReal32 = c_float
ViReal64 = c_double
ViAddr = c_void_p

ViString = ViPChar
ViRsrc = ViString
ViBoolean = ViUInt16
ViStatus = ViInt32
ViVersion = ViUInt32
ViObject = ViUInt32
ViSession = ViObject
ViAttr = ViUInt32

VI_SUCCESS = 0
VI_NULL = 0
VI_TRUE = 1
VI_FALSE = 0

TRIGGER_MAP = {'External' : AGN6030A_VAL_EXTERNAL,
               'Software' : AGN6030A_VAL_SOFTWARE_TRIG,
               'No Trigger' : AGN6030A_VAL_NOTRIG_FLAG,
               'Software 1 Flag' : AGN6030A_VAL_SOFTWARE1_FLAG,
               'Software 2 Flag' : AGN6030A_VAL_SOFTWARE2_FLAG,
               'Software 3 Flag' : AGN6030A_VAL_SOFTWARE3_FLAG,
               'External 2 Flag' : AGN6030A_VAL_EXTERNAL2_FLAG,
               'External 3 Flag' : AGN6030A_VAL_EXTERNAL3_FLAG,
               'External 4 Flag' : AGN6030A_VAL_EXTERNAL4_FLAG,
               'LXI Trig1 Flag' : AGN6030A_VAL_LXI_TRIG1_FLAG}

MARKER_MAP = {"Off" : AGN6030A_VAL_MARKER_OFF,
              "Software Marker" : AGN6030A_VAL_MARKER_SOFTWARE,
              "Channel 1 Marker 1" : AGN6030A_VAL_MARKER_CH1_M1,
              "Channel 1 Marker 2" : AGN6030A_VAL_MARKER_CH1_M2,
              "Channel 2 Marker 1" : AGN6030A_VAL_MARKER_CH2_M1,
              "Channel 2 Marker 2" : AGN6030A_VAL_MARKER_CH2_M2,
              "Waveform Start Marker" : AGN6030A_VAL_MARKER_WFM_START,
              "Waveform Repeat Marker" : AGN6030A_VAL_MARKER_WFM_REP,
              "Waveform Gate Marker" : AGN6030A_VAL_MARKER_WFM_GATE,
              "Sequence Start Marker" : AGN6030A_VAL_MARKER_SEQ_START,
              "Sequence Repeat Marker" : AGN6030A_VAL_MARKER_SEQ_REP,
              "Sequence Gate Marker" : AGN6030A_VAL_MARKER_SEQ_GATE,
              "Scenario Repeat Marker" : AGN6030A_VAL_MARKER_SCENARIO_REP,
              "Hardware Trigger 1" : AGN6030A_VAL_MARKER_HDWR_TRIG_1,
              "Hardware Trigger 2" : AGN6030A_VAL_MARKER_HDWR_TRIG_2,
              "Hardware Trigger 3" : AGN6030A_VAL_MARKER_HDWR_TRIG_3,
              "Hardware Trigger 4" : AGN6030A_VAL_MARKER_HDWR_TRIG_4,
              "Hardware Trigger Auxiliary" : AGN6030A_VAL_MARKER_HDWR_AUX_TRIG,
              "Software 2 Marker" : AGN6030A_VAL_MARKER_SOFTWARE_2,
              "Software 3 Marker" : AGN6030A_VAL_MARKER_SOFTWARE_3,
              "Software 4 Marker" : AGN6030A_VAL_MARKER_SOFTWARE_4}

class AGN_Parameter(Parameter):
    """attribute of all types, except for the
        ViSession attribute. Use get_attribute_ViSession instead.
        
        Parameters:
        -----------
        attribute: Integer
            ID of the attribute
        dtype: type
            The expected type of the attribute value. Possible types are:
                bool, int, float, basestring
            basestring requires the additional parameter `str_size`.
        
        Optional Parameters:
        --------------------
        ch: Integer
            Some attributes require a specific channel number
        str_size: Integer
            Number of bytes to read from the instrument. This parameter is
            required if dtype is basestring"""
    def __init__(self, name, attribute, dtype, ch='', str_size=None, **kwargs) -> None:
        super(AGN_Parameter, self).__init__(name, **kwargs)
        self.attribute = attribute
        self.dtype = dtype
        self.ch = ch
        self.str_size = str_size
        self._dll = self._instrument._dll
        self._handle = self._instrument._handle
        self._status_handle = self._instrument._status_handle
        
        if kwargs.get('set_cmd', True) is False:
            self.set = self._set_error

    def get_raw(self):
        ch_str = basestring(self.ch)
        
        if self.dtype is bool:
            value = ViBoolean(0)
            rc = self._dll.AGN6030A_GetAttributeViBoolean(
                self._handle, ViString(ch_str), ViAttr(self.attribute), byref(value))
            self._status_handle(rc)
        elif self.dtype is int:
            value = ViInt32(0)
            rc = self._dll.AGN6030A_GetAttributeViInt32(
                self._handle, ViString(ch_str), ViAttr(self.attribute), byref(value))
            self._status_handle(rc)
        elif self.dtype is float:
            value = ViReal64(0)
            rc = self._dll.AGN6030A_GetAttributeViReal64(
                self._handle, ViString(ch_str), ViAttr(self.attribute), byref(value))
            self._status_handle(rc)
        elif self.dtype is bytes:
            if self.str_size is None:
                raise TypeError("If dtype is bytes, optional argument `str_size` "
                                "is required.")

            value = create_string_buffer(self.str_size + 1) # Including the NULL termination
            rc = self._dll.AGN6030A_GetAttributeViString(
                self._handle, ViString(ch_str), ViAttr(self.attribute),
                ViInt32(self.str_size), value)
            self._status_handle(rc)
        else:
            raise TypeError("`value` type {0} not supported".format(str(dtype)))
        
        return value.value

    def set_raw(self, value):
        '''
        Set the value of an attribute of all types, except for the
        ViSession attribute. Use set_attribute_ViSession instead.
        
        Parameters:
        -----------
        attribute: Integer
            ID of the attribute to be set
        value: bool, int, float, basestring
            Set attribute to this value
            
        Optional Parameters:
        --------------------
        ch: Integer
            Some attributes require a specific channel number
            
        '''
        ch_str = basestring(self.ch)
        value = self.dtype(value)
        
        if isinstance(value, bool):
            rc = self._dll.AGN6030A_SetAttributeViBoolean(
                self._handle, ViString(ch_str), ViAttr(self.attribute), ViBoolean(value))
        # isinstance(value, long) is needed to support the constants from 
        # Agilent_N8241A_constants.py, which has some constants defined as L
        # because thats how it was written in the c header file. In principle, this
        # L is not needed, but removing it is tedious.
        elif isinstance(value, int):
            rc = self._dll.AGN6030A_SetAttributeViInt32(
                self._handle, ViString(ch_str), ViAttr(self.attribute), ViInt32(value))
        elif isinstance(value, float):
            rc = self._dll.AGN6030A_SetAttributeViReal64(
                self._handle, ViString(ch_str), ViAttr(self.attribute), ViReal64(value))
        elif isinstance(value, bytes):
            rc = self._dll.AGN6030A_SetAttributeViString(
                self._handle, ViString(ch_str), ViAttr(self.attribute), ViString(value))
        else:
            raise TypeError("`value` of {0} not supported".format(type(value)))
        
        self._status_handle(rc)

    def _set_error(self, *args, **kwargs):
        raise AttributeError('{} cannot be set'.format(self.name))

class AGN_Marker_Parameter(AGN_Parameter):
    
    def __init__(self, name, attribute, dtype, ch='', str_size=None, **kwargs) -> None:
        super().__init__(name, attribute, dtype, ch, str_size, **kwargs)
        
    def get_raw(self):
        getattr(self._instrument.parent, 'active_marker')(self._instrument.channel)
        return super().get_raw()
        
    def set_raw(self, value):
        getattr(self._instrument.parent, 'active_marker')(self._instrument.channel)
        super().set_raw(value)
        
class AGN_Channel(InstrumentChannel):

    def __init__(self, parent, name, channel) -> None:
        super().__init__(parent, name)
        self._parent = parent
        self.channel = channel
        
        self._dll = self._parent._dll
        self._handle = self._parent._handle
        self._status_handle = self._parent._status_handle

        self.add_parameter('output_filter',
                           attribute=AGN6030A_ATTR_OUTPUT_FILTER_ENABLED,
                           dtype=bool,
                           vals=vals.Bool(),
                           parameter_class=AGN_Parameter)

        self.add_parameter('output_bandwidth', unit='Hz',
                           attribute=AGN6030A_ATTR_OUTPUT_BANDWIDTH,
                           dtype=float,
                           parameter_class=AGN_Parameter)

        self.add_parameter('output',
                           attribute=AGN6030A_ATTR_OUTPUT_ENABLED,
                           dtype=bool,
                           vals=vals.Bool(),
                           parameter_class=AGN_Parameter)
        self.output.set_raw = self._configure_output_enabled

        self.add_parameter('output_configuration',
                           attribute=AGN6030A_ATTR_OUTPUT_CONFIGURATION,
                           dtype=int,
                           val_mapping={'Differential' : AGN6030A_VAL_CONFIGURATION_DIFFERENTIAL,
                                        'Single Ended' : AGN6030A_VAL_CONFIGURATION_SINGLE_ENDED,
                                        'Amplified' : AGN6030A_VAL_CONFIGURATION_AMPLIFIED},
                           parameter_class=AGN_Parameter)

        self.add_parameter('output_impedance', unit='Ohm',
                           attribute=AGN6030A_ATTR_OUTPUT_IMPEDANCE,
                           dtype=float,
                           parameter_class=AGN_Parameter)
        self.output_impedance.set_raw = self._configure_output_impedance

        self.add_parameter('gain',
                           attribute=AGN6030A_ATTR_ARB_GAIN,
                           dtype=float,
                           vals=vals.Numbers(0.170, 0.500),
                           parameter_class=AGN_Parameter)

        self.add_parameter('offset', unit='V',
                           attribute=AGN6030A_ATTR_ARB_OFFSET,
                           dtype=float,
                           vals=vals.Numbers(-1, 1),
                           parameter_class=AGN_Parameter)

        self.add_parameter('burst_count',
                           attribute=AGN6030A_ATTR_BURST_COUNT,
                           dtype=int,
                           parameter_class=AGN_Parameter)
        self.burst_count.set_raw = self._configure_burst_count

        self.add_parameter('trigger_source',
                           attribute=AGN6030A_ATTR_TRIGGER_SOURCE,
                           dtype=int,
                           #val_mapping=TRIGGER_MAP,
                           parameter_class=AGN_Parameter,
                           docstring='The available flags can be OR\'ed together to use multiple trigger '
                                    +'sources. This is however not supported by QTlab via the properties '
                                    +'setter and getters. Use configure_trigger_source instead if you '
                                    +'want to use multiple trigger sources.')
        self.configure_trigger_source(1)

        self.add_parameter('operation_mode',
                           attribute=AGN6030A_ATTR_OPERATION_MODE,
                           dtype=int,
                           val_mapping={'Continuous' : AGN6030A_VAL_OPERATE_CONTINUOUS,
                                        'Burst' : AGN6030A_VAL_OPERATE_BURST},
                           parameter_class=AGN_Parameter)

    @property
    def Parent(self):
        return self._parent
        
    @property
    def Amplitude(self):
        return self.gain() #TODO: CHECK THIS PROPERLY WITH MANUAL!
    @Amplitude.setter
    def Amplitude(self, val):
        self.gain(val)
        
    @property
    def Offset(self):
        return self.offset()    #TODO: CHECK WITH PROPERLY WITH MANUAL!
    @Offset.setter
    def Offset(self, val):
        self.offset(val)
        
    @property
    def Output(self):
        return (self.output() == 1)
    @Output.setter
    def Output(self, boolVal):
        self.output(boolVal)
        

    def add_parameter(self, name, **kwargs):
        kwargs['ch'] = str(self.channel)
        super().add_parameter(name, **kwargs)

    def _configure_output_enabled(self, enabled):
        '''
        Turn output on or off
        
        Parameters:
        -----------
        ch: Integer
            Channel number
        enabled: Boolean
            True if output enabled
        
        '''
        rc = self._dll.AGN6030A_ConfigureOutputEnabled(
            self._handle, ViString(basestring(self.channel)), ViBoolean(enabled))
        self._status_handle(rc)

    def _configure_output_impedance(self, impedance):
        '''
        Set the output impedance for the specified channel
        
        Parameters:
        -----------
        ch: Integer
            Channel number
        impedance: float
            Output impedance in units of ohm.
        
        '''
        rc = self._dll.AGN6030A_ConfigureOutputImpedance(
            self._handle, ViString(basestring(self.channel)), ViReal64(impedance))
        self._status_handle(rc)

    def _configure_burst_count(self, count):
        rc = self._dll.AGN6030A_ConfigureBurstCount(
            self._handle, ViString(basestring(self.channel)), ViInt32(count))
        self._status_handle(rc)

    def configure_trigger_source(self, source):
        '''
        Configure the trigger source
        
        Parameters:
        -----------
        ch: Integer
            Channel number
        source: Integer
            Flags can be OR'ed together
            1: External Trigger
            2: Software Trigger
            1024: No Trigger Flag
            1025: Software 1 Flag
            1056: Software 2 Flag
            1088: Software 3 Flag
            1026: External 1 Flag
            1028: External 2 Flag
            1032: External 3 Flag
            1040: External 4 Flag
            4195328: LXI Trig1 Flag
            
        '''
        rc = self._dll.AGN6030A_ConfigureTriggerSource(
            self._handle, ViString(basestring(self.channel)), ViInt32(source))
        self._status_handle(rc)
        
        self.trigger_source(source)

class AGN_Marker(InstrumentChannel):

    def __init__(self, parent, name, channel) -> None:
        super().__init__(parent, name)
        # self.parent = parent
        self.channel = channel

        self._dll = self._parent._dll
        self._handle = self._parent._handle
        self._status_handle = self._parent._status_handle

        self.add_parameter('source',
                           attribute=AGN6030A_ATTR_MARKER_SOURCE,
                           dtype=int,
                           val_mapping=MARKER_MAP,
                           parameter_class=AGN_Marker_Parameter)

        self.add_parameter('delay',
                           attribute=AGN6030A_ATTR_MARKER_DELAY,
                           dtype=float,
                           parameter_class=AGN_Marker_Parameter)

        self.add_parameter('pulse_width',
                           attribute=AGN6030A_ATTR_MARKER_PULSE_WIDTH,
                           dtype=float,
                           parameter_class=AGN_Marker_Parameter)

    def add_parameter(self, name, **kwargs):
        #kwargs['ch'] = str(self.channel)
        super().add_parameter(name, **kwargs)
                           
class Agilent_N8241A(Instrument):
    """
    qcodes driver for the Agilent_81180A Arbitrary Waveform Generator.

    Args:
        name: instrument name
        address: VISA resource name of instrument in format
            'TCPIP0::192.168.15.100::inst0::INSTR'
        **kwargs: passed to base class
    """
    def __init__(self, name: str, ivi_dll: str, address: str, init_clk_src='Internal', init_sync_mode='Independent', reset: bool=False, **kwargs) -> None:

        super().__init__(name=name, **kwargs)

        # load agilent dll
        self._dll = windll.LoadLibrary(ivi_dll)
        self._handle = None
        self._address = basestring(address)
        
        self._last_handle_wfm1 = None
        self._last_handle_wfm2 = None

        self._init(reset=reset)
        
        self.add_parameter('clock_frequency', unit='Hz',
                           attribute=AGN6030A_ATTR_CLOCK_FREQUENCY,
                           dtype=float,
                           set_cmd=False,
                           parameter_class=AGN_Parameter,
                           docstring='sample clock frequency of the instrument.')
        self.clock_frequency.set = self._set_sample_clock_frequency

        self.add_parameter('clock_source',
                           attribute=AGN6030A_ATTR_CLOCK_SOURCE,
                           dtype=int,
                           parameter_class=AGN_Parameter,
                           val_mapping={'Internal' : AGN6030A_VAL_CLOCK_INTERNAL,
                                        'External' : AGN6030A_VAL_CLOCK_EXTERNAL},
                           set_cmd=False,
                           docstring='sample clock source of the instrument.')
        self.clock_source.set = self._set_sample_clock_source

        self.add_parameter('output_mode',
                           attribute=AGN6030A_ATTR_OUTPUT_MODE,
                           dtype=int,
                           val_mapping={'Arbitrary Waveform' : AGN6030A_VAL_OUTPUT_ARB,
                                        'Sequence' : AGN6030A_VAL_OUTPUT_SEQ,
                                        'Advanced Sequence' : AGN6030A_VAL_OUTPUT_ADV_SEQ},
                           parameter_class=AGN_Parameter)
        self.output_mode.set_raw = self._configure_output_mode

        self.add_parameter('model',
                           attribute=AGN6030A_ATTR_INSTRUMENT_MODEL,
                           dtype=bytes,
                           str_size=255,
                           set_cmd=False,
                           parameter_class=AGN_Parameter)

        self.add_parameter('predistortion',
                           attribute=AGN6030A_ATTR_PREDISTORTION_ENABLED,
                           dtype=bool,
                           vals=vals.Bool(),
                           parameter_class=AGN_Parameter)

        self.add_parameter('ref_clock_source',
                           attribute=AGN6030A_ATTR_REF_CLOCK_SOURCE,
                           dtype=int,
                           val_mapping={'Internal' : AGN6030A_VAL_REF_CLOCK_INTERNAL,
                                        'External' : AGN6030A_VAL_REF_CLOCK_EXTERNAL,
                                        'PXI 10MHz' : AGN6030A_VAL_REF_CLOCK_PXI},
                           parameter_class=AGN_Parameter)
        self.ref_clock_source.set_raw = self._configure_ref_clock_source

        self.add_parameter('sync',
                           attribute=AGN6030A_ATTR_SYNC_ENABLED,
                           dtype=bool,
                           vals=vals.Bool(),
                           parameter_class=AGN_Parameter)

        self.add_parameter('sync_output',
                           attribute=AGN6030A_ATTR_SYNC_OUT_ENABLED,
                           dtype=bool,
                           vals=vals.Bool(),
                           parameter_class=AGN_Parameter)

        self.add_parameter('sync_mode',
                           attribute=AGN6030A_ATTR_SYNC_MODE,
                           dtype=int,
                           val_mapping={'Master' : AGN6030A_VAL_SYNC_MASTER,
                                        'Slave' : AGN6030A_VAL_SYNC_SLAVE},
                           parameter_class=AGN_Parameter)

        self.add_parameter('trigger_threshold_A',
                           attribute=AGN6030A_ATTR_TRIGGER_THRESHOLD_A,
                           dtype=float,
                           vals=vals.Numbers(-4.3, 4.3),
                           parameter_class=AGN_Parameter)

        self.add_parameter('trigger_threshold_B',
                           attribute=AGN6030A_ATTR_TRIGGER_THRESHOLD_B,
                           dtype=float,
                           vals=vals.Numbers(-4.3, 4.3),
                           parameter_class=AGN_Parameter)

        self.add_submodule('ch1', AGN_Channel(self, 'ch1', 1))
        self.add_submodule('ch2', AGN_Channel(self, 'ch2', 2))
        self._seq_wfms = {'ch1' : [], 'ch2' : []}
        self._seq_handles = {'ch1' : None, 'ch2' : None}
        self.done_programming = True
        self._raw_wfm_data = {}
        self._seq_mode = False

        self.add_submodule('m1', AGN_Marker(self, 'm1', 1))
        self.add_submodule('m2', AGN_Marker(self, 'm2', 2))
        self.add_submodule('m3', AGN_Marker(self, 'm3', 3))
        self.add_submodule('m4', AGN_Marker(self, 'm4', 4))
        
        self.add_parameter('active_marker',
                           attribute=AGN6030A_ATTR_ACTIVE_MARKER,
                           dtype=bytes,
                           str_size=255,
                           val_mapping = {1 : b'1',
                                          2 : b'2',
                                          3 : b'3',
                                          4 : b'4'},
                           parameter_class=AGN_Parameter)

        self.add_parameter('min_wfm_size',
                           attribute=AGN6030A_ATTR_MIN_WAVEFORM_SIZE,
                           dtype=int,
                           vals=vals.Ints(),
                           set_cmd=False,
                           parameter_class=AGN_Parameter)

        ########################
        #!!!!!!DISCLAIMER!!!!!!#
        #
        #THE FOLLOWING CODE IS PRESENT TO INITIALISE THE AWG INTO ITS USUAL DEFAULT STATE
        #ADD IN ENTRIES INTO THE YAML TO CHANGE SAID DEFAULTS. THE CURRENT ORDERING WORKS
        #IN BOTH INDEPENDENT AND MASTER/SLAVE CONFIGURATIONS - SO IF THESE COMMANDS ARE
        #CHANGED, ENSURE THAT THE MASTER/SLAVE CONFIGURATION STILL WORKS CORRECTLY BEFORE
        #PROCEEDING ONWARDS.

        #Setup clock to be internal for this case...
        self.ref_clock_source('External')
        if init_clk_src == 'Internal':
            self.configure_sample_clock(source=0, freq=1.25e9)
        else:
            self.configure_sample_clock(source=1, freq=1.25e9)

        #Setup synchronisation state
        self._sync_state = init_sync_mode
        self.add_parameter('Sync_State', label='Output Enable',
            get_cmd=self._get_awg_sync_state,
            set_cmd=self._set_awg_sync_state)
        self.Sync_State(self._sync_state)

        #Setup default mode to be burst
        self.ch1.operation_mode('Burst')
        self.ch1.burst_count(1)
        self.ch2.operation_mode('Burst')
        self.ch2.burst_count(1)
        #Use amplified output
        self.ch1.output_configuration('Amplified')
        self.ch2.output_configuration('Amplified')
        self.predistortion(False)
        self.ch1.output_filter(False)
        self.ch2.output_filter(False)
        self.ch1.gain(0.5)
        self.ch2.gain(0.5)
        #self.set_ch1_output_bandwidth(500e6)
        #self.set_ch2_output_bandwidth(500e6)
        #Set output to be 50Ohm and ON by default
        self.ch1.output_impedance(50)
        self.ch2.output_impedance(50)
        self.ch1.output(True)
        self.ch2.output(True)
        #Setup clock and triggers
        # self.clock_source('Internal')
        #self.ch1.configure_trigger_source(1024) # No Trigger flag
        #self.ch2.configure_trigger_source(1024) # No Trigger flag
        self.ch1.configure_trigger_source(1|1026|1028|1032|1040) # any hardware trigger input
        self.ch2.configure_trigger_source(1|1026|1028|1032|1040) # any hardware trigger input
        #Setup the marker sources to be for channels 1 and 2.
        self.m1.source('Channel 1 Marker 1')
        self.m2.source('Channel 1 Marker 2')
        self.m3.source('Channel 2 Marker 1')
        self.m4.source('Channel 2 Marker 2')
        self.trigger_threshold_A(0.7)
        self.trigger_threshold_B(0.7)

        self.get_all()

    def _init(self, id_query=True, reset=False):
        '''
        Open and configure an I/O session to the instrument and create
        a new session handle.
        
        If id_query is True, the function queries the instrument for its ID
        and verifies that the driver supports the particular instrument model.
        
        If True is passed to reset, the function places the instrument in
        a known state.
   
        '''
        if self._handle is None:
            self._handle = ViSession(0)
        else:
            raise Warning("There already exists an open session. Close it before "
                          "opening a new one.")

        rc = self._dll.AGN6030A_init(ViRsrc(self._address),
                                     ViBoolean(id_query),
                                     ViBoolean(reset),
                                     pointer(self._handle))
        self._status_handle(rc)

    def _status_handle(self, status):
        if status != VI_SUCCESS:
            message = self.get_error_message(status)
            if isinstance(message, int):
                message = "Error code {:x}".format(status & 2**32-1)
            else:
                message = "Error message: {}".format(message)
            if status & IVI_ERROR_BASE != IVI_ERROR_BASE:
                logging.debug(__name__+ ': '+message)
            else:
                raise RuntimeError(message)

    def close(self):
        '''Close the session handle to the instrument'''
        if self._handle is None:
            return
        
        rc = self._dll.AGN6030A_close(self._handle)
        self._handle = None
        self._status_handle(rc)

    def _configure_output_mode(self, output_mode):
        '''
        Configure whether a simple waveform, sequence or advanced sequence
        is played.
        
        Parameters:
        -----------
        output_mode:
            1:    arbitrary waveform
            2:    arbitrary sequence
            1001: advanced sequence
                
        '''
        display(output_mode)
        rc = self._dll.AGN6030A_ConfigureOutputMode(
            self._handle, ViInt32(output_mode))
        self._status_handle(rc)

    def _configure_ref_clock_source(self, source):
        '''
        Configure the reference clock source
        
        Parameters:
        -----------
        source: Integer
            0:    Internal reference clock
            1:    External reference clock
            1001: PXI 10MHz reference clock
        
        '''
        rc = self._dll.AGN6030A_ConfigureRefClockSource(
            self._handle, ViInt32(source))
        self._status_handle(rc)

    def get_error_message(self, error_code):
        message = create_string_buffer(256)
        
        rc = self._dll.AGN6030A_error_message(self._handle, ViInt32(error_code), message)
        if rc != VI_SUCCESS:
            return rc
        else:
            return message.value
        
    def abort_generation(self):
        rc = self._dll.AGN6030A_AbortGeneration(self._handle)
        self._status_handle(rc)
    
    def stop(self):
        '''Abort generation and disable slave triggers.'''
        self.abort_generation()
        if self.sync() and (self.sync_mode() == 'Master'):
            sync_marker_source = self.m4.source()
            if sync_marker_source != "Off":
                self.m4.source("Off")
                self._sync_marker_source = sync_marker_source

    def load_sequence(self, path, filename, append=False):
        '''
        Read the sequence file as defined in the pattern generation library
        and upload the corresponding waveform and marker data.
        
        This function then automatically generates an advanced sequence,
        currently with all loop_count=1,
        adv_modes=AGN6030A_VAL_WFM_ADV_PLAY_ONE_REP and marker_masks=VI_NULL.
        In the future, these parameters could also be added to the sequence
        file to create more versatile sequences.
        
        This function then creates an arbitrary scenario containing one single
        sequence with loop_count=1 and marker_mask=VI_NULL.
        
        This scenario is then set to be played, with options
        AGN6030A_VAL_PLAY_SINGLE and AGN6030A_VAL_JUMP_IMMEDIATE.
        
        Parameters:
        -----------
        path: String
            Path to the sequence file
        filename: String
            Name of the sequence file
        append: Bool
            If True, don't clear the waveform/sequence/scenario memories before loading.
        
        Returns:
        --------
        ch_wfm_handles: list of list of handle 
            Waveform handles for each channel
        seq_handles: list of handle
            Sequence handle for each channel
        scenario_handles: list of handle
            Scenario handle for each channel
        
        '''
        # Show filename in frontpanel
        self._file = (path, filename)
        #self.get_filename()
        #self.get_filepath()
        
        ch_waveforms, ch_inverse = self._read_sequence_file(path, filename)
        ## TODO: Or clear only the specific sequence handles?
        ## TODO: Include loop counts, marker masks into sequence file
        self.abort_generation()
        self.output_mode('Advanced Sequence')
        if not append:
            self.clear_arb_memory()
        self.output_mode('Arbitrary Waveform')
        ch_wfm_handles = self._create_waveform_handles(ch_waveforms, ch_inverse)
        self.output_mode('Advanced Sequence')
        
        # Create scenario handle for each channel
        seq_handles = []
        scenario_handles = []
        for ch, wfm_handles in enumerate(ch_wfm_handles, 1):
            # create sequence handle
            loop_counts = np.ones_like(wfm_handles)
            adv_modes = loop_counts.copy()
            adv_modes.fill(AGN6030A_VAL_WFM_ADV_PLAY_ONE_REP)
            marker_masks = loop_counts.copy()
            marker_masks.fill(VI_NULL)
            seq_handle = self.create_advanced_sequence(
                wfm_handles, loop_counts, adv_modes, marker_masks)
            seq_handles.append(seq_handle)
            
            # create scenario handle
            scenario_handle = self.create_arb_scenario(
                [seq_handle], [1], [VI_NULL])
            scenario_handles.append(scenario_handle)
            
            gain = getattr(self, "ch" + str(ch)).gain()
            offset = getattr(self, "ch" + str(ch)).offset()
            
            self.configure_arb_scenario(
                ch, scenario_handle, AGN6030A_VAL_PLAY_SINGLE,
                AGN6030A_VAL_JUMP_IMMEDIATE, gain, offset)
        
        return ch_wfm_handles, seq_handles, scenario_handles
    
    def _read_bin_file(self, path, filename, dtype="waveform"):
        array = []
        with open(os.path.join(path, filename), 'rb') as filep:
            if dtype == "waveform":
                array = np.fromfile(filep, dtype=np.float32)
            elif dtype == "marker":
                array = np.fromfile(filep, dtype=np.int8)
            else:
                raise TypeError('Unknown dtype `{0}`. Allowed dtypes are'
                                ' `waveform` or `marker`.'.format(dtype))
        return array

    def _read_sequence_file(self, path, filename):
        waveform_data_ch1 = []
        waveform_data_ch2 = []
        
        # read sequence file
        with open(os.path.join(path, filename)) as filep:
            files_ch1 = []
            files_ch2 = []
            for line in filep:
                match = re.match(r"\"(.*)\",\"(.*)\"", line)
                files_ch1.append(match.group(1))
                files_ch2.append(match.group(2))
        #files_ch1, inverse_ch1 = np.unique(files_ch1, return_inverse=True)
        #files_ch2, inverse_ch2 = np.unique(files_ch2, return_inverse=True)
        inverse_ch1 = range(len(files_ch1))
        inverse_ch2 = range(len(files_ch2))

        # allow programming of empty sequences        
        if not len(files_ch1):
            logging.warning('{0}: sequence file {1} is empty.'
                            .format(__name__, filename))
            min_size = self.min_wfm_size()
            waveform_data_empty = [(np.zeros((min_size,), np.float32), 
                                    np.zeros((min_size//8,), np.uint8))]
            return (waveform_data_empty, waveform_data_empty), ([0], [0])

        # load waveform and marker files                
        for waveform_data, files in [(waveform_data_ch1, files_ch1), 
                                     (waveform_data_ch2, files_ch2)]:
            for fn in files:
                wfm = self._read_bin_file(path, fn, dtype="waveform")
                marker = self._read_bin_file(path, "marker_" + fn, dtype="marker")
                waveform_data.append((wfm, marker))
                
        return (waveform_data_ch1, waveform_data_ch2), (inverse_ch1, inverse_ch2)

    def _create_waveform_handles(self, ch_waveforms, ch_inverse):
        '''
        Create waveform handles for a sequence file.
        
        Input:
            ch_waveforms (tuple of list of ndarray) - 
                list of unique waveforms for each channel
            ch_inverse (tuple of list of int) -
                waveform index for each channel, segment
        Return:
            (tuple of list of int) -
                waveform handle for each channel, segment
        '''
        # In the N8241A, waveform handles for the even (odd) for the first 
        # (second) channel. Thus, we have to alternate between channels when
        # creating handles.
        # balance lengths of ch_waveforms
        while len(ch_waveforms[0]) > len(ch_waveforms[1]):
            ch_waveforms[1].append(ch_waveforms[1][-1])
        while len(ch_waveforms[0]) < len(ch_waveforms[1]):
            ch_waveforms[0].append(ch_waveforms[0][-1])
        # create waveform handles
        unique_wfm_handles = np.zeros((2, len(ch_waveforms[0])), dtype=np.int32)
        for idx, waveforms in enumerate(zip(*ch_waveforms)):
            for ch, wfm in enumerate(waveforms):
                wfm_handle = self.create_arb_waveform_with_markers(wfm[0], wfm[1])
                unique_wfm_handles[ch][idx] = wfm_handle
        #
        ch_wfm_handles = (list(unique_wfm_handles[0][ch_inverse[0]]),
                          list(unique_wfm_handles[1][ch_inverse[1]]))
        return ch_wfm_handles

    def create_arb_waveform_with_markers(self, wfm_data, marker_data):
        '''
        Create a new waveform handle with markers
        
        Parameters:
        -----------
        wfm_data: 1 dimensional list or np.ndarray
            Waveform to be uploaded. All elements must be normalized
            between -1.00 and +1.00
            Restrictions:
                Length must be an integer multiple of 8.
        
        marker_data: 1 dimensional list or np.ndarray
            Marker waveform to be uploaded. Marker length must be
            equal to 1/8th of the waveform length.
            Bit 6 is marker1 and bit 7 is marker 2.
        
        return:
        -------
        wfm_handle: Integer
            Waveform handle referencing the uploaded waveform
            
        '''
        wfm_data = np.array(wfm_data)
        marker_data = np.array(marker_data)
        
        # Make waveform length integer multiple of 8 
        # and convert waveform to correct type
        wfm_data = self._pad_wfm(wfm_data)
        
        wfm_len = len(wfm_data)
        wfm_data = wfm_data.astype(ViReal64)
        ViReal64Array = wfm_len * ViReal64
        
        # Make marker length equal to 1/8th of waveform length
        marker_len = len(marker_data)
        len_difference = wfm_len // 8 - marker_len
        if len_difference != 0:
            logging.warning(__name__ + ": marker length not equal to 1/8th of"
                            " the waveform length. Append/remove last element {0:d} times"
                            " to match this condition.". format(len_difference))
            if len_difference > 0:
                marker_data = np.pad(marker_data, (0, len_difference), 'edge')
            elif len_difference < 0:
                marker_data = marker_data[:-len_difference]
        
        marker_len += len_difference
        marker_data = marker_data.astype(c_byte)
        ByteArray = marker_len * c_byte
        
        wfm_handle = ViInt32(0)
        
        rc = self._dll.AGN6030A_CreateArbWaveformWithMarkers(
            self._handle, ViInt32(wfm_len), ViReal64Array(*wfm_data),
            ViInt32(marker_len), ByteArray(*marker_data), byref(wfm_handle))
        self._status_handle(rc)
        
        return wfm_handle.value

    def create_advanced_sequence(self, wfm_handles, loop_counts, adv_modes, marker_masks):
        '''
        Create an advanced sequence handle
        
        Parameters:
        -----------
        wfm_handles: List/1D Array of Integers
            Array of waveform handles for the new advanced sequence.
        loop_counts: List/1D Array of Integers
            Array of loop counts for the new advanced sequence. Each
            loop_counts array element corresponds to a wfm_handles array
            element and indicates how many times to repeat that waveform.
            Must have same length as wfm_handles
        adv_modes: List/1D Array of Integers
            Specifies how to advance from one waveform to another within
            the sequence. Must have same length as wfm_handles array.
            There are four possibilities:
                0: Auto:
                    Plays the waveform, including repeats and advances to
                    the next waveform automatically. No trigger is required.
                1: Continuous:
                    Plays the waveform continuously. Waveform repeat count
                    is ignored. Only two types of trigger will stop waveform
                    in this mode: Jump trigger and stop trigger.
                2: Play one repetition:
                    One repetition of the waveform is played. Playback then
                    pauses until a waveform advance or waveform jump trigger
                    is received. An advance trigger continues playing
                    repeats until the repeat count is exhausted, while
                    jump trigger causes any remaining repeats to be skipped.
                3: Play all repetitions:
                    All repetition of the waveform are played. Playback then
                    pauses until a waveform advance or waveofrm jump 
                    trigger is received.
        marker_mask: List/1D Array of integers
            For each waveform, you can enable or disable markers that are
            automatically generated when the waveform stars, repeats,
            or during the time the waveform is being played (gate) using
            the following values:
                0x01: Start mask
                0x02: Repeat mask
                0x04: Gate mask
            These values may be OR'ed together to enable any desired set
            of markers for each point in the sequence.
                0: All waveform event markers are disabled.
            This array must have same length as wfm_handles array.
        
        Return:
        -------
        seq_handle: Integer:
            Handle identifying the created advanced sequence
        
        '''
        wfm_handles = np.array(wfm_handles)
        loop_counts = np.array(loop_counts)
        adv_modes = np.array(adv_modes)
        marker_masks = np.array(marker_masks)
        
        array_len = len(wfm_handles)
        if not all([len(array) == array_len for array in 
                    [loop_counts, adv_modes, marker_masks]]):
            raise ValueError("All arrays must have equal length")
        
        ViInt32Array = array_len * ViInt32
        ViUInt8Array = array_len * ViUInt8
        
        wfm_handles = wfm_handles.astype(ViInt32)
        loop_counts = loop_counts.astype(ViInt32)
        adv_modes = adv_modes.astype(ViUInt8)
        marker_masks = marker_masks.astype(ViUInt8)
        
        seq_handle = ViInt32(0)
        
        rc = self._dll.AGN6030A_CreateAdvancedSequence(self._handle,
            ViInt32(array_len), ViInt32Array(*wfm_handles), ViInt32Array(*loop_counts),
            ViUInt8Array(*adv_modes), ViUInt8Array(*marker_masks), byref(seq_handle))
        self._status_handle(rc)
        
        return seq_handle.value

    def create_arb_scenario(self, seq_handles, loop_counts, marker_masks):
        '''
        Create an arbitrary scenario handle
        
        Parameters:
        -----------
        seq_handles: 1D List/Array of Integers
            Array of advanced sequence handles.
        loop_counts: 1D List/Array of Integers
            Array of loop counts for arbitrary sequences of the new scenario.
            Each loop_counts array element corresponds to a seq_handles array
            element and indicates how many times to repeat that advanced
            sequence. Must have same length as seq_handles
        marker_masks: 1D List/Array of Integers
            For each sequence, you can enable or disable markers that are
            automatically generated when the sequence stars, repeats,
            or during the time the sequence is being played (gate) using
            the following values:
                0x01: Start mask
                0x02: Repeat mask
                0x04: Gate mask
            These values may be OR'ed together to enable any desired set
            of markers for each point in the scenario.
                0: All waveform event markers are disabled.
            This array must have same length as seq_handles array.
        
        '''
        seq_handles = np.array(seq_handles)
        loop_counts = np.array(loop_counts)
        marker_masks = np.array(marker_masks)
        array_len = len(seq_handles)
        if not all([len(array) == array_len for array in 
                    [loop_counts, marker_masks]]):
            raise ValueError("All arrays must have equal length")
        
        ViInt32Array = array_len * ViInt32
        ViUInt8Array = array_len * ViUInt8
        
        seq_handles = seq_handles.astype(ViInt32)
        loop_counts = loop_counts.astype(ViInt32)
        marker_masks = marker_masks.astype(ViUInt8)
        
        scenario_handle = ViInt32(0)
        
        rc = self._dll.AGN6030A_CreateArbScenario(self._handle, ViInt32(array_len),
                 ViInt32Array(*seq_handles), ViInt32Array(*loop_counts),
                 ViUInt8Array(*marker_masks), byref(scenario_handle)
                 )
        self._status_handle(rc)
        
        return scenario_handle.value

    def clear_arb_memory(self):
        '''
        Clears all previously created waveforms and sequences from the memory
        and invalidates all waveform and sequence handles
        
        '''
        self.abort_generation()
        rc = self._dll.AGN6030A_ClearArbMemory(self._handle)
        self._status_handle(rc)

    def configure_output_configuration(self, 
        ch, configuration, filter_enabled, filter_bandwidth):
        '''
        Configure the output configuration and the filter and
        filter bandwidth attributes.
        
        Parameters:
        -----------
        ch: Integer
            Channel number
        configuration: Integer
            0: differential output
            1: single ended output
            2: amplified output
        filter_enabled: Boolean
            If True, filter is enabled
        filter_bandwidth: float
            250e6: Limit bandwidth to 250MHz
            500e6: Limit bandwidth to 500MHz
        
        '''
        
        rc = self._dll.AGN6030A_ConfigureOutputConfiguration(
            self._handle, ViString(basestring(ch)), 
            ViInt32(configuration),
            ViBoolean(filter_enabled), 
            ViReal64(filter_bandwidth)
            )
        self._status_handle(rc)
        self.get_all()

    def _set_sample_clock_source(self, source):
        if source == 'Internal':
          self.configure_sample_clock(0, 1.25e9)
        elif source == 'External':
          self.configure_sample_clock(1, self.clock_frequency())

    def _set_sample_clock_frequency(self, freq):
        if self.clock_source():
          self.configure_sample_clock(1, freq)
        else:
          logging.warning('Cannot set frequency in internal clock source mode. Clock frequency is 1.25 GHz')

    def configure_sample_clock(self, source, freq):
        '''
        Configure the sample clock to be used
        
        Call abort_generation prior to calling this function and then restart 
        waveform playback with initiate_generation.
        
        Parameters:
        -----------
        source: Integer
            0: Internal clock
            1: External clock
        freq: Float
            Frequency of the clock in Hz.
            Restrictions:
                internal: Fixed to 1.25e9
                external: 100e6 to 1.25e9
        
        '''
        rc = self._dll.AGN6030A_ConfigureSampleClock(
            self._handle, ViInt32(source), ViReal64(freq))
        self._status_handle(rc)
        self.clock_source()
        self.clock_frequency()

    def initiate_generation(self):
        '''Initiate the generation of the output signal.'''
        rc = self._dll.AGN6030A_InitiateGeneration(self._handle)
        self._status_handle(rc)
    
    def run(self):
        '''Initiate generation of the output signal and slave triggers.'''
        self.initiate_generation()
        if self.sync() and (self.sync_mode() == 'Master'):
            if hasattr(self, '_sync_marker_source'):
                self.m4.source(self._sync_marker_source)
    
    def wait(self):
        '''Does nothing.'''
        pass

    def clear_arb_waveform(self, wfm_handle):
        '''
        Removes a previously created arbitrary waveform from the memory and
        invalidates the waveform handle
        
        Parameters:
        -----------
        wfm_handle: Integer
            Waveform handle
        
        '''
        if not isinstance(wfm_handle, ViInt32):
            wfm_handle = ViInt32(wfm_handle)
        
        rc = self._dll.AGN6030A_ClearArbWaveform(self._handle, wfm_handle)
        self._status_handle(rc)
    
    def _pad_wfm(self, wfm_data):
        wfm_len = len(wfm_data)
        remain = wfm_len % 8
        add_samples = 0
        if remain != 0:
            add_samples = 8 - remain
            logging.debug(__name__ + ": waveform length not an integer"
                            " multiple of 8. Append last element {:d} times"
                            " to match this condition.". format(add_samples))
        
            wfm_len += add_samples
            wfm_data = np.pad(wfm_data, (add_samples, 0), 'constant')
        return wfm_data

    def create_arb_waveform(self, wfm_data):
        '''
        Create a new waveform handle without markers
        
        Parameters:
        -----------
        wfm_data: 1 dimensional list or np.ndarray
            Waveform to be uploaded. All elements must be normalized
            between -1.00 and +1.00
            Restrictions:
                Length must be an integer multiple of 8.
        
        return:
        -------
        wfm_handle: Integer
            Waveform handle referencing the uploaded waveform
                
        '''
        # Make waveform length integer multiple of 8 
        # and convert waveform to correct type
        wfm_data = np.array(wfm_data)
        wfm_data = self._pad_wfm(wfm_data)
        wfm_len = len(wfm_data)
        wfm_data = wfm_data.astype(np.float64)
        ViReal64Array = wfm_len * ViReal64
        
        wfm_handle = ViInt32(0)
        
        rc = self._dll.AGN6030A_CreateArbWaveform(self._handle, ViInt32(wfm_len),
            ViReal64Array(*wfm_data), byref(wfm_handle)
            )
        self._status_handle(rc)
        
        return wfm_handle.value

    def configure_arb_waveform(self, ch, wfm_handle, gain, offset):
        '''
        Configure the gain and offset of a specific waveform
        
        Parameters:
        -----------
        ch: Integer
            Channel number
        wfm_handle: Integer
            Waveform handle that identifies the arbitrary waveform to
            generate.
        gain: Float
            Output amplitude (Vpp/2) of the waveform in Volts.
            Restrictions:
                single ended:           0.170 <= gain <= 0.250
                amplified/differential: 0.340 <= gain <= 0.500
        offset: Float
            DC offset in Volts added to the waveform output.
            Restrictions:
                -1.00 <= offset <= 1.00
        
        '''
        if not isinstance(wfm_handle, ViInt32):
            wfm_handle = ViInt32(wfm_handle)
            
        rc = self._dll.AGN6030A_ConfigureArbWaveform(
            self._handle, ViString(basestring(ch)),wfm_handle, ViReal64(gain), ViReal64(offset))
        self._status_handle(rc)
        self.get_all()

    def clear_advanced_sequence(self, seq_handle):
        '''
        Removes the previously created advanced sequence from the memory and
        invalidates the sequence handle
        
        Parameters:
        -----------
        seq_handle: Integer
            Advanced sequence handle

        '''
        if not isinstance(seq_handle, ViInt32):
            seq_handle = ViInt32(seq_handle)
        rc = self._dll.AGN6030A_ClearAdvancedSquence(self._handle, seq_handle)
        self._status_handle(rc)

    def clear_arb_sequence(self, seq_handle):
        '''
        Removes the previously created arbitrary sequence from the memory and
        invalidates the sequence handle
        
        Parameters:
        -----------
        seq_handle: Integer
            Handle that identifies the arbitrary sequence to clear

        '''
        if not isinstance(seq_handle, ViInt32):
            seq_handle = ViInt32(seq_handle)
        rc = self._dll.AGN6030A_ClearArbSquence(self._handle, seq_handle)
        self._status_handle(rc)

    def configure_arb_sequence(self, ch, seq_handle, gain, offset):
        '''
        Configure the gain and offset attribute of the arbitrary waveform generator
        that affect sequence generation
        
        Parameters:
        -----------
        ch: Integer
            Channel number
        seq_handle: Integer
            Sequence handle that identifies the arbitrary sequence to
            generate.
        gain: Float
            Output amplitude (Vpp/2) of the waveform in Volts.
            Restrictions:
                single ended:           0.170 <= gain <= 0.250
                amplified/differential: 0.340 <= gain <= 0.500
        offset: Float
            DC offset in Volts added to the waveform output.
            Restrictions:
                -1.00 <= offset <= 1.00
        
        '''
        if not isinstance(seq_handle, ViInt32):
            seq_handle = ViInt32(seq_handle)
            
        rc = self._dll.AGN6030A_ConfigureArbSequence(
            self._handle, ViString(basestring(ch)), seq_handle, ViReal64(gain), ViReal64(offset))
        self._status_handle(rc)
        self.get_all()

    def create_arb_sequence(self, wfm_handles, loop_counts):
        # TODO: Check for maximal loop count
        '''
        Create a new waveform handle without markers
        
        Parameters:
        -----------
        wfm_handles: 1 dimensional list or np.ndarray
            An array of waveform handles for the new sequence
        loop_counts: 1 dimensional list or np.ndarray of 32 bit integers
            An array that specifies the loop counts for the new sequence.
            Each element corresponds to a wfm_handles array element and indicates
            how many times to repeat that waveform. 
            Must have the same length as wfm_handles.
        
        return:
        -------
        seq_handle: Integer
            Arbitrary sequence handle referencing the generated sequence.
                
        '''
        
        wfm_handles = np.array(wfm_handles)
        loop_counts = np.array(loop_counts)
        
        wfm_handles_len = len(wfm_handles)
        if wfm_handles_len != len(loop_counts):
            raise ValueError("`wfm_handles` and `loop_counts` must have same length.")
         
        wfm_handles = wfm_handles.astype(ViInt32)
        loop_counts = loop_counts.astype(ViInt32)
        ViInt32Array = wfm_handles_len * ViInt32
        
        seq_handle = ViInt32(0)
        
        rc = self._dll.AGN6030A_CreateArbSequence(
            self._handle, ViInt32(wfm_handles_len), ViInt32Array(*wfm_handles),
            ViInt32Array(*loop_counts), byref(seq_handle)
            )
        self._status_handle(rc)
        
        return seq_handle.value

    def clear_arb_scenario(self, scenario_handle):
        '''
        Remove a previously created advanced sequence scenario from the memory
        and invalidate the handle that identifies it
        
        Parameter:
        ----------
        scenario_handle: Integer
            Handle identifying the scenario to be cleared.
        '''
        rc = self._dll.AGN6030A_ClearArbScenario(self._handle, ViInt32(scenario_handle))
        self._status_handle(rc)

    def configure_arb_scenario(
        self, ch, scenario_handle, play_mode, jump_mode, gain, offset):
        '''
        Configure the attributes that affect the advanced sequence
        scenario generation
        
        Parameters:
        -----------
        ch: Integer
            Channel number
        scenario_handle: Integer
            Handle identifying the scenario to be configured
        play_mode: Integer
            0: play single
            1: play continuous
        jump_mode: Integer
            This mode determines how the play table responds to a scenario
            jump event. There are three jump modes:
                0: Immediate: 
                    Scenario starts or jumps immediately with latency.
                1: End of waveform:
                    The current waveform, including repeats, is completed
                    before jumping to the new scenario.
                2: End of scenario:
                    The current scenario is completed before jumping to 
                    new scenario.
        gain: Float
            Output amplitude (Vpp/2) of the waveform in Volts.
            Restrictions:
                single ended:           0.170 <= gain <= 0.250
                amplified/differential: 0.340 <= gain <= 0.500
        offset: Float
            DC offset in Volts added to the waveform output.
            Restrictions:
                -1.00 <= offset <= 1.00
        
        '''
        rc = self._dll.AGN6030A_ConfigureArbScenario(
            self._handle, ViString(basestring(ch)), ViInt32(scenario_handle), 
            ViInt32(play_mode), ViInt32(jump_mode), ViReal64(gain), ViReal64(offset))
        self._status_handle(rc)
        self.get_all()

    def send_software_trigger(self):
        '''Send a software-generated trigger'''
        rc = self._dll.AGN6030A_SendSoftwareTrigger(self._handle)
        self._status_handle(rc)

    def reset(self):
        '''Reset the instrument to a known state'''
        rc = self._dll.AGN6030A_reset(self._handle)
        self._status_handle(rc)

    def configure_clock_sync(self, enabled, master):
        '''
        Configure the synchronization between different N8241A Series modules
        
        Parameters:
        -----------
        enabled: Boolean
            Turn on/off the synchronization mode
        mode: Boolean
            Specifies whether this instrument is the master or a slave.
            True: Master
            False: Slave
            
        '''
        rc = self._dll.AGN6030A_ConfigureClockSync(
            self._handle, ViBoolean(enabled), ViInt32(not master))
        
        ## Update front panel
        self.sync()
        self.sync_mode()
        
        self._status_handle(rc)

    def get_all(self):
        for key, p in self.parameters.items():
            p()
        for key, s in self.submodules.items():
            for key, p in s.parameters.items():
                p()

    def set_attribute_ViSession(self, ch, attribute, value):
        '''
        Set the value of a ViSession attribute
        
        Parameters:
        -----------
        ch: Integer
            Channel name
        attribute: Integer
            ID of the attribute to be set
        value: Integer
            Set attribute to this value
            
        '''
        rc = self._dll.AGN6030A_SetAttributeViSession(
            self._handle, ViString(basestring(ch)), ViAttr(attribute), ViReal64(value))
        self._status_handle(rc)

    def get_attribute_ViSession(self, ch, attribute):
        '''
        Get the value of a ViSession attribute
        
        Parameters:
        -----------
        ch: Integer
            Channel name
        attribute: Integer
            ID of the attribute
        
        Return:
        -------
        value: Integer
            Value of the attribute
            
        '''
        value = ViSession(0)
        rc = self._dll.AGN6030A_GetAttributeViSession4(
            self._handle, ViString(str(ch)), ViAttr(attribute), byref(value))
        self._status_handle(rc)
        return value.value

    def get_attribute_min_max(self, ch, attribute, dtype):
        '''
        Queries the minimum and maximum values of the specified attribute
        
        Parameters:
        -----------
        ch: Integer
            Channel name
        attribute: Integer
            ID of the attribute
        dtype: type
            Type of the return value. Possible values: int or float
        
        Return:
        -------
        min_max: tuple (min, max, has_min, has_max)
            min: dtype
            max: dtype
            has_min: Boolean
            has_max: Boolean
        '''
        has_min = ViBoolean(False)
        has_max = ViBoolean(False)
        
        if dtype == int:
            min_ = ViInt32(0)
            max_ = ViInt32(0)
            rc = self._dll.AGN6030A_GetAttrMinMaxViIn32(
                self._handle, ViString(basestring(ch)), ViAttr(attribute),
                byref(min_), byref(max_), byref(has_min), byref(has_max))
        elif dtype == float:
            min_ = ViReal64(0)
            max_ = ViReal64(0)
            rc = self._dll.AGN6030A_GetAttrMinMaxViReal64(
                self._handle, ViString(basestring(ch)), ViAttr(attribute),
                byref(min_), byref(max_), byref(has_min), byref(has_max))
        else:
            raise TypeError("Unsupported `dtype` {0}".format(dtype))
        
        self._status_handle(rc)
        return (min_.value, max_.value, has_min.value, has_max.value)

    def __del__(self):
        self.close()

    def num_supported_markers(self, channel_name):
        return 2

    def _get_channel_output(self, identifier):
        if identifier in self.submodules:
            return self.submodules[identifier]
        else:
            return None

    @property
    def SampleRate(self):
        return self.clock_frequency()
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        #TODO: this doesn't work - fix it...
        self.configure_sample_clock(source=0, freq=frequency_hertz)

    @property
    def AutoCompressionSupport(self):
        return {'Supported' : True, 'MinSize' : 128 , 'Multiple' : 8}

    def prepare_waveform_memory(self, chan_id, seg_lens, **kwargs):
        if len(seg_lens) > 1:
            self._seq_mode = True
        self._raw_wfm_data[chan_id] = kwargs.get('raw_data')
        self.done_programming = False

    def program_channel(self, chan_id, dict_wfm_data):
        if self.done_programming:
            #If no waveform preparation calls are made, then the done_programming flag stays True
            return

        #!!!NOTE!!!
        #Since the channels cannot be independently programmed, this function must be called after programming both channels (i.e. calling prepare_waveform_memory).
        #Just be aware of this during debugging.

        if len(self._seq_wfms['ch1']) > 0:
            #TODO: Implement the update-flag discriminator here... (If it's even possible with this AWG?)
            for cur_wgm_handle in self._seq_wfms['ch1']:
                self.clear_arb_waveform(cur_wgm_handle)
        self._seq_wfms['ch1'] = []
        if len(self._seq_wfms['ch2']) > 0:
            #TODO: Implement the update-flag discriminator here... (If it's even possible with this AWG?)
            for cur_wgm_handle in self._seq_wfms['ch2']:
                self.clear_arb_waveform(cur_wgm_handle)
        self._seq_wfms['ch2'] = []

        if self._seq_mode:
            self._program_channels_sequence()
        else:
            #There is at most one waveform committed to each channel. So use Arbitrary mode...
            if 'ch1' in self._raw_wfm_data:
                self._program_channel_non_sequence('ch1', self._raw_wfm_data['ch1']['waveforms'][0], self._raw_wfm_data['ch1']['markers'][0])
                if 'ch2' in self._raw_wfm_data:
                    self._program_channel_non_sequence('ch2', self._raw_wfm_data['ch2']['waveforms'][0], self._raw_wfm_data['ch2']['markers'][0])
            else:
                #Channel 2 has a waveform, but Channel 1 is empty. Due to the waveform handle restrictions, a dummy waveform is filled in channel 1's memory to enable writes to Channel 2...
                self._wfm_clog_memory()
                self._program_channel_non_sequence('ch2', self._raw_wfm_data['ch2']['waveforms'][0], self._raw_wfm_data['ch2']['markers'][0])

        self.done_programming = True
        self._seq_mode = False
        # self._raw_wfm_data = {}   #Pre-cache it so that if the data is unchanged, then it can be reused as channels must be programmed together on this special AWG...

    def _wfm_clog_memory(self):
        return self.create_arb_waveform_with_markers([0]*128, [0]*16)

    def _upload_waveforms(self, chan_id, wfm_data, mkr_data, gain_val):
        if len(mkr_data) == 2:
            mkr_data_reduced = np.zeros(int(len(wfm_data)/8))
            if len(mkr_data[0]) > 0:
                mkr_data_reduced += mkr_data[0][::8] * 2**6
            if len(mkr_data[1]) > 0:
                mkr_data_reduced += mkr_data[1][::8] * 2**7
        #Okay, the AWG has a strange quirk in which:
        #   - Waveforms cannot be updated, they can only be created
        #   - Waveforms are stored into AWG memory depending on the ordering of calls
        #   - So ensure that the order in uploading is always one waveform in channel 1 and then one in channel 2 etc...
        if len(mkr_data) == 2:
            self._seq_wfms[chan_id] += [self.create_arb_waveform_with_markers(wfm_data / gain_val, mkr_data_reduced)]
        else:
            self._seq_wfms[chan_id] += [self.create_arb_waveform(wfm_data / gain_val)]

    def _extract_marker_segments(self, mkr_list_overall, slice_start, slice_end):
        cur_mkrs = []
        for sub_mkr in range(len(mkr_list_overall)):
            if mkr_list_overall[sub_mkr].size > 0:
                cur_mkrs += [ mkr_list_overall[sub_mkr][slice_start:slice_end] ]
            else:
                cur_mkrs += [ mkr_list_overall[sub_mkr][:] ]    #Copy over the empty array...
        return cur_mkrs

    def _segment_single_waveform_into_2(self, chan_id):
        #Note that the presumption is that the other waveform channel has at least 2 segments in its sequence and thus, more than 256 points...
        dict_cur_wfm = self._raw_wfm_data[chan_id]
        cur_wfm = dict_cur_wfm['waveforms'][0]
        mkrs = [[None,None],[None,None]]
        if cur_wfm.size > 256:
            self._raw_wfm_data[chan_id]['waveforms'] = [cur_wfm[:128], cur_wfm[128:]]
            for mkr_ind, cur_mkr in enumerate(self._raw_wfm_data[chan_id]['markers'][0]):
                if cur_mkr.size > 0:
                    mkrs[0][mkr_ind] = cur_mkr[:128]
                    mkrs[1][mkr_ind] = cur_mkr[128:]
                else:
                    mkrs[0][mkr_ind] = cur_mkr[:]
                    mkrs[1][mkr_ind] = cur_mkr[:]
        elif cur_wfm.size > 128:
            wfm2 = np.concatenate((cur_wfm[128:] , np.repeat(cur_wfm[-1], cur_wfm.size - 128) ))
            self._raw_wfm_data[chan_id]['waveforms'] = [cur_wfm[:128], wfm2]
            for mkr_ind, cur_mkr in enumerate(self._raw_wfm_data[chan_id]['markers'][0]):
                if cur_mkr.size > 0:
                    mkrs[0][mkr_ind] = cur_mkr[:128]
                    mkrs[1][mkr_ind] = np.concatenate((cur_mkr[128:] , np.repeat(cur_mkr[-1], cur_mkr.size - 128) ))
                else:
                    mkrs[0][mkr_ind] = cur_mkr[:]
                    mkrs[1][mkr_ind] = cur_mkr[:]
        else:
            wfm1 = np.concatenate((cur_wfm, np.repeat(cur_wfm[-1], 128 - cur_wfm.size) ))
            wfm2 = np.repeat(cur_wfm[-1], 128)
            self._raw_wfm_data[chan_id]['waveforms'] = [wfm1, wfm2]
            for mkr_ind, cur_mkr in enumerate(self._raw_wfm_data[chan_id]['markers'][0]):
                if cur_mkr.size > 0:
                    mkrs[0][mkr_ind] = np.concatenate((cur_mkr, np.repeat(cur_mkr[-1], 128 - cur_mkr.size) ))
                    mkrs[1][mkr_ind] = np.repeat(cur_mkr[-1], 128)
                else:
                    mkrs[0][mkr_ind] = cur_mkr[:]
                    mkrs[1][mkr_ind] = cur_mkr[:]
        self._raw_wfm_data[chan_id]['markers'] = mkrs
        self._raw_wfm_data[chan_id]['seq_ids'] = [1,2]

    def _program_channels_sequence(self):
        self.stop()
        self.output_mode('Sequence')

        gain_1 = self.ch1.gain()
        gain_2 = self.ch2.gain()

        if 'ch1' in self._raw_wfm_data:
            num_wfms1 = len(self._raw_wfm_data['ch1']['waveforms'])
        else:
            num_wfms1 = 0
        if 'ch2' in self._raw_wfm_data:
            num_wfms2 = len(self._raw_wfm_data['ch2']['waveforms'])
        else:
            num_wfms2 = 0
        num_seg_pairs = max(num_wfms1, num_wfms2)

        #If one of the waveforms is a single-segment waveform, then it must be split and possibly padded to ensure it meets the minimum 2 segment sequence requirement...
        if num_wfms1 == 1:
            self._segment_single_waveform_into_2('ch1')
            num_wfms1 = 2
        if num_wfms2 == 1:
            self._segment_single_waveform_into_2('ch2')
            num_wfms2 = 2

        for m in range(num_seg_pairs):
            if m == 40:
                a=0
            if m < num_wfms1:
                self._upload_waveforms('ch1', self._raw_wfm_data['ch1']['waveforms'][m], self._raw_wfm_data['ch1']['markers'][m], gain_1)
                #A strange bug where the returned waveform handle is odd... Just reupload waveform...
                while self._seq_wfms['ch1'][-1] % 2 == 1:
                    self._seq_wfms['ch1'].pop(-1)
                    self._upload_waveforms('ch1', self._raw_wfm_data['ch1']['waveforms'][m], self._raw_wfm_data['ch1']['markers'][m], gain_1)
            else:
                self._seq_wfms['ch1'] += [self._wfm_clog_memory()]  #Clogs need to be registered to be ridden in the next episode...
                #A strange bug where the returned waveform handle is odd... Just reupload waveform...
                while self._seq_wfms['ch1'][-1] % 2 == 1:
                    self._seq_wfms['ch1'].pop(-1)
                    self._seq_wfms['ch1'] += [self._wfm_clog_memory()]
            if m < num_wfms2:
                self._upload_waveforms('ch2', self._raw_wfm_data['ch2']['waveforms'][m], self._raw_wfm_data['ch2']['markers'][m], gain_2)
                #A strange bug where the returned waveform handle is even... Just reupload waveform...
                while self._seq_wfms['ch2'][-1] % 2 == 0:
                    self._seq_wfms['ch2'].pop(-1)
                    self._upload_waveforms('ch2', self._raw_wfm_data['ch2']['waveforms'][m], self._raw_wfm_data['ch2']['markers'][m], gain_2)
            else:
                self._seq_wfms['ch2'] += [self._wfm_clog_memory()]  #Clogs need to be registered to be ridden in the next episode...
                #A strange bug where the returned waveform handle is even... Just reupload waveform...
                while self._seq_wfms['ch2'][-1] % 2 == 0:
                    self._seq_wfms['ch2'].pop(-1)
                    self._seq_wfms['ch2'] += [self._wfm_clog_memory()]

        # seq_len_1 = len(self._raw_wfm_data['ch1']['seq_ids'])
        # seq_len_2 = len(self._raw_wfm_data['ch2']['seq_ids'])
        # if seq_len_1 > seq_len_2:
        #     self._raw_wfm_data['ch2']['seq_ids'] += [self._raw_wfm_data['ch2']['seq_ids'][-1]]*( seq_len_1 - seq_len_2 )
        # if seq_len_2 > seq_len_1:
        #     self._raw_wfm_data['ch1']['seq_ids'] += [self._raw_wfm_data['ch1']['seq_ids'][-1]]*( seq_len_2 - seq_len_1 ) 

        num_wfms = (num_wfms1, num_wfms2)
        gains = (gain_1, gain_2)
        for ind, chan_id in enumerate(['ch1', 'ch2']):
            if num_wfms[ind] == 0:
                continue
            #Clear previous sequence if it exists...
            if self._seq_handles[chan_id] != None:
                self.clear_arb_sequence(self._seq_handles[chan_id])
            #Upload sequence
            wfm_handle_seq = [self._seq_wfms[chan_id][x] for x in self._raw_wfm_data[chan_id]['seq_ids']]
            loop_counts = [1]*len(wfm_handle_seq)
            self._seq_handles[chan_id] = self.create_arb_sequence(wfm_handle_seq, loop_counts)
        
        self.configure_arb_sequence(2, self._seq_handles['ch2'], gains[1], 0.0)
        self.configure_arb_sequence(1, self._seq_handles['ch1'], gains[0], 0.0)

        #Not required for Independent mode, but it is required for Master/Slave mode
        self.run()

    def _program_channel_non_sequence(self, chan_id, wfm_data, mkr_data = np.array([])):
        self.stop()
        self.output_mode('Arbitrary Waveform')

        #Bit 6 is Mkr1, Bit 7 is Mkr2
        if len(mkr_data) == 2:
            mkr_data_reduced = np.zeros(int(len(wfm_data)/8))
            if len(mkr_data[0]) > 0:
                mkr_data_reduced += mkr_data[0][::8] * 2**6
            if len(mkr_data[1]) > 0:
                mkr_data_reduced += mkr_data[1][::8] * 2**7
        #Program the channels
        if chan_id == 'ch1':
            if len(mkr_data) == 2:
                self._seq_wfms['ch1'] = [self.create_arb_waveform_with_markers(wfm_data / self.ch1.gain(), mkr_data_reduced)]
            else:
                self._seq_wfms['ch1'] = [self.create_arb_waveform(wfm_data / self.ch1.gain())]
            self.configure_arb_waveform(1, self._seq_wfms['ch1'][0], self.ch1.gain(), 0.0)
        elif chan_id == 'ch2':
            if len(mkr_data) == 2:
                self._seq_wfms['ch2'] = [self.create_arb_waveform_with_markers(wfm_data / self.ch2.gain(), mkr_data_reduced)]
            else:
                self._seq_wfms['ch2'] = [self.create_arb_waveform(wfm_data / self.ch2.gain())]
            self.configure_arb_waveform(2, self._seq_wfms['ch2'][0], self.ch2.gain(), 0.0)
        #Not required for Independent mode, but it is required for Master/Slave mode
        self.run()
    
    def _get_awg_sync_state(self):
        return self._sync_state #TODO: Remove this redundant state variable and augment sync_mode?
    def _set_awg_sync_state(self, new_state):
        if new_state == 'Independent':
            self.configure_clock_sync(enabled=False, master=True)
        elif new_state == 'Master':
            # self.sync(True)
            self.configure_clock_sync(enabled=True, master=True)
        elif new_state == 'Slave':
            self.configure_clock_sync(enabled=True, master=False)
        else:
            assert False, "The AWG SYNC state must be Independent, Master or Slave."
        self._sync_state = new_state
        