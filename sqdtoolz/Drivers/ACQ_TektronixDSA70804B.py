import time
from collections import OrderedDict
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from qcodes import validators as vals
from qcodes.instrument import Instrument, VisaInstrument, InstrumentChannel
# from qcodes.instrument_drivers.tektronix import TektronixDSA70000 


class TektronixDSA70804BChannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, channel:int) -> None:
        super().__init__(parent, name)
        self.channel = channel
        self._parent = parent     
        
        #vertical scale in volts
        self.add_parameter(
        'voltage_scale', label = 'Voltage Scale', unit = 'V',
        get_cmd = 'CH%d:SCAle?' %(self.channel), get_parser = float,
        set_cmd = 'CH%d:SCAle {}' %(self.channel), vals = vals.Numbers(20e-12, 1e3)
        )

        #vertical position: in divisions
        self.add_parameter(
        'vertical_position', label = 'Vertical Position', unit = 'div',
        get_cmd = 'CH%d:POSition?' %(self.channel), get_parser = float,
        set_cmd = 'CH%d:POSition {}' %(self.channel), vals = vals.Numbers(-8, 8)
        )
        #vertical offset: in volts
        self.add_parameter(
        'vertical_offset', label = 'Vertical Offset', unit = 'V',
        get_cmd = 'CH%d:OFFSet?' %(self.channel), get_parser = float,
        set_cmd = 'CH%d:OFFSet {}' %(self.channel), vals = vals.Numbers()
        )
   
        #vertical: select the channel to be displayed
        self.add_parameter(
        'select_ch', label = 'Select Ch', unit = 'a.u.',
        get_cmd = 'select:CH%d?' %(self.channel), get_parser = int,
        set_cmd = 'select:CH%d {}' %(self.channel), vals = vals.MultiType(vals.Numbers(),vals.Enum('on','off'))  
        )
    @property
    def VoltageScale(self):
        return self.voltage_scale()
    @VoltageScale.setter
    def VoltageScale(self, val):
        self.voltage_scale(val)

    @property
    def VerticalPosition(self):
        return self.vertical_position()
    @VerticalPosition.setter
    def VerticalPosition(self, val):
        self.vertical_position(val)
              
    @property
    def VerticalOffset(self):
        return self.vertical_offset()
    @VerticalOffset.setter
    def VerticalOffset(self, val):
        self.vertical_offset(val)

    @property
    def SelectCh(self):
        return self.select_ch()
    @SelectCh.setter
    def SelectCh(self, val):
        self.select_ch(val)        

