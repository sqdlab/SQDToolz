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

        num_qasm_qubits = len(self._leSchedule['qubit_mappings'])
        assert num_qasm_qubits <= len(qubit_ids), f"The QASM script needs {num_qasm_qubits} while only {len(qubit_ids)} qubits have been specified."
        mapping = {x:x for x in range(len(qubit_ids))}

        super().__init__(name, expt_config, oqasm_scheduled_qubits, hal_QPU, qubit_ids, openqasm_schedule=self._leSchedule, **kwargs)
        self._args['qubit_mapping'] = mapping

    def get_qubit_regs(self):
        return [x for x in self._leSchedule['qubit_mappings']]

    def set_qubit_reg_to_ZI_mappings(self, mapping:dict):
        """
        Give as key-value pairs where key is a key from get_qubit_regs and value is the name (only string-based name allowed here) of the ZI-Qubit object...
        """
        num_qasm_qubits = len(self._leSchedule['qubit_mappings'])
        assert num_qasm_qubits == len(mapping), f"The QASM script has {num_qasm_qubits} qubits that need to be mapped onto the hardware, the provided mapping specifies {len(mapping)} qubits."
        
        leQubitNames = [self._hal_QPU.get_qubit_obj(x).Name for x in self._qubit_ids] #Still allowing integer/string-based indexing on the qubit_ids...

        final_mapping = {}
        for m,cur_qubit_reg in enumerate(self._leSchedule['qubit_mappings']):
            assert cur_qubit_reg in mapping, f"The qubit register {cur_qubit_reg} not present in the supplied mapping."
            assert mapping[cur_qubit_reg] in leQubitNames, f"Qubit by name {mapping[cur_qubit_reg]} does not exist in the qubits supplied in qubit_ids when initialising ExpZIQASM..."
            final_mapping[m] = leQubitNames.index( mapping[cur_qubit_reg] )
        self._args['qubit_mapping'] = final_mapping

    def _run(self, file_path, sweep_vars=[], **kwargs):
        # leTable = self._poqasm.tabulate_schedule(leSchedule, qubit_params)
        self._poqasm.plot_schedule(self._leSchedule, self._qasm_qubit_params, file_path + 'compiled_qasm_schedule.html')

        self._poqasm.check_ZI_compatibility(self._leSchedule, self._qasm_qubit_params, **kwargs)

        super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        pass

