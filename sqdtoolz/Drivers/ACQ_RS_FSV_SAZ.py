import time
from collections import OrderedDict
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from qcodes import validators as vals
from qcodes.instrument import Instrument, VisaInstrument, InstrumentChannel
# from qcodes.instrument_drivers.tektronix import TektronixDSA70000 


class RS_FSV_SAZChannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, channel:int) -> None:
        super().__init__(parent, name)
        self.channel = channel
        self._parent = parent     
class RS_FSV_SAZ(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=60, **kwargs)
        self.PowerUnit='dBm'
        # Go to Remote Controll
        self.add_parameter( 
        'gtr', label = 'GTR', unit = 'a.u.', set_cmd = '{}',vals=vals.Enum('gtr')
        )      
        # the dispaly control during remote program exectution   
        self.add_parameter(
        'system_display_update', label = 'System Display Update', unit = 'a.u.', get_cmd='SYSTem:DISPlay:UPDate?', get_parser = int, set_cmd = 'SYSTem:DISPlay:UPDate {}',vals=vals.Enum('on','off')
        )      

        # setting and query the data format to the tranferred
        self.add_parameter(
        'format_data', label = 'Format Data', unit = 'a.u.', get_cmd='format:data?', get_parser = str,set_cmd = 'format:data {}',vals=vals.Enum('ascii','real,32')
        )
        # the power unit of the y axis
        self.add_parameter(
        'calculate_unit_power', label = 'Calculate Unit Power', unit = 'a.u.',get_cmd='CALCulate:UNIT:POWer?',get_parser = str,set_cmd = 'CALCulate:UNIT:POWer {}',vals=vals.Enum('dBm','V','A','W','dBpW','watt','dBuV','dBmV','volt','dBuA','ampere')
        )
        # autoset all
        self.add_parameter(
        'sense_adjust_all', label = 'Sense Adjust All', unit = 'a.u.',set_cmd = 'sense:adjust:{}',vals=vals.Enum('all')
        )
        # set the center frequency
        self.add_parameter(
        'sense_frequency_center', label = 'Sense Frequency Center', unit = 'a.u.',get_cmd='sense:frequency:center?',get_parser=float,set_cmd = 'sense:frequency:center {}',vals=vals.Numbers()
        )
        # set the frequency span
        self.add_parameter(
        'sense_frequency_span', label = 'Sense Frequency Span', unit = 'a.u.',get_cmd='sense:frequency:span?',get_parser=float,set_cmd = 'sense:frequency:span {}',vals=vals.Numbers()
        )
        # set the full span0-30 GHz
        self.add_parameter(
        'sense_frequency_span_full', label = 'Sense Frequency Span Full', unit = 'a.u.',set_cmd = 'sense:frequency:span:{}',vals=vals.Enum('full')
        )
        # set the start frequency
        self.add_parameter(
        'sense_frequency_start', label = 'Sense Frequency Start', unit = 'a.u.',get_cmd='sense:frequency:start?', get_parser=float, set_cmd = 'sense:frequency:start {}',vals=vals.Numbers()
        )
        self.add_parameter(
        'sense_frequency_stop', label = 'Sense Frequency Stop', unit = 'a.u.',get_cmd='sense:frequency:stop?', get_parser=float, set_cmd = 'sense:frequency:stop {}',vals=vals.Numbers()
        )

        self.add_parameter(
        'sense_roscillator_external_frequency', label = 'Sense Roscillator External Frequency', unit = 'Hz',get_cmd='SENSe:ROSCillator:EXTernal:FREQuency?', get_parser=float, set_cmd = 'SENSe:ROSCillator:EXTernal:FREQuency {}',vals=vals.Numbers(1e6,20e6)#1-20MHz, default unit,MHz
        )

        self.add_parameter(
        'sense_roscillator_source', label = 'Sense Roscillator Source', unit = 'a.u.',get_cmd='SENSe:ROSCillator:SOURce?', get_parser=str, set_cmd = 'SENSe:ROSCillator:SOURce {}',vals=vals.Enum('internal','external','eauto') #EAUTo The external reference is used as long as it is available, then the instrument switches to the internal reference
        )


    def wfm_plot(self):
        wfm_data=self.wfm_data
        n_x=self.wfm_x
        plt.plot(n_x,wfm_data)
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Power (%s)'%self.CalculateUnitPower)

    @property
    def wfm_data(self):
        data_format=self.FormatData
        if data_format=='ASC,0':
            wfm_data_=self.visa_handle.query_ascii_values('trace:data? trace1')
            return np.array(wfm_data_)
        elif data_format=='REAL,32':
            wfm_data_=self.visa_handle.query_binary_values('trace:data? trace1', datatype='f', is_big_endian=False)
            return np.array(wfm_data_)
        else:
            print('Data format: %s'%data_format)            
            raise Exception('Invalid data format')
    @property
    def wfm_x(self):
        data_format=self.FormatData
        if data_format=='ASC,0':
            wfm_x_=self.visa_handle.query_ascii_values('TRACe:DATA:X? TRACE1')
            return np.array(wfm_x_)
        elif data_format=='REAL,32':
            wfm_x_=self.visa_handle.query_binary_values('TRACe:DATA:X? TRACE1', datatype='f', is_big_endian=False)
            return np.array(wfm_x_)
        else:
            print('Data format: %s'%data_format)            
            raise Exception('Invalid data format')        
    @property 
    def GTR(self):
        return
    @GTR.setter
    def GTR(self,val):
        self.gtr(val)

    @property 
    def SystemDisplayUpdate(self):
        return self.system_display_update()
    @SystemDisplayUpdate.setter
    def SystemDisplayUpdate(self,val):
        self.system_display_update(val)

    @property 
    def FormatData(self):
        return self.format_data()
    @FormatData.setter
    def FormatData(self,val):
        self.format_data(val)
    
    @property 
    def CalculateUnitPower(self):
        pw_unit=self.calculate_unit_power()
        if  pw_unit.casefold()=='DBM'.casefold():
            pw_unit='dBm'
        elif pw_unit.casefold()=='V'.casefold():
            pw_unit='V'
        elif pw_unit.casefold()=='A'.casefold():
            pw_unit='A'
        elif pw_unit.casefold()=='dBpW'.casefold():
            pw_unit='dBpW'
        elif pw_unit.casefold()=='watt'.casefold():
            pw_unit='watt'        
        elif pw_unit.casefold()=='dBuV'.casefold():
            pw_unit='dBuV'
        elif pw_unit.casefold()=='dBmV'.casefold():
            pw_unit='dBmV'
        elif pw_unit.casefold()=='volt'.casefold():
            pw_unit='volt'
        elif pw_unit.casefold()=='dBuA'.casefold():
            pw_unit='dBuA'
        elif pw_unit.casefold()=='ampere'.casefold():
            pw_unit='ampere'   
        else:
            raise Exception('Invalid power unit!')
        return pw_unit
    @CalculateUnitPower.setter
    def CalculateUnitPower(self,val):
        self.calculate_unit_power(val)

    @property
    def SenseAdjustAll(self):
        return
    @SenseAdjustAll.setter
    def SenseAdjustAll(self,val):
        self.sense_adjust_all(val)

    @property
    def SenseFrequencyCenter(self):        
        return obj.sense_frequency_center()
    @SenseFrequencyCenter.setter
    def SenseFrequencyCenter(self,val):
        self.sense_frequency_center(val)  
    
    @property
    def SenseFrequencySpan(self):        
        return obj.sense_frequency_span()
    @SenseFrequencySpan.setter
    def SenseFrequencySpan(self,val):
        self.sense_frequency_span(val)   

    @property
    def SenseFrequencySpanFull(self):        
        return 
    @SenseFrequencySpanFull.setter
    def SenseFrequencySpanFull(self,val):
        self.sense_frequency_span_full(val)  

    @property
    def SenseFrequencyStart(self):        
        return obj.sense_frequency_start()
    @SenseFrequencyStart.setter
    def SenseFrequencyStart(self,val):
        self.sense_frequency_start(val)   

    @property
    def SenseFrequencyStop(self):        
        return obj.sense_frequency_stop()
    @SenseFrequencyStop.setter
    def SenseFrequencyStop(self,val):
        self.sense_frequency_stop(val)   

    @property
    def SenseRoscillatorExternalFrequency(self):        
        return obj.sense_roscillator_external_frequency()
    @SenseRoscillatorExternalFrequency.setter
    def SenseRoscillatorExternalFrequency(self,val):
        self.sense_roscillator_external_frequency(val) 

    @property
    def SenseRoscillatorSource(self):        
        return obj.sense_roscillator_source()
    @SenseRoscillatorSource.setter
    def SenseRoscillatorSource(self,val):
        self.sense_roscillator_source(val)                   

if __name__=='__main__':
    obj = RS_FSV_SAZ('test', address='TCPIP::192.168.1.150::INSTR')
    a=0       