class TektronixDSA70804BTriEdg(InstrumentChannel):    #trigger edge settings
    def __init__(self, parent:Instrument, tri_edg_name:str) -> None:
        super().__init__(parent=parent, name=tri_edg_name)
        self.tri_edg_name = tri_edg_name
        self._parent = parent   #not necessary?
        #####################trigger###########################
        self.add_parameter(
        'trigger_edge_source', label = 'Trigger %s Edge Source'%self.tri_edg_name, unit = 'a.u.',
        get_cmd = 'TRIGger:%s:EDGE:SOUrce?' %(self.tri_edg_name), get_parser = str,
        set_cmd = 'TRIGger:%s:EDGE:SOUrce {}' %(self.tri_edg_name), \
        vals =vals.Enum('auxiliary','ch1','ch2','ch3','ch4','line',\
            'd0','d1','d2','d3','d4','d5','d6','d7','d8','d9','d10','d11','d12','d13'\
            ,'d14','d15')             
        ) 
        self.add_parameter(
        'trigger', label = 'Trigger %s'%self.tri_edg_name, unit = 'a.u.',
        get_cmd = 'TRIGger:%s?' %(self.tri_edg_name), get_parser = str,
        set_cmd = 'TRIGger:%s {}' %(self.tri_edg_name), \
        vals =vals.Enum('setlevel')             #50% min~max voltage
        )  
        
        self.add_parameter(
        'trigger_edge_coupling', label = 'Trigger %s Edge Coupling'%self.tri_edg_name, unit = 'a.u.',
        get_cmd = 'TRIGger:%s:EDGE:COUPling?' %(self.tri_edg_name), get_parser = str,
        set_cmd = 'TRIGger:%s:EDGE:COUPling {}' %(self.tri_edg_name), \
        vals =vals.Enum('ac','dc','hfrej','lfrej','noiserej','atrigger') # 'atrigger' sets B the same as A, thus only valid for B
        )
        
        self.add_parameter(
        'trigger_edge_slope', label = 'Trigger %s Edge Slope'%self.tri_edg_name, unit = 'a.u.',
        get_cmd = 'TRIGger:%s:EDGE:SLOpe?' %(self.tri_edg_name), get_parser = str,
        set_cmd = 'TRIGger:%s:EDGE:SLOpe {}' %(self.tri_edg_name), \
        vals =vals.Enum('rise','fall','either')             #50% min~max voltage
        )  
                
        self.add_parameter(
        'trigger_level', label = 'Trigger %s Level'%self.tri_edg_name, unit = 'V',
        get_cmd = 'TRIGger:%s:LEVel?' %(self.tri_edg_name), get_parser = float,
        set_cmd = 'TRIGger:%s:LEVel {}' %(self.tri_edg_name), \
        vals =vals.MultiType(vals.Enum('ecl','ttl'),vals.Numbers())             #50% min~max voltage
        )  

        if self.tri_edg_name=='B':
            self.add_parameter(
            'trigger_state', label = 'Trigger %s State'%self.tri_edg_name, unit = 'a.u.',
            get_cmd = 'TRIGger:%s:STATE?' %(self.tri_edg_name), get_parser = int,
            set_cmd = 'TRIGger:%s:STATE {}' %(self.tri_edg_name), \
            vals =vals.MultiType(vals.Enum('on','off'),vals.Numbers())             #50% min~max voltage
            )              
 
        self.add_parameter( #query only
        'trigger_state_sys', label = 'Trigger State Sys', unit = 'a.u.',
        get_cmd = 'TRIGger:STATE?', get_parser = str
        )

        if self.tri_edg_name=='A':                               
            self.add_parameter( #query only
            'trigger_holdoff', label = 'Trigger Holdoff', unit = 'a.u.',
            get_cmd = 'TRIGger:A:HOLDoff?', get_parser = str
            )   
            self.add_parameter( #query only
            'trigger_holdoff_actual', label = 'Trigger Holdoff Actual', unit = 'a.u.',
            get_cmd = 'TRIGger:A:HOLDoff:ACTUal?', get_parser = str
            )  
            self.add_parameter( 
            'trigger_holdoff_by', label = 'Trigger Holdoff By', unit = 'a.u.',
            get_cmd = 'TRIGger:A:HOLDoff:BY?', get_parser = str,
            set_cmd = 'TRIGger:A:HOLDoff:BY {}',vals = vals.Enum('time','default','random','auto')
            )    
            self.add_parameter( 
            'trigger_holdoff_time', label = 'Trigger Holdoff Time', unit = 'a.u.',
            get_cmd = 'TRIGger:A:HOLDoff:TIMe?', get_parser = str,
            set_cmd = 'TRIGger:A:HOLDoff:TIMe {}',vals = vals.Numbers(250e-9,12)
            )                                                
    @property
    def TriggerEdgeSource(self):
        return self.trigger_edge_source()
    @TriggerEdgeSource.setter
    def TriggerEdgeSource(self, val):
        self.trigger_edge_source(val)    
          
    @property
    def Trigger(self):
        return self.trigger()
    @Trigger.setter
    def Trigger(self, val):
        self.trigger(val)    

    @property
    def TriggerEdgeCoupling(self):
        return self.trigger_edge_coupling()
    @TriggerEdgeCoupling.setter
    def TriggerEdgeCoupling(self, val):
        self.trigger_edge_coupling(val) 

    @property
    def TriggerEdgeSlope(self):
        return self.trigger_edge_slope()
    @TriggerEdgeSlope.setter
    def TriggerEdgeSlope(self, val):
        self.trigger_edge_slope(val)                    
    
    @property
    def TriggerLevel(self):
        return self.trigger_level()
    @TriggerLevel.setter
    def TriggerLevel(self, val):
        self.trigger_level(val)     

    @property
    def TriggerState(self):
        return self.trigger_state()
    @TriggerState.setter
    def TriggerState(self, val):
        self.trigger_state(val)        
    
    @property
    def TriggerStateSys(self):
        return self.trigger_state_sys()    

    @property
    def TriggerHoldoff(self):
        return self.trigger_holdoff()   

    @property
    def TriggerHoldoffActual(self):
        return self.trigger_holdoff_actual()   

    @property
    def TriggerHoldoffBy(self):
        return self.trigger_holdoff_by()
    @TriggerHoldoffBy.setter
    def TriggerHoldoffBy(self, val):
        self.trigger_holdoff_by(val)    

    @property
    def TriggerHoldoffTime(self):
        return self.trigger_holdoff_time()
    @TriggerHoldoffTime.setter
    def TriggerHoldoffTime(self, val):
        self.trigger_holdoff_time(val)                                            

