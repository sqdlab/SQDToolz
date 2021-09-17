from sqdtoolz.Experiment import*
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.HAL.ACQvna import ACQvna

class ExpVNAEquations(Experiment):
    '''
    Experiment to get data from VNA setting equations on each of the traces.
    '''

    def __init__(self, name, expt_config, s_params, equations, **kwargs):
        super().__init__(name, expt_config)

        assert len(equations) >= len(s_params)
        assert isinstance(expt_config._hal_ACQ, ACQvna)

        self._equations = equations
        self._s_params = s_params
        self._instr_vna = expt_config._hal_ACQ._instr_vna
        self._expt_config.get_data = self.get_data

        self.pdiv = kwargs.pop('pdiv', 10)
        self.rlev = kwargs.pop('rlev', -40)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        return super()._run(file_path, sweep_vars, **kwargs)

    def get_data(self):
        x_var_name = 'frequency'
        if self._instr_vna.SweepMode == 'Power-1f':
            x_var_name = 'power'
        elif self._instr_vna.SweepMode == 'Time-1f':
            x_var_name = 'time'
        ret_data = {
                    'parameters' : ['repetition', x_var_name],
                    'data' : {},
                    'parameter_values' : {}
                }
        
        self._instr_vna._delete_all_measurements()
        self._instr_vna._display_window()

        for i, cur_s_param in enumerate(self._s_params):
            cur_s_str = f'S{cur_s_param[0]}{cur_s_param[1]}'
            cur_name = f'ch1_{cur_s_str}'
            self._instr_vna.write(f'CALC:PAR:EXT {cur_name}, {cur_s_str}')
            self._instr_vna.write(f'DISP:WIND:TRAC{i+1}:FEED {cur_name}')
            # self._instr_vna.write(f'CALC:PAR:MNUM {i+1}')
            # self._instr_vna.write(f'CALC:EQU:TEXT "{self._equations[i]}"')
            # assert int(self._instr_vna.ask(f'CALC:EQU:VAL?').strip()) == 1
            # self._instr_vna.write(f'CALC:EQU 1')
            self._instr_vna.write(f'DISP:WIND:TRACe{i+1}:Y:PDIV {self.pdiv}')
            self._instr_vna.write(f'DISP:WIND:TRACe{i+1}:Y:RLEV {self.rlev}')

        for i in range(len(self._equations)):
            if i >= len(self._s_params):
                self._instr_vna.write(f'CALC:PAR:EXT Tr{i}, S11')
                self._instr_vna.write(f'DISP:WIND:TRAC{i+1}:FEED Tr{i}')
                self._instr_vna.write(f'DISP:WIND:TRACe{i+1}:Y:PDIV {self.pdiv}')
                self._instr_vna.write(f'DISP:WIND:TRACe{i+1}:Y:RLEV {self.rlev}')

        #For each measurement, gather the trace data...
        x_var_name = 'frequency'
        if self._instr_vna.SweepMode == 'Power-1f':
            x_var_name = 'power'
        elif self._instr_vna.SweepMode == 'Time-1f':
            x_var_name = 'time'
        ret_data = {
                    'parameters' : [x_var_name],
                    'data' : {},
                    'parameter_values' : {}
                }
            
        self._instr_vna.write('FORM:DATA ASCii,0')
        self._instr_vna.write(f'MMEM:STOR:TRAC:FORM:SNP RI')

        self._instr_vna.write('ABORT')
        self._instr_vna.write('SENSE:SWEEP:MODE SINGLE')
        self._instr_vna.write('TRIG:SOUR IMM')
        self._instr_vna.write('INIT:IMM')
        self._instr_vna.ask('*OPC?')

        for i in range(len(self._equations)):
            self._instr_vna.write(f'CALC:PAR:MNUM {i+1}')
            self._instr_vna.write(f'CALC:EQU:TEXT "{self._equations[i]}"')
            assert int(self._instr_vna.ask(f'CALC:EQU:VAL?').strip()) == 1
            self._instr_vna.write(f'CALC:EQU 1')

        # for i, cur_s_param in enumerate(self._s_params):
        #     self._instr_vna.write(f'CALC:PAR:MNUM {i+1}')
        #     self._instr_vna.write(f'CALC:EQU:TEXT "{self._equations[i]}"')
        #     assert int(self._instr_vna.ask(f'CALC:EQU:VAL?').strip()) == 1
        #     self._instr_vna.write(f'CALC:EQU 1')

        self._instr_vna.write('ABORT')
        self._instr_vna.write('SENSE:SWEEP:MODE GROUPS')
        self._instr_vna.write(f'SENSE:SWEEP:GROUPS:COUNT {self._instr_vna.NumRepetitions}')

        while self._instr_vna.ask('SENSE:SWEEP:MODE?').strip() == 'GRO':
            time.sleep(10e-3)

        cur_meas_traces = self._instr_vna.ask('CALC:PAR:CAT:EXT?').strip('"').split(',')
        assert len(cur_meas_traces) >= 2 and len(cur_meas_traces) % 2 == 0, "There appears to be no valid traces/measurements upon which to measure on the VNA."
        b=iter(cur_meas_traces)
        cur_meas_traces = list(zip(b,b))

        for cur_meas_name, cur_meas in cur_meas_traces:
            self._instr_vna.write(f'CALC:PAR:SEL \'{cur_meas_name}\'')
            #Note that SDATA just means complex-valued...
            s_data_raw = self._instr_vna.ask('CALC:DATA? SDATA').split(',')
            s_data_raw = np.array(list(map(float, s_data_raw)))
            ret_data['data'][f'{cur_meas}_real'] = s_data_raw[::2]
            ret_data['data'][f'{cur_meas}_imag'] = s_data_raw[1::2]
        freq_data_raw = self._instr_vna.ask('CALC:X?').split(',')
        ret_data['parameter_values'][x_var_name] = np.array(list(map(float, freq_data_raw)))
        return ret_data