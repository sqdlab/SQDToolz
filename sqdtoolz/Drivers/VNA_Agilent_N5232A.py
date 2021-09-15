import time
from collections import OrderedDict

import numpy as np
import pandas as pd
from qcodes import (
    MultiParameter, InstrumentChannel, VisaInstrument, validators as vals
)

#NOTE THAT THE MANUAL IS FOUND AT: http://na.support.keysight.com/pna/help/WebHelp9_42/help.htm
         
class VNA_Agilent_N5232A(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', **kwargs)
        self._data_processor = None
        #By default we are working with the channel number 1, so SENSe<cnum>: if all queries is just SENSe1: ...
        
        
        # Acquisition parameters
        self.add_parameter(
            'freq_start', label = 'Start frequency', unit = 'Hz',
            get_cmd = 'SENSe1:FREQuency:STARt?', get_parser = float,
            set_cmd = 'SENSe1:FREQuency:STARt {:f}', vals = vals.Numbers(1., 20e9))
        
        self.add_parameter(
            'freq_stop', label = 'Stop frequency', unit = 'Hz',
            get_cmd = 'SENSe1:FREQuency:STOP?', get_parser = float,
            set_cmd = 'SENSe1:FREQuency:STOP {:f}', vals = vals.Numbers(1., 20e9))
        
        self.add_parameter(
            'freq_center', label = 'Center frequency', unit = 'Hz',
            get_cmd = 'SENSe1:FREQuency:CENTer?', get_parser = float,
            set_cmd = 'SENSe1:FREQuency:CENTer {:f}', vals = vals.Numbers(1., 20e9))
        
        self.add_parameter(
            'freq_span', label = 'Frequency span', unit = 'Hz',
            get_cmd = 'SENSe1:FREQuency:SPAN?', get_parser = float,
            set_cmd = 'SENSe1:FREQuency:SPAN {:f}', vals = vals.Numbers(0., 10e9))
        
        self.add_parameter(
            'freq_CW', label = 'CW frequency', unit = 'Hz',
            docstring = '''Sets the frequency of the single-frequency continuous wave sweep.
            This is the frequency which will be used for CW or POWer sweeps.''',
            get_cmd = 'SENS:FREQ:CW?', get_parser = float,
            set_cmd = 'SENS:FREQ:CW {:f}', vals = vals.Numbers(0., 20e9))
        
        self.add_parameter(
            'power_start', label = 'Start power',
            unit = 'dB', docstring = 'Start power for the power sweep mode',
            get_cmd = 'SOUR:POW:STAR?', get_parser = float,
            set_cmd = 'SOUR:POW:STAR {:f}', vals = vals.Numbers(-30., 30))
        
        self.add_parameter(
            'power_stop', label = 'Stop power',
            unit = 'dB', docstring = 'Stop power for the power sweep mode',
            get_cmd = 'SOUR:POW:STOP?', get_parser = float,
            set_cmd = 'SOUR:POW:STOP {:f}', vals = vals.Numbers(-30., 30))
        
        self.add_parameter(
            'output',
            docstring = '''Turns the output power ON or OFF''',
            get_cmd = 'OUTP?', 
            set_cmd = 'OUTP {}',
            val_mapping = {'ON': 1, 'OFF': 0, True: 1, False: 0, 1: 1, 0: 0})
            #val_mapping = OrderedDict((True, 1), (False, 0), (1, 1), (0, 0), ('ON', 1), ('OFF', 0)))
        
        self.add_parameter(
            'power', label = 'power',  unit = 'dB',
            docstring = '''Sets the source power''',
            get_cmd = 'SOUR:POW?', get_parser = float,
            set_cmd = 'SOUR:POW {:f}', vals = vals.Numbers(-60., 20.))
            
        self.add_parameter(
            'averaging',
            docstring = '''Averaging ON/OFF''',
            get_cmd = 'SENS:AVER?',
            set_cmd = 'SENS:AVER {}', val_mapping = {True: 1, False: 0})
            
        self.add_parameter(
            'averaging_mode',
            docstring = '''
            Sets the type of averaging to perform: Point or Sweep.
            POINT - Averaging measurements are made on each data point before stepping to the next data point.
            SWEEP - Averaging measurements are made on subsequent sweeps until the required number of averaging sweeps are performed.
            Default setting is sweep.
            ''',
            get_cmd = 'SENS:AVER:MODE?', 
            set_cmd = 'SENS:AVER:MODE {}', val_mapping = {'point': 'POIN', 'sweep': 'SWE'})
            
        self.add_parameter(
            'averages', label = 'averages',
            docstring = '''Sets the number of averages. Averaging should be True as well.''',
            get_cmd = 'SENS:AVER:COUN?', get_parser = int,
            set_cmd = 'SENS:AVER:COUN {:d}', vals = vals.Ints(1, 1<<16))
        
        self.add_parameter(
            'sweep_points', label = 'Points in sweep',
            get_cmd = 'SENS:SWE:POIN?', get_parser = int,
            set_cmd = 'SENS:SWE:POIN {:d}', vals = vals.Ints(1, 32001))
        
        self.add_parameter(
            'sweep_time', unit = 's',
            docstring = '''The time in seconds required to complete a single sweep.
            Setting to zero will result in minimum possible time required to run the sweep.
            The setting is valid for any sweep type.''',
            get_cmd = 'SENS:SWE:TIME?', get_parser = float,
            set_cmd = 'SENS:SWE:TIME {:f}', vals = vals.Numbers(0, 86400))
        
        self.add_parameter(
            'bandwidth', label = 'bandwidth',
            docstring = '''Sets the measurement bandwidth in Hz, working range is a list of values from 1Hz to 15MHz.
            Automatically rounds the input value to the closest value from the list.''',
            get_cmd = 'SENS:BAND?', get_parser = float,
            set_cmd = 'SENS:BAND {:f}', vals = vals.Numbers(1, 15e6))
        
        self.add_parameter(
            'sweep_type',
            docstring = '''Type of the sweep.''',
            get_cmd = 'SENS:SWE:TYPE?',
            set_cmd = 'SENS:SWE:TYPE {}', vals = vals.Enum('LIN', 'LOG', 'POW', 'CW', 'SEGM', 'PHAS'))
            
        self.add_parameter(
            'trigger',
            docstring = '''Mode of the internal trigger of the instrument: hold, continuous, groups or single.''',
            get_cmd = 'SENS:SWE:MODE?',
            set_cmd = 'SENS:SWE:MODE {}', vals = vals.Enum('hold', 'cont', 'gro', 'sing'))
            
        self.add_parameter(
            'trigger_source',
            docstring = '''Source of the internal trigger of the instrument: EXTernal, IMMediate, or MANual.''',
            get_cmd = 'TRIG:SOUR?',
            set_cmd = 'TRIG:SOUR {}', vals = vals.Enum('EXT', 'IMM', 'MAN'))
        
        self._num_repetitions = 1
        self._segment_freqs = []

        # *IDN?
        self.connect_message()

    @property
    def SupportedSweepModes(self):
        return ['Linear', 'Decade', 'Power-1f', 'Time-1f', 'Segmented']

    @property
    def SweepMode(self):
        if self.sweep_type() == 'LIN':
            return 'Linear'
        elif self.sweep_type() == 'LOG':
            return 'Decade'
        elif self.sweep_type() == 'POW':
            return 'Power-1f'
        elif self.sweep_type() == 'CW':
            return 'Time-1f'
        elif self.sweep_type() == 'SEGM':
            return 'Segmented'
        else:
            #Some other mode - just set it to default Linear...
            self.sweep_type('LIN')
            return 'Linear'
    @SweepMode.setter
    def SweepMode(self, new_mode):
        assert new_mode in self.SupportedSweepModes, f"Mode {new_mode} is invalid for this VNA."
        if new_mode == 'Linear':
            self.sweep_type.set('LIN')
        elif new_mode == 'Decade':
            self.sweep_type.set('LOG')
        elif new_mode == 'Power-1f':
            self.sweep_type.set('POW')
        elif new_mode == 'Time-1f':
            self.sweep_type.set('CW')
        elif new_mode == 'Segmented':
            self.sweep_type.set('SEGM')

    @property
    def FrequencyStart(self):
        return self.freq_start()
    @FrequencyStart.setter
    def FrequencyStart(self, val):
        self.freq_start(val)

    @property
    def FrequencyEnd(self):
        return self.freq_stop()
    @FrequencyEnd.setter
    def FrequencyEnd(self, val):
        self.freq_stop(val)

    @property
    def FrequencyCentre(self):
        return self.freq_center()
    @FrequencyCentre.setter
    def FrequencyCentre(self, val):
        self.freq_center(val)

    @property
    def FrequencySpan(self):
        return self.freq_span()
    @FrequencySpan.setter
    def FrequencySpan(self, val):
        self.freq_span(val)

    @property
    def Power(self):
        return self.power()
    @Power.setter
    def Power(self, val):
        self.power(val)

    @property
    def SweepPoints(self):
        return self.sweep_points()
    @SweepPoints.setter
    def SweepPoints(self, val):
        self.sweep_points(val)

    @property
    def AveragesNum(self):
        return self.averages()
    @AveragesNum.setter
    def AveragesNum(self, val):
        self.averages(val)

    @property
    def AveragesEnable(self):
        return self.averaging()
    @AveragesEnable.setter
    def AveragesEnable(self, val):
        self.averaging(val)

    @property
    def Bandwidth(self):
        return self.bandwidth()
    @Bandwidth.setter
    def Bandwidth(self, val):
        self.bandwidth(val)

    @property
    def NumRepetitions(self):
        return self._num_repetitions
    @NumRepetitions.setter
    def NumRepetitions(self, val):
        self._num_repetitions = val


    @property
    def FrequencySingle(self):
        return self.freq_CW()
    @FrequencySingle.setter
    def FrequencySingle(self, val):
        self.freq_CW(val)

    @property
    def PowerStart(self):
        return self.power_start()
    @PowerStart.setter
    def PowerStart(self, val):
        self.power_start(val)

    @property
    def PowerEnd(self):
        return self.power_stop()
    @PowerEnd.setter
    def PowerEnd(self, val):
        self.power_stop(val)


    def setup_segmented(self, segment_freqs):
        self._segment_freqs = segment_freqs[:]
        #Clear all segments
        self.write("SENS:FOM:RANG:SEGM:DEL:ALL")
        #Initialise segments
        for segment in range(len(segment_freqs)):
            self.write(f"SENS:SEGM{segment+1}:ADD")
            self.write(f"SENS:SEGM{segment+1}:STAT on")
        #Now that segments exist, activate segmented-mode...
        self.SweepMode = 'Segmented'
        #Set segments...
        for index, cur_seg in enumerate(segment_freqs):
            freq_start, freq_end, freq_pts = cur_seg
            self.write(f"SENS:SEGM{index+1}:FREQ:START {freq_start} Hz")
            self.write(f"SENS:SEGM{index+1}:FREQ:STOP {freq_end} Hz")
            self.write(f"SENS:SEGM{index+1}:SWE:POIN {freq_pts}")

    def get_frequency_segments(self):
        return self._segment_freqs[:]

    def setup_measurements(self, ports_meas_src_tuples):
        self._delete_all_measurements()
        self._display_window()
        for i, cur_s_param in enumerate(ports_meas_src_tuples):
            cur_s_str = f'S{cur_s_param[0]}{cur_s_param[1]}'
            cur_name = f'ch1_{cur_s_str}'
            self.write(f'CALC:PAR:EXT {cur_name}, {cur_s_str}')
            self.write(f'DISP:WIND:TRAC{i+1}:FEED {cur_name}')

    def get_data(self):
        #Just check what data traces are being measured at the moment just in case...
        cur_meas_traces = self.ask('CALC:PAR:CAT:EXT?').strip('"').split(',')
        assert len(cur_meas_traces) >= 2 and len(cur_meas_traces) % 2 == 0, "There appears to be no valid traces/measurements upon which to measure on the VNA."
        b=iter(cur_meas_traces)
        cur_meas_traces = list(zip(b,b))
        #For each measurement, gather the trace data...
        x_var_name = 'frequency'
        if self.SweepMode == 'Power-1f':
            x_var_name = 'power'
        elif self.SweepMode == 'Time-1f':
            x_var_name = 'time'
        ret_data = {
                    'parameters' : ['repetition', x_var_name],
                    'data' : {},
                    'parameter_values' : {}
                }
        for cur_meas_name, cur_meas in cur_meas_traces:
            ret_data['data'][f'{cur_meas}_real'] = []
            ret_data['data'][f'{cur_meas}_imag'] = []

        #Strange behaviour when running the benchmark in the end is that ascii is the fastest at ~49ms per point (15 in total) while
        #bin32/bin64 are the same speed at ~59ms?!?! So there's no speed difference in transferring more data and yet it's faster to
        #transfer and encode ascii data?!
        mode = 'ascii'

        if mode == 'ascii':
            self.write('FORM:DATA ASCii,0')
            self.write(f'MMEM:STOR:TRAC:FORM:SNP RI')

            av_enabled = self.AveragesEnable
            for r in range(self.NumRepetitions):
                self.write('ABORT')
                self.trigger.set('cont')
                self.write('TRIG:SOUR IMM')
                if self.AveragesEnable:
                    self.clear_averages()
                    while not self._finished_averaging():
                        time.sleep(0.01)
                else:
                    self.write('TRIG:SOUR MAN')
                    try:
                        self._set_visa_timeout(len(cur_meas_traces)*self.sweep_time.get() + 5)
                    except AttributeError:
                        self._set_visa_timeout(self.sweep_time.get() + 5)
                    self.write('ABORT; :INIT:IMM')
                    self.ask('*OPC?')
                for cur_meas_name, cur_meas in cur_meas_traces:
                    self.write(f'CALC:PAR:SEL \'{cur_meas_name}\'')
                    #Note that SDATA just means complex-valued...
                    s_data_raw = self.ask('CALC:DATA? SDATA').split(',')
                    s_data_raw = np.array(list(map(float, s_data_raw)))
                    ret_data['data'][f'{cur_meas}_real'] += [ s_data_raw[::2] ]
                    ret_data['data'][f'{cur_meas}_imag'] += [ s_data_raw[1::2] ]
            freq_data_raw = self.ask('CALC:X?').split(',')
            ret_data['parameter_values'][x_var_name] = np.array(list(map(float, freq_data_raw)))
        elif mode == 'bin32':
            #Set data-type to be float-32 - can be 64 as well...
            self.write('FORM:DATA REAL,32')
            #Set output to be real-imaginary...
            self.write(f'MMEM:STOR:TRAC:FORM:SNP RI')

            av_enabled = self.AveragesEnable
            for r in range(self.NumRepetitions):
                self.write('ABORT')
                self.trigger.set('cont')
                self.write('TRIG:SOUR IMM')
                if av_enabled:
                    self.clear_averages()
                    while not self._finished_averaging():
                        time.sleep(0.01)
                else:
                    self.write('TRIG:SOUR MAN')
                    try:
                        self._set_visa_timeout(len(cur_meas_traces)*self.sweep_time.get() + 5)
                    except AttributeError:
                        self._set_visa_timeout(self.sweep_time.get() + 5)
                    self.write('ABORT; :INIT:IMM')
                    self.ask('*OPC?')
                for cur_meas_name, cur_meas in cur_meas_traces:
                    self.write(f'CALC:PAR:SEL \'{cur_meas_name}\'')
                    #Note that SDATA just means complex-valued...
                    s_data_raw = self.visa_handle.query_binary_values('CALC:DATA? SDATA', datatype=u'f')
                    ret_data['data'][f'{cur_meas}_real'] += [ s_data_raw[::2] ]
                    ret_data['data'][f'{cur_meas}_imag'] += [ s_data_raw[1::2] ]
            ret_data['parameter_values'][x_var_name] = self.visa_handle.query_binary_values('CALC:X?', datatype=u'f')
        elif mode == 'bin64':
            #Set data-type to be float-32 - can be 64 as well...
            self.write('FORM:DATA REAL,64')
            #Set output to be real-imaginary...
            self.write(f'MMEM:STOR:TRAC:FORM:SNP RI')

            av_enabled = self.AveragesEnable
            for r in range(self.NumRepetitions):
                self.write('ABORT')
                self.trigger.set('cont')
                self.write('TRIG:SOUR IMM')
                if av_enabled:
                    self.clear_averages()
                    while not self._finished_averaging():
                        time.sleep(0.01)
                else:
                    self.write('TRIG:SOUR MAN')
                    try:
                        self._set_visa_timeout(len(cur_meas_traces)*self.sweep_time.get() + 5)
                    except AttributeError:
                        self._set_visa_timeout(self.sweep_time.get() + 5)
                    self.write('ABORT; :INIT:IMM')
                    self.ask('*OPC?')
                for cur_meas_name, cur_meas in cur_meas_traces:
                    self.write(f'CALC:PAR:SEL \'{cur_meas_name}\'')
                    #Note that SDATA just means complex-valued...
                    s_data_raw = self.visa_handle.query_binary_values('CALC:DATA? SDATA', datatype=u'd')
                    ret_data['data'][f'{cur_meas}_real'] += [ s_data_raw[::2] ]
                    ret_data['data'][f'{cur_meas}_imag'] += [ s_data_raw[1::2] ]
            ret_data['parameter_values'][x_var_name] = self.visa_handle.query_binary_values('CALC:X?', datatype=u'd')

        for cur_meas_name, cur_meas in cur_meas_traces:
            ret_data['data'][f'{cur_meas}_real'] = np.vstack(ret_data['data'][f'{cur_meas}_real'])
            ret_data['data'][f'{cur_meas}_imag'] = np.vstack(ret_data['data'][f'{cur_meas}_imag'])
        
        if self._data_processor is not None:
            self._data_processor.push_data(ret_data)
            return self._data_processor.get_all_data()
        return ret_data

    def abort(self):
        '''Stops all sweeps and restarts the averaging.
        After the command is executed, measurements will continue as per trigger setting.'''
        self.write('ABORT')
    
    def _delete_all_measurements(self):
        '''Deletes all measurements on the PNA'''
        self.write('CALC:PAR:DEL:ALL')
    
    def _display_window(self):
        self.write('DISP:WIND ON')
        
    def Autoscale(self):
        '''Autoscales the output on the screen'''
        self.write('DISP:WIND:TRAC:Y:AUTO')
            
    def clear_averages(self):
        '''Clears and restarts averaging of the measurement data. Does NOT apply to point averaging.'''
        #Todo: do something if the averaging is in the point mode. Restart the measurement? Or just let the user decide.
        self.write('SENS:AVER:CLE')

    def _finished_averaging(self):
        return bool(int(self.ask('STATUS:OPER:AVERAGING?')))
            
    def IsFinishedMeasuring(self):
        '''Checks whether the current running measurement is finished.
        Currently works only in the averaging mode;
        In the single-measurement mode always waits until the measurement finishes and then returns True.'''
        if (self.averaging.get()):
            return self._finished_averaging()
        else:
            self._set_visa_timeout(self.sweep_time.get() + 5)
            return int(self.ask('*OPC?')) > 0
               
    def preset(self):
        '''Deletes all traces, measurements, and windows. In addition, resets the analyzer to factory defined default settings and creates a S11 measurement named "CH1_S11_1".'''
        self.write('system:preset')

    def shutdown(self):
        '''Remotely shuts down the instrument'''
        self.write('Diag:batch \'C:/shutdown.bat\'')
    
    def restart(self):
        '''Remotely reboots the instrument'''
        self.write('Diag:batch \'C:/restart.bat\'')


import matplotlib.pyplot as plt
import time

def runme():
    test_vna = VNA_Agilent_N5232A("test", 'TCPIP::192.168.1.202::INSTR')

    test_vna.FrequencyStart = 10e6
    test_vna.FrequencyEnd = 6e9

    test_vna.FrequencySingle = 500e6
    test_vna.SweepMode = 'Time-1f'
    x_var = 'time' #'power' #'frequency'

    test_vna.setup_segmented([(10e6,100e6,5), (500e6,1000e6,5), (1000e6,5000e6,5)])
    x_var = 'frequency'

    test_vna.setup_measurements([(1,2)])

    test_vna.SweepPoints = 801

    test_vna.AveragesEnable = False
    test_vna.AveragesNum = 8
    test_vna.Bandwidth = 100e3


    cur_time = time.time()
    test_vna.NumRepetitions = 200
    leData = test_vna.get_data()
    cur_time = time.time() - cur_time

    
    s23s = np.sqrt(leData['data']['S12_real']**2 + leData['data']['S12_imag']**2)
    plt.plot(leData['parameter_values'][x_var], s23s[0])
    # s22s = np.sqrt(leData['data']['S11_real']**2 + leData['data']['S11_imag']**2)
    # plt.plot(leData['parameter_values'][x_var], s22s[0])
    plt.show()
    input('Press ENTER')



if __name__ == '__main__':
    runme()