class TektronixDSA70804B(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=10, **kwargs)
         
        #parameters
        #Check VISA Daemon is running on the instrument
        #Autoset
        self.add_parameter(
        'autoset', label = 'Autoset', unit = 'a.u.',
        # get_cmd = 'ACQuire:SAMPlingmode?', get_parser = str,
        set_cmd = 'AUTOSet {}', vals = vals.Enum('execute','undo','vfields','video','vlines')
        )        

        #vertical: ask the status of all the channels
        self.add_parameter( #query only
        'select', label = 'Select', unit = 'a.u.',
        get_cmd = 'select?', get_parser = str,
        )       

        #smpling mode setting and query
        self.add_parameter(
        'acquire_samplingmode', label = 'Acquire Samplingmode', unit = 'a.u.',
        get_cmd = 'ACQuire:SAMPlingmode?', get_parser = str,
        set_cmd = 'ACQuire:SAMPlingmode {}', vals = vals.Enum('rt','it','et')
        )   

        self.add_parameter(
        'acquire_mode', label = 'Acquire Mode', unit = 'a.u.',
        get_cmd = 'ACQuire:MODe?', get_parser = str,
        set_cmd = 'ACQuire:MODe {}', vals = vals.Enum('sample','peakdetect','hires','average','wfmdb','envelop')
        )        

        #set the time scale (Horizontal axis) i.e. define period of time per division
        #valid nonly for manual mode
        self.add_parameter(
        'time_scale', label = 'Time Scale', unit = 's',
        get_cmd = 'HORizontal:MODE:SCAle?', get_parser = float,
        set_cmd = 'HORizontal:MODE:SCAle {}'#, vals = vals.Numbers(20e-12, 1e3)
        )

        #horizontal position: the position of the trigger point 
        self.add_parameter(
        'horizontal_position', label = 'Horizontal Position', unit = '%',
        get_cmd = 'HORizontal:POSition?', get_parser = float,
        set_cmd = 'HORizontal:POSition {}' , vals = vals.Numbers(0, 100)
        )


        #Sample Rate  max 25e9 GS/s, division by powers of two of max sample rate
        #Therefore, sampling rate values are 250MS/s, 625MS/s, 1.25GS/s, 3.13GS/s, 6.25GS/s, 12.5GS/s
        self.add_parameter(# settings for enabling sample rate tunability
        'horizontal_mode', label = 'Horizontal Mode', unit = 'a.u.',
        get_cmd = 'HORizontal:MODE?', get_parser = str,
        set_cmd = 'HORizontal:MODE {}', vals = vals.Enum('auto','constant','manual')
        )        
        self.add_parameter(
        'sample_rate', label = 'Sample Rate', unit = 'Hz',
        get_cmd = 'HORizontal:MODE:SAMPLERate?', get_parser = float,
        set_cmd = 'HORizontal:MODE:SAMPLERate {}'#, vals = vals.Numbers(1, 25e9)
        )
        self.add_parameter(#query only
        'horizontal_acqduration', label = 'Horizontal Acqduration', unit = 's',
        get_cmd = 'HORizontal:ACQDURATION?', get_parser = float,        
        )
        self.add_parameter(#query only
        'horizontal_acqlength', label = 'Horizontal Acqlength', unit = 'pts',
        get_cmd = 'HORizontal:ACQLENGTH?', get_parser = int,        
        )
        # For query the commands below and above are the same
        self.add_parameter(#query and write 
        'horizontal_mode_recordlength', label = 'Horizontal Mode Recordlength', unit = 'pts',
        get_cmd = 'HORizontal:MODE:RECOrdlength?', get_parser = int,  
        set_cmd = 'HORizontal:MODE:RECOrdlength {}'    
        )              
        #Added after David left in the afternoon on 22/07/2024
        ################output command groups from instrument to controller##################
        # (1) in the below, the comma in ``%(self.channel_number,)'' is necessary for syntax validity for format oupt
        # (2) in the below "get_parser" means the returned data type of the "get_cmd", which is a string, e.g., ``CH1''. 
        # Thus "get_parser=str" is used.   
        # (3) vals.Enum(1,2,3,4) means only values in the pratheses are allowed
        # (4) this function specifies the waveform source when transferring a waveform "FROM" the instrument INTO the measurement computer
        self.add_parameter( # step1 Select the waveform source(s) using DATa:SOUrce
        'data_source', label = 'Data Source', unit = 'a.u.',
        get_cmd = 'data:source?', get_parser =str,
        set_cmd = 'data:source {}',vals = vals.Enum('ch1','ch2','ch3','ch4','math1','math2',\
                                                    'math3','math4','ref1','ref2','ref3','ref4')#, #needing further modification to include ch1, ref1, math1, etc
        )

        self.add_parameter( # step2  Specify the waveform data format using DATa:ENCdg.
        'data_encdg', label = 'Data Encdg', unit = 'a.u.',
        get_cmd = 'data:encdg?', get_parser =str,
        set_cmd = 'data:encdg {}',vals = vals.Enum('ascii','fastest','ribinary','rpbinary','fpbinary',\
                                                   'sribinary','srpbinary','sfpbinary')
        )
       
        self.add_parameter( # step3 Specify the number of bytes per data point using WFMOutpre:BYT_Nr.
        'wfmoutpre_byt_nr', label = 'Wfmoutpre Byt Nr', unit = 'a.u.',
        get_cmd = 'wfmoutpre:byt_nr?', get_parser =int,
        set_cmd = 'wfmoutpre:byt_nr {}',vals = vals.Enum(1,2,4,8) 
        # the number of bytes per data point and can be 1, 2 (RI, RP) or 4 (FP)
        # A value of 1 or 2 bytes per waveform point indicates channel data; 
        # 4 bytes per waveform point indicate math data; 
        # 8 bytes per waveform point indicate pixel map (DPO) data.
        )
        # these function of data_start and data-stop are used for obtaining data FROM the instrument INTO the measurement computer
        self.add_parameter(#step 4 Specify the portion of the waveform that you want to transfer using DATa:STARt and DATa:STOP.
        'data_start', label = 'Data Start', unit = 'a.u.',
        # ranging from 1 to the record length
        get_cmd = 'data:start?', get_parser = int,
        set_cmd = 'data:start {}', #vals = vals.Numbers(1, 1e5)
        )
        self.add_parameter(
        'data_stop', label = 'Data Stop', unit = 'a.u.',
        get_cmd = 'data:stop?', get_parser = int,
        set_cmd = 'data:stop {}', #vals = vals.Numbers(1, 1e5)
        )
        # waveform output preamble
        self.add_parameter(#step 5 Transfer waveform preamble information using WFMOutpre.
        'wfmoutpre', label = 'Wfmoutpre', unit = 'a.u.',
        get_cmd = 'wfmoutpre?', get_parser =str
        ) 
        
        self.add_parameter(#step 6 Transfer waveform data from the instrument using CURVe?.
        'curve', label = 'Curve', unit = 'a.u.',
        get_cmd = 'curve?', get_parser =str,
        set_cmd='{}',vals=vals.Enum('curve')
        ) 
        
        self.add_parameter(#step 6 Transfer waveform data from the instrument using CURVe?.
        'curve_block', label = 'Curve Block', unit = 'a.u.',
        get_cmd = 'curve?', get_parser =str,
        set_cmd='curve {}',vals=vals.Arrays()
        ) 
        self.add_parameter(#
        'wfmoutpre_byt_or', label = 'Wfmoutpre Byt Or', unit = 'a.u.',
        get_cmd = 'WFMOutpre:BYT_Or?', get_parser =str,
        set_cmd = 'WFMOutpre:BYT_Or {}',vals = vals.Enum('msb','lsb')
        # this specification is only meaningful when wfminpre:encdg==BIN and wfminpre:bn_fmt==RI or RP 
        )
