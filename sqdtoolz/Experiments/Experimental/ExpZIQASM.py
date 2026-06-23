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

class ExpZIQASM(ExpZIqubit):   
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, qasm_file_path, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False

        kwargs['coordinate_system'] = kwargs.get('coordinate_system', 'RH')
        assert kwargs['coordinate_system'] in ['LH', 'RH'], "The 'coordinate_system' must be either LH or RH for left/right handed."

        self._poqasm = ParserOpenQASM(qasm_file_path, kwargs.pop('source_dirs', []))
        qubit_params = ScheduleParametersSoftQPUZI(hal_QPU)
        leSchedule = self._poqasm.create_schedule(qubit_params)
        # leTable = self._poqasm.tabulate_schedule(leSchedule, qubit_params)
        # self._poqasm.plot_schedule(leSchedule, qubit_params, 'output.html')

        super().__init__(name, expt_config, oqasm_scheduled_qubits, hal_QPU, qubit_ids, openqasm_schedule=leSchedule, **kwargs)

    def _post_process(self, data):
        pass

