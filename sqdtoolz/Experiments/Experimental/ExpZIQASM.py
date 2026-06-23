import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.WaveformGeneric import *
from sqdtoolz.HAL.WaveformSegments import *
from sqdtoolz.Utilities.DataFitting import *
from sqdtoolz.Experiments.Experimental.ExpCalibGE import *
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
import json
from sqdtoolz.Experiments.Experimental.ZI import oqasm_scheduled_qubits
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
from sqdtoolz.Utilities.OpenQASM.ParserOpenQASM import ParserOpenQASM, ScheduleParametersSoftQPUZI
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous

class ExpZIQASM(ExpZIqubit):   
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, qasm_file_path, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False

        kwargs['coordinate_system'] = kwargs.get('coordinate_system', 'RH')
        assert kwargs['coordinate_system'] in ['LH', 'RH'], "The 'coordinate_system' must be either LH or RH for left/right handed."

        self._poqasm = ParserOpenQASM(qasm_file_path, kwargs.pop('source_dirs', []), measure_label='QMEAS')
        self._qasm_qubit_params = ScheduleParametersSoftQPUZI(hal_QPU)
        self._leSchedule = self._poqasm.create_schedule(self._qasm_qubit_params)

        super().__init__(name, expt_config, oqasm_scheduled_qubits, hal_QPU, qubit_ids, openqasm_schedule=self._leSchedule, **kwargs)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        # leTable = self._poqasm.tabulate_schedule(leSchedule, qubit_params)
        self._poqasm.plot_schedule(self._leSchedule, self._qasm_qubit_params, file_path + 'compiled_qasm_schedule.html')

        #Perform simple checks before compilation
        leTable = self._poqasm.tabulate_schedule(self._leSchedule, self._qasm_qubit_params)
        leTableMeas = leTable[leTable['gate_type'].str.contains("QMEAS", na=False)]
        if len(leTableMeas) > 1:
            leTableMeas = leTableMeas.sort_values(by='start_time').reset_index(drop=True)
            ###################
            #Overlap check
            #
            #Apparently this exists as LabOneQ calculates the measurement final multiplexed pulse by summing all the
            #signals together. This aligns with the kernel and has a fixed length in memory - i.e. it could be theoretically
            #unbounded with cascading measurement pulses. Making them start at the same time places an upper bound - i.e.
            #the maximum allowed measurement time... 
            for m in range(len(leTableMeas)):
                for n in range(m + 1, len(leTableMeas)):
                    start_m, end_m = leTableMeas.loc[m, 'start_time'], leTableMeas.loc[m, 'end_time']
                    start_n, end_n = leTableMeas.loc[n, 'start_time'], leTableMeas.loc[n, 'end_time']
                    # Check for overlap: max(starts) < min(ends)
                    overlap = max(start_m, start_n) < min(end_m, end_n)
                    # Check condition 1: Overlap AND different start times
                    Miscellaneous
                    assert not (overlap and start_m != start_n), f"ZI HW limitation: overlapping measure pulses at {Miscellaneous.get_units(start_m)}s and {Miscellaneous.get_units(start_n)}s do not start at the same time."
            #
            ###################
            #Gap check
            #
            #Basically there must be about 20-30ns gap between multiple acquisitions...
            time_threshold = kwargs.get('min_buffer_between_acquisitions', 40e-9)
            for m in range(len(leTableMeas) - 1):   #It's a sorted list, so it can be checked sequentially...
                end_m = leTableMeas.loc[m, 'end_time']
                start_n = leTableMeas.loc[m+1, 'start_time']            
                # Check for non-overlap (gap exists)
                if end_m < start_n:
                    gap = start_n - end_m
                    # Check condition 2: Gap is small
                    assert gap >= time_threshold, f"ZI HW limitation: the gap between multiple non-overlapping measure pulses must be at least 20-30ns. Check gap between {Miscellaneous.get_units(end_m)}s and {Miscellaneous.get_units(start_n)}s."

        super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        pass