############################################# input
########## 1. Specify waveform reference memory using DATa:DESTination.

        self.add_parameter(#step 6 Transfer waveform data from the instrument using CURVe?.
        'data_destination', label = 'Data Destination', unit = 'a.u.',
        get_cmd = 'data:destination?', get_parser =str,
        set_cmd='data:destination {}',vals=vals.Enum('ref1','ref2','ref3','ref4')
        ) 
########## 2. Set WFMInpre:NR_Pt to equal the number of data points to be sent
        #This command sets or queries the number of data points that are 
        #in the transmitted waveform record.
        self.add_parameter(#
        'wfminpre_nr_pt', label = 'Wfminpre Nr Pt', unit = 'a.u.',
        get_cmd = 'wfmINpre:NR_Pt?', get_parser =int,
        set_cmd = 'wfmINpre:NR_Pt {}',vals = vals.Numbers(1,1e5)#, 1e5 could be modified to other values
        )
######### 3. Specify the waveform data format using WFMInpre:ENCdg.       
        self.add_parameter(#
        'wfminpre_encdg', label = 'Wfminpre Encdg', unit = 'a.u.',
        get_cmd = 'WFMInpre:ENCdg?', get_parser =str,
        set_cmd = 'WFMInpre:ENCdg {}',vals = vals.Enum('ascii','binary')#, 1e5 could be modified to other values
        )
