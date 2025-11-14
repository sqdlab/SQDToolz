from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.ExperimentSpecification import ExperimentSpecification
from sqdtoolz.HAL.ZI.ZIbase import ZIbase
from sqdtoolz.Variable import VariableInternalTransient
from sqdtoolz.Utilities.FileIO import FileIODatalogger, FileIOReader
import time
import scipy.signal
import numpy as np
import laboneq.dsl.quantum

class SOFTqpu(HALbase, ZIbase):
    def __init__(self, hal_name, lab, **kwargs):
        #NOTE: the driver is presumed to be a single-pole many-throw switch (i.e. only one circuit route at a time).
        HALbase.__init__(self, hal_name)
        lab._register_HAL(self)
        self._lab=lab
        config_dict = kwargs.get('config_dict', {})        
        self._qubits = config_dict.get('Qubits', [])
        self._qubit_couplings = config_dict.get('QubitCouplings', [])

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict=config_dict["instrument"])

    def add_qubit(self, hal_obj:HALbase|ExperimentSpecification):
        self._qubits.append(self._lab._resolve_sqdobj_tree(hal_obj))
    
    def add_qubit_coupling(self, qubit1: str|int, qubit2: str|int, hal_obj:str|HALbase):
        qubit1 = self._resolve_qubit_index(qubit1)
        qubit2 = self._resolve_qubit_index(qubit2)
        if isinstance(hal_obj, HALbase):
            self._qubits.append((qubit1, qubit2, self._lab._resolve_sqdobj_tree(hal_obj)))
        else:
            self._qubits.append((qubit1, qubit2, hal_obj))

    def get_qubit(self, qubit_id: str|int):
        return self._qubits[self._resolve_qubit_index(qubit_id)]
    
    def get_qubit_couplings(self, qubit1: str|int, qubit2: str|int):
        qubit1 = self._resolve_qubit_index(qubit1)
        qubit2 = self._resolve_qubit_index(qubit2)
        ret_cpls = []
        for cur_cpl in self._qubit_couplings:
            if qubit1 == cur_cpl[0] and qubit2 == cur_cpl[1] or qubit1 == cur_cpl[1] and qubit2 == cur_cpl[0]:
                ret_cpls.append(cur_cpl[2])
        return ret_cpls

    def get_ZI_parameters(self):
        leQubits = []
        leQops = []
        for m in range(len(self._qubits)):
            cur_qubit = self._lab._get_resolved_obj(self._qubits[m])
            assert isinstance(cur_qubit, ZIbase), f"The qubit on index {m} is not a ZI-compatible qubit HAL."
            qubit, qop = cur_qubit.get_ZI_parameters()
            leQubits.append(qubit)
            leQops.append(qop)
            qop.detach_qpu()
        leQPU = laboneq.dsl.quantum.QPU(leQubits, quantum_operations=leQops[0]) #TODO: Look up why this doesn't work with a list properly...
        for m in range(len(self._qubit_couplings)):
            qubit1 = self._qubits[self._qubit_couplings[m][0]].Name
            qubit2 = self._qubits[self._qubit_couplings[m][1]].Name
            if isinstance(self._qubit_couplings[m][2], str):
                leQPU.topology.add_edge(self._qubit_couplings[m][2], qubit1, qubit2)
            else:
                cur_cpl = self._lab._get_resolved_obj(self._qubit_couplings[m][2])
                assert isinstance(hal_obj, ZIbase), f"The qubit coupling {cur_cpl.Name} between qubits {qubit1} and {qubit2} is not a ZI-compatible qubit HAL."
                leQPU.topology.add_edge(cur_cpl.Name, qubit1, qubit2, quantum_elements=cur_cpl.get_ZI_parameters())
        return leQPU, leQubits

    def _resolve_qubit_index(self, qubit_id):
        if isinstance(qubit_id, int):
            assert qubit_id < len(self._qubits) and qubit_id >= 0, f"Qubit index {qubit_id} is out of range given the number of qubits."
            return qubit_id
        for m in range(len(self._qubits)):
            cur_qubit = self._lab._get_resolved_obj(self._qubits[m])
            if cur_qubit.Name==qubit_id:
                return m
        assert False, f"Qubit \"{qubit_id}\" does not exist."


    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__,
            'Qubits': self._qubits,
            'QubitCouplings': self._qubit_couplings
            }
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a SoQPU with a configuration that is of type ' + dict_config['Type']
        self._qubits = dict_config.get('Qubits', [])
        self._qubit_couplings = dict_config.get('QubitCouplings', [])
