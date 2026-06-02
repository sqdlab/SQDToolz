import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.WaveformGeneric import *
from sqdtoolz.HAL.WaveformSegments import *
from sqdtoolz.Utilities.DataFitting import *
from sqdtoolz.Experiments.Experimental.ExpCalibGE import *
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
import json
from sqdtoolz.Experiments.Experimental.ZI import single_qubit_gates_sweep
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
from sqdtoolz.Utilities.ParserOpenQASM import ParserOpenQASM

class ExpZIQASM(ExpZIqubit):   
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, qasm_file_path, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False

        kwargs['coordinate_system'] = kwargs.get('coordinate_system', 'RH')
        assert kwargs['coordinate_system'] in ['LH', 'RH'], "The 'coordinate_system' must be either LH or RH for left/right handed."

        self._poqasm = ParserOpenQASM(qasm_file_path)
        self._poqasm.compiled_operations

        kwargs['gate_lists'] = []
        for cur_seq in self._gate_seqs:
            kwargs['gate_lists'].append([cur_seq]*len(qubit_ids))

        super().__init__(name, expt_config, single_qubit_gates_sweep, hal_QPU, qubit_ids, **kwargs)

    def _post_process(self, data):
        pass