##########4. Specify the number of bytes per data point using WFMInpre:BYT_Nr.
        self.add_parameter(#
        'wfminpre_byt_nr', label = 'Wfminpre Byt Nr', unit = 'a.u.',
        get_cmd = 'WFMInpre:BYT_Nr?', get_parser =int,
        set_cmd = 'WFMInpre:BYT_Nr {}',vals = vals.Enum(1,2,4)
        # this specification is only meaningful when wfminpre:encdg==BIN and wfminpre:bn_fmt==RI or RP 
        )


        # wave form input preamble
        self.add_parameter(     #step6 for input
        'wfminpre', label = 'Wfminpre', unit = 'a.u.',
        get_cmd = 'wfminpre?', get_parser =str
        )
  
#############other commands####################
        # Control whether the answer from the insturment has headers
        self.add_parameter(     #step6 for input
        '_header', label = 'Header', unit = 'a.u.',
        get_cmd = 'header?', get_parser =str,
        set_cmd = 'header {}',vals=vals.Enum(0,'off','on')
        )
###############parameters for scaling the output from the instrument
        self.add_parameter(     # query only
        'wfmoutpre_xzero', label = 'Wfmoutpre Xzero', unit = 'a.u.',
        get_cmd = 'WFMOutpre:XZEro?', get_parser =float        
        )

        self.add_parameter(     # query only
        'wfmoutpre_xincr', label = 'Wfmoutpre Xincr', unit = 'a.u.',
        get_cmd = 'WFMOutpre:XINcr?', get_parser =float,
        )

        self.add_parameter(     # query only
        #trigger point relative to DATa:STARt for the waveform specified by the DATa:SOUrce command.
        'wfmoutpre_pt_off', label = 'Wfmoutpre Pt Off', unit = 'a.u.',
        get_cmd = 'WFMOutpre:PT_Off?', get_parser =float
        )

        self.add_parameter(     # query only
        'wfmoutpre_xunit', label = 'Wfmoutpre Xunit', unit = 'a.u.',
        get_cmd = 'WFMOutpre:XUNit?', get_parser =str,
        )        
        self.add_parameter(     # query only
        'wfmoutpre_yzero', label = 'Wfmoutpre Yzero', unit = 'a.u.',
        get_cmd = 'WFMOutpre:YZEro?', get_parser =float,
        )
        self.add_parameter(     # query only
        'wfmoutpre_ymult', label = 'Wfmoutpre Ymult', unit = 'a.u.',
        get_cmd = 'WFMOutpre:YMUlt?', get_parser =float,
        )
        self.add_parameter(     # query only
        'wfmoutpre_yoff', label = 'Wfmoutpre Yoff', unit = 'a.u.',
        get_cmd = 'WFMOutpre:YOFf?', get_parser =float,
        )
        self.add_parameter(     # query only
        'wfmoutpre_yunit', label = 'Wfmoutpre Yunit', unit = 'a.u.',
        get_cmd = 'WFMOutpre:YUNit?', get_parser =str,
        )

        self.add_parameter(     # binary data format
        'wfmoutpre_bn_fmt', label = 'Wfmoutpre Bn Fmt', unit = 'a.u.',
        get_cmd = 'WFMOutpre:bn_fmt?', get_parser =str,
        set_cmd = 'WFMOutpre:bn_fmt {}', vals=vals.Enum('ri','rp','fp')  
        # RI specifies signed integer data point representation.
        # RP specifies positive integer data point representation.
        # FP specifies single-precision binary floating point data point representation.
        )


        self._ch_list = ['CH1', 'CH2', 'CH3', 'CH4']
        for ch_ind, ch_name in enumerate(self._ch_list):
            cur_channel = TektronixDSA70804BChannel(self, ch_name, ch_ind+1)
            self.add_submodule(ch_name, cur_channel)

        self._tri_edg_list = ['A', 'B']
        for _,tri_edg_name in enumerate(self._tri_edg_list):
            cur_tri_edg = TektronixDSA70804BTriEdg(self, tri_edg_name)
            self.add_submodule(tri_edg_name, cur_tri_edg)            
    @property
    def Autoset(self):
        raise Exception("Autoset is set-only: no query allowed")
        return         
    @Autoset.setter
    def Autoset(self, val):
        self.autoset(val)           

    @property
    def Select(self):        
        return self.select()        


    @property
    def AcquireSamplingmode(self):
        return self.acquire_samplingmode()
    @AcquireSamplingmode.setter
    def AcquireSamplingmode(self, val):
        self.acquire_samplingmode(val)

    @property
    def AcquireMode(self):
        return self.acquire_mode()
    @AcquireMode.setter
    def AcquireMode(self, val):
        self.acquire_mode(val)        

    @property
    def TimeScale(self):
        return self.time_scale()
    @TimeScale.setter
    def TimeScale(self, val):
        self.time_scale(val)

    @property
    def HorizontalPosition(self):
        return self.horizontal_position()
    @HorizontalPosition.setter
    def HorizontalPosition(self, val):
        self.horizontal_position(val)

    @property
    def HorizontalMode(self):
        return self.horizontal_mode()
    @HorizontalMode.setter
    def HorizontalMode(self, val):
        self.horizontal_mode(val)
    
    @property
    def SampleRate(self):
        return self.sample_rate()
    @SampleRate.setter
    def SampleRate(self, val):
        self.sample_rate(val)

    @property
    def HorizontalAcqduration(self):
        return self.horizontal_acqduration()
    @property
    def HorizontalAcqlength(self):
        return self.horizontal_acqlength()

    @property
    def HorizontalModeRecordlength(self):
        return self.horizontal_mode_recordlength()
    @HorizontalModeRecordlength.setter
    def HorizontalModeRecordlength(self, val):
        self.horizontal_mode_recordlength(val)

