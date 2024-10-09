import time
from collections import OrderedDict
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from qcodes import validators as vals
from qcodes.instrument import Instrument, VisaInstrument, InstrumentChannel
from sqdtoolz.Utilities.FileIO import FileIOWriter

# from qcodes.instrument_drivers.tektronix import TektronixDSA70000 


class RS_FSV_SAZChannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, channel:int) -> None:
        super().__init__(parent, name)
        self.channel = channel
        self._parent = parent     
class SA_RS_FSV(VisaInstrument):
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
            'format_data', label = 'Format Data', unit = 'a.u.',
            get_cmd='format:data?',
            get_parser = str,
            set_cmd = 'format:data {}',
            vals=vals.Enum('ascii','real,32'),
            initial_value='real,32'
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
        'sense_frequency_center', label = 'Sense Frequency Center', unit = 'Hz',get_cmd='sense:frequency:center?',get_parser=float,set_cmd = 'sense:frequency:center {}',vals=vals.Numbers()
        )
        # set the frequency span
        self.add_parameter(
        'sense_frequency_span', label = 'Sense Frequency Span', unit = 'Hz.',get_cmd='sense:frequency:span?',get_parser=float,set_cmd = 'sense:frequency:span {}',vals=vals.Numbers()
        )

        self.add_parameter(
            'res_bandwidth', label = 'Resolution Bandwidth', unit = 'Hz',
            get_cmd='BAND:RES?',
            get_parser=float,
            set_cmd = 'BAND:RES {}',
            vals=vals.Numbers()
            )

        self.add_parameter(
            'sweep_points', label = 'Resolution Bandwidth', unit = 'Hz',
            get_cmd='SENS:SWE:POINts?',
            get_parser=int,
            set_cmd = 'SENS:SWE:POINts {}',
            vals=vals.Numbers(101, 32001)
            )

        self.add_parameter(
            'average_enable',
            docstring = 'Enables average',
            get_cmd = 'AVER?', 
            set_cmd = 'AVER {}',
            val_mapping = {True: 1, False: 0}
            )

        self.add_parameter(
            'average_count', label = 'Number of averages',
            get_cmd='AVER:COUN?',
            get_parser=int,
            set_cmd = 'AVER:COUN {}',
            vals=vals.Numbers()
            )

        self.add_parameter(
            'average_type', label = 'Number of averages',
            get_cmd='AVER:COUN?',
            get_parser=int,
            set_cmd = 'AVER:COUN {}',
            vals=vals.Enum('VID', 'LIN', 'POW'),    #LIN means average first then take log, POW is the reverse...
            initial_value='LIN'
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


    @property
    def FrequencyStart(self):        
        return self.sense_frequency_start()
    @FrequencyStart.setter
    def FrequencyStart(self,val):
        self.sense_frequency_start(val)
    @property
    def FrequencyEnd(self):        
        return self.sense_frequency_stop()
    @FrequencyEnd.setter
    def FrequencyEnd(self,val):
        self.sense_frequency_stop(val)   
    @property
    def FrequencyCentre(self):        
        return self.sense_frequency_center()
    @FrequencyCentre.setter
    def FrequencyCentre(self,val):
        self.sense_frequency_center(val)  
    @property
    def FrequencySpan(self):        
        return self.sense_frequency_span()
    @FrequencySpan.setter
    def FrequencySpan(self,val):
        self.sense_frequency_span(val)

    @property
    def Bandwidth(self):
        return self.res_bandwidth()
    @Bandwidth.setter
    def Bandwidth(self, val):
        self.res_bandwidth(val)
    @property
    def SweepPoints(self):
        return self.sweep_points()
    @SweepPoints.setter
    def SweepPoints(self, val):
        self.sweep_points(val)

    @property
    def AveragesEnable(self):
        return self.average_enable() == '1'
    @AveragesEnable.setter
    def AveragesEnable(self, val):
        if (val):
            self.write('AVER ON')
        else:
            self.write('AVER OFF')
    @property
    def AveragesNum(self):
        return self.average_count()
    @AveragesNum.setter
    def AveragesNum(self, val):
        self.average_count(val)

    def get_data(self, **kwargs):
        self.write('INIT:CONT OFF')

        #Restart and initiate the sweep and block all subsequent commands...
        self.ask('ABOR;INIT:IMM;*OPC?')

        wfm_data = self.visa_handle.query_binary_values('trace:data? trace1', datatype='f', is_big_endian=False)
        wfm_x = self.visa_handle.query_binary_values('TRACe:DATA:X? TRACE1', datatype='f', is_big_endian=False)

        ret_data = {
            'parameters' : ['Frequency'],
            'data' : {},
            'parameter_values' : {}
            }

        ret_data['data'][f'Power_dBm'] = np.array(wfm_data)
        ret_data['parameter_values']['Frequency'] = np.array(wfm_x)
        
        leProc = kwargs.get('data_processor', None)
        if leProc is not None:
            leProc.push_data(ret_data)
            return {'data': leProc.get_all_data()}
        return {'data': ret_data}



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

if __name__=='__main__':
    obj = SA_RS_FSV('test', address='TCPIP::192.168.1.150::INSTR')

    a=0       