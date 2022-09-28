from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.ACQvna import ACQvna
import numpy as np
from pyvisa.errors import VisaIOError
import time

class ExpVNAPointTrigger(Experiment):
    '''
    Experiment to get data from VNA setting equations on each of the traces.
    '''

    def __init__(self, name, expt_config, **kwargs):
        super().__init__(name, expt_config)

        assert isinstance(expt_config._hal_ACQ, ACQvna)

        self._instr_vna = expt_config._hal_ACQ._instr_vna

        self.pdiv = kwargs.pop('pdiv', 10)
        self.rlev = kwargs.pop('rlev', -40)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        self.sweep_var = sweep_vars[-1]
        sweep_vars = sweep_vars[:-1]
        
        # replace the get_data with the custom get_data()
        old_get_data = self._expt_config.get_data
        self._expt_config.get_data = self.get_data
        ret_data = super()._run(file_path, sweep_vars, **kwargs)
        self._expt_config.get_data = old_get_data
        return ret_data


    def get_data(self):
        self.setup_vna()
        sweep_time = self._instr_vna.sweep_time.get()
        
        var = self.sweep_var[0]
        values = self.sweep_var[1]
        sleep_time = sweep_time/len(values)
        self._instr_vna.SweepPoints = len(values)
        for value in values:
            var.Value = value
            error = True
            while error:
                self._instr_vna.write('INIT:IMM')
                time.sleep(sleep_time)
                error = (int(self._instr_vna.ask('*ESR?')) > 0)
        timeout = self._instr_vna._get_visa_timeout()
        self._instr_vna._set_visa_timeout(1)
        time.sleep(10e-3)
        # assert self._instr_vna.ask('SENSE:SWEEP:MODE?').strip() == 'HOLD', 'Not enough points?'
        self._instr_vna._set_visa_timeout(timeout)
        
        return self.final_get_data(var, values)

    def setup_vna(self):
        assert self._instr_vna.SweepMode == 'Time-1f', 'Can only use CW Time mode'
        
        self._instr_vna.write('FORM:DATA ASCii,0')
        self._instr_vna.write(f'MMEM:STOR:TRAC:FORM:SNP RI')

        # self._instr_vna.write('STAT:OPER:DEF:USER1:ENAB 1')
        # self._instr_vna.write('STAT:OPER:DEF:USER1:MAP 0,260')

        self._instr_vna.write('ABORT')
        self._instr_vna.write('TRIG:SOUR MAN')
        self._instr_vna.write('TRIG:SCOP ACT')
        self._instr_vna.write('SENSe:SWEep:MODE SINGLE')
        self._instr_vna.write('SENSe:SWE:TRIG:MODE POINT')

    def final_get_data(self, var, values):
        ret_data = {
                    'parameters' : [var.Name],
                    'data' : {},
                    'parameter_values' : {var.Name: values}
                }
        
        #Just check what data traces are being measured at the moment just in case...
        cur_meas_traces = self._instr_vna.ask('CALC:PAR:CAT:EXT?').strip('"').split(',')
        assert len(cur_meas_traces) >= 2 and len(cur_meas_traces) % 2 == 0, "There appears to be no valid traces/measurements upon which to measure on the VNA."
        b=iter(cur_meas_traces)
        cur_meas_traces = list(zip(b,b))

        for cur_meas_name, cur_meas in cur_meas_traces:
            ret_data['data'][f'{cur_meas}_real'] = []
            ret_data['data'][f'{cur_meas}_imag'] = []

        for cur_meas_name, cur_meas in cur_meas_traces:
            self._instr_vna.write(f'CALC:PAR:SEL \'{cur_meas_name}\'')
            #Note that SDATA just means complex-valued...
            s_data_raw = self._instr_vna.ask('CALC:DATA? SDATA').split(',')
            s_data_raw = np.array(list(map(float, s_data_raw)))
            ret_data['data'][f'{cur_meas}_real'] = s_data_raw[::2]
            ret_data['data'][f'{cur_meas}_imag'] = s_data_raw[1::2]
        freq_data_raw = self._instr_vna.ask('CALC:X?').split(',')
        assert len(np.array(list(map(float, freq_data_raw)))) == len(values), f'Returned data is not same size as number of values for variable {var.Name}'

        self._instr_vna.write('SENSe:SWE:TRIG:MODE SWE')
        self._instr_vna.write('TRIG:SCOP ALL')

        return ret_data