#Added after David left in the afternoon on 22/07/2024
    

    @property   #step 1 for output: transferring data from the instrument to controller
    def DataSource(self):
        return self.data_source()
    @DataSource.setter
    def DataSource(self, val):
        self.data_source(val)                

    @property   #step 2 for output
    def DataEncdg(self):
        return self.data_encdg()
    @DataEncdg.setter
    def DataEncdg(self, val):
        self.data_encdg(val)     

    @property   #step 3 for output
    def WfmoutpreBytNr(self):
        return self.wfmoutpre_byt_nr()
    @WfmoutpreBytNr.setter
    def WfmoutpreBytNr(self, val):
        self.wfmoutpre_byt_nr(val)  

    @property   #step 4 for output
    def DataStart(self):
        return self.data_start()
    @DataStart.setter
    def DataStart(self, val):
        self.data_start(val)        
    @property
    def DataStop(self):
        return self.data_stop()
    @DataStart.setter
    def DataStop(self, val):
        self.data_stop(val) 

    @property   #step 5 for output
    def Wfmoutpre(self):
        return self.wfmoutpre()

    @property   #step 6 for output
    def Curve(self):
        return self.curve()
    @Curve.setter
    def Curve(self,val):
        return self.curve(val) 
    
    @property
    def CurveBlock(self):
        return self.curve_block()   
    @CurveBlock.setter
    def CurveBlock(self,val):
        return self.curve_block(val)

    @property
    def WfmoutpreBytOr(self):
        return self.wfmoutpre_byt_or()   
    @WfmoutpreBytOr.setter
    def WfmoutpreBytOr(self,val):
        return self.wfmoutpre_byt_or(val)        
########################## Input
    @property   #step 1 for input
    def DataDestination(self):
        return self.data_destination()
    @DataDestination.setter
    def DataDestination(self,val):
        return self.data_destination(val) 
    

    @property   #step 2 for input
    def WfminpreNrPt(self):
        return self.wfminpre_nr_pt()
    @WfminpreNrPt.setter
    def WfminpreNrPt(self, val):
        self.wfminpre_nr_pt(val)      

    @property   #step 3 for input
    def WfminpreEncdg(self):
        return self.wfminpre_encdg()
    @WfminpreEncdg.setter
    def WfminpreEncdg(self, val):
        self.wfminpre_encdg(val)   

    @property   #step 4 for input
    def WfminpreBytNr(self):
        return self.wfminpre_byt_nr()
    @WfminpreBytNr.setter
    def WfminpreBytNr(self, val):
        self.wfminpre_byt_nr(val)           
                # step 5 Specify first data point in the waveform record using DATa:STARt.
                # using the command for the one for output
    @property   #step6 for input
    def Wfminpre(self):
        return self.wfminpre()
#####################################################
    @property   
    def _Header(self):
        return self._header()
    @_Header.setter
    def _Header(self, val):
        self._header(val)      
###########parmeters for creating the waveform from the raw data####
    @property   
    def WfmoutpreXzero(self):
        return self.wfmoutpre_xzero()
    @property   
    def WfmoutpreXincr(self):
        return self.wfmoutpre_xincr()
    @property   
    def WfmoutprePtOff(self):
        return self.wfmoutpre_pt_off()
    @property
    def WfmoutpreXunit(self):
        x_unit=self.wfmoutpre_xunit()
        x_unit=list(x_unit)
        x_unit[0]='('
        x_unit[-1]=')'
        x_unit="".join(x_unit)
        return x_unit
    @property
    def WfmoutpreYzero(self):
        return self.wfmoutpre_yzero()
    @property
    def WfmoutpreYmult(self):
        return self.wfmoutpre_ymult()
    @property
    def WfmoutpreYoff(self):
        return self.wfmoutpre_yoff()
    @property
    def WfmoutpreYunit(self):
        y_unit=self.wfmoutpre_yunit()
        y_unit=list(y_unit)
        y_unit[0]='('
        y_unit[-1]=')'
        y_unit="".join(y_unit)
        return y_unit
    
    @property
    def WfmoutpreBnFmt(self):
        return self.wfmoutpre_bn_fmt()
    @WfmoutpreBnFmt.setter
    def WfmoutpreBnFmt(self,val):
        self.wfmoutpre_bn_fmt(val)

    
    def wfm_plot(self):
        x0=self.WfmoutpreXzero
        x_incr=self.WfmoutpreXincr
        pt_off=self.WfmoutprePtOff
        x_unit=self.WfmoutpreXunit

        y0=self.WfmoutpreYzero
        y_mult=self.WfmoutpreYmult
        y_off=self.WfmoutpreYoff
        y_unit=self.WfmoutpreYunit
        
        # if self.DataEncdg==''
        # if self.WfmoutpreBytNr
        # if self.WfmoutpreBnFmt
        DataEncdg=self.DataEncdg
        BnFmt=self.WfmoutpreBnFmt
        BytNr=self.WfmoutpreBytNr
        BytOr=self.WfmoutpreBytOr
        # print(BytOr)
        if BytOr=='MSB':
            is_big_endian=True
        elif BytOr=='LSB':
            is_big_endian=False
        else:
            print('Illegal Byt_Or obtained!')
        # print(DataEncdg)
        # print(BnFmt)
        # print(BytNr)
        if DataEncdg=='ASCI': # fastest will induce ri rp or fp, so omit fastest           
            wfm_data=self.visa_handle.query_ascii_values('curve?')
        elif  BnFmt=='RI' :#| BnFmt=='SRI':#signed integer
            if BytNr==1:#signed char
                wfm_data=self.visa_handle.query_binary_values('curve?', datatype='b',is_big_endian=is_big_endian)
                self.status_print()
            elif BytNr==2:#short
                wfm_data=self.visa_handle.query_binary_values('curve?', datatype='h',is_big_endian=is_big_endian)   
                self.status_print()
            # elif BytNr==4:#int, optionally long (not existing)
            #     wfm_data=self.visa_handle.query_binary_values('curve?', datatype='i')
                # what is the difference between int and long
            elif BytNr==8:#long long
                wfm_data=self.visa_handle.query_binary_values('curve?', datatype='q',is_big_endian=is_big_endian)
                self.status_print()
        elif  BnFmt=='RP' :#| DataEncdg=='SRP':#positive integer
            if BytNr==1:#unsigned char
                wfm_data=self.visa_handle.query_binary_values('curve?', datatype='B',is_big_endian=is_big_endian)
                self.status_print()
            elif BytNr==2:#unsigned short
                wfm_data=self.visa_handle.query_binary_values('curve?', datatype='H',is_big_endian=is_big_endian)  
                self.status_print() 
            # elif BytNr==4:#unsigned int, optionally long (not existing)
            #     wfm_data=self.visa_handle.query_binary_values('curve?', datatype='I')
                # what is the difference between int and long
            elif BytNr==8:#unsigned long long
                wfm_data=self.visa_handle.query_binary_values('curve?', datatype='Q',is_big_endian=is_big_endian)
                self.status_print()
        elif  BnFmt=='FP':# | DataEncdg=='SFP': #floating point 
            #The FPBinary argument is only applicable to math waveforms or ref
            #waveforms saved from math waveforms.
            # if BytNr==1:#unsigned char
            #     wfm_data=self.visa_handle.query_binary_values('curve?', datatype='B')
            # elif BytNr==2:#unsigned short
            #     wfm_data=self.visa_handle.query_binary_values('curve?', datatype='H')   
            if BytNr==4:#unsigned int, optionally long 
                 wfm_data=self.visa_handle.query_binary_values('curve?', datatype='f',is_big_endian=is_big_endian)
                 self.status_print()
            #     # what is the difference between int and long
            # elif BytNr==8:#unsigned long long
            #     wfm_data=self.visa_handle.query_binary_values('curve?', datatype='Q')
        else:
            self.status_print()
            print('Illegal Bn_Fmt obtained!')
        wfm_data=np.array(wfm_data)
        n_x=np.arange(0,len(wfm_data))

        # N=len(wfm_data)
        X=x0+x_incr*(n_x-pt_off)
        Y=y0+y_mult*(wfm_data-y_off)
        plt.plot(X,Y)
        plt.xlabel('Time '+x_unit)
        plt.ylabel('Voltage '+y_unit)
        plt.show()
    def status_print(self):

        DataEncdg=self.DataEncdg
        BnFmt=self.WfmoutpreBnFmt
        BytNr=self.WfmoutpreBytNr
        print(DataEncdg)
        print(BnFmt)
        print(BytNr)
        # print('YYY')

    
# ch1 = TektronixDSA70804B('test', address='TCPIP::192.168.1.200', channel_number = 1)
# ch1.VerticalPosition = 500e-3
# ch1.HorizontalPosition = 65
# #obj.write('HORizontal:MODE:SAMPLERate 2e9')
# print(ch1.VerticalPosition)
# print(ch1.HorizontalPosition)

# data = ch1.ask('CURVe?')

# print(data)
if __name__ == '__main__':
    obj = TektronixDSA70804B('test', address='TCPIP::192.168.1.200')
    a=0

# #obj.ask('DATA:STOP?')