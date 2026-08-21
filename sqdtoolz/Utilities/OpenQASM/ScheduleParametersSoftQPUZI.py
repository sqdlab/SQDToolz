from sqdtoolz.Utilities.OpenQASM import ScheduleParametersBase, QASMCompatibleQubitSingle
from sqdtoolz.HAL.SOFTqpu import SOFTqpu


class ScheduleParametersSoftQPUZI(ScheduleParametersBase):
    def __init__(self, softQPU_ZI:SOFTqpu, mapping:dict):
        self._qpu = softQPU_ZI
        self.mapping = mapping  #This maps the physical qubit index in QASM onto the softQPU IDs...
    
    def get_phys_qubit_ids(self) -> list[int]:
        return [x for x in self.mapping]

    def get_duration(self, phys_qubit_index:int, gate_type:str|list|tuple) -> float:
        if isinstance(gate_type, (list,tuple)):
            if gate_type[0] == 'D':
                return gate_type[1]
            elif gate_type[0] == 'Measure':
                return self.get_measurement_params(phys_qubit_index)['duration']
        return self._qpu.get_qubit_obj(self.mapping[phys_qubit_index]).get_gate_duration(gate_type)
    
    def get_measurement_params(self, phys_qubit_index:int):
        return {'duration': self._qpu.get_qubit_obj(self.mapping[phys_qubit_index]).get_measure_duration(), 'align_step': 8e-9}    #Assuming 2Gs/s

    def get_duration2QG(self, qubit1_phys_index:int, qubit2_phys_index:int, gate_type:list) -> dict:
        cur_cplrs = self._qpu.get_qubit_coupling_objs(self.mapping[qubit1_phys_index], self.mapping[qubit2_phys_index])
        assert len(cur_cplrs) != 0, f"There is no 2-qubit coupling between physical qubits {qubit1_phys_index} and {qubit2_phys_index}"
        zi_elem,_ = cur_cplrs[0].get_ZI_parameters()    #Presume that the 0th coupler is the main 2QG coupler...
        #
        cur_signal_qubits = cur_cplrs[0].get_involved_qubits()
        cur_phys_qubits_signals = [next((k for k, v in self.mapping.items() if v == cur_qubit_id), None) for cur_qubit_id in cur_signal_qubits]
        cur_phys_qubits_signals = [x for x in cur_phys_qubits_signals if x != qubit1_phys_index and x != qubit2_phys_index]
        #
        return {
            'duration': zi_elem.get_gate_duration(gate_type, [self._qpu.get_qubit_obj(self.mapping[qubit1_phys_index]), self._qpu.get_qubit_obj(self.mapping[qubit2_phys_index])]),
            'aux_qubits': cur_phys_qubits_signals
        }
    
    def dt(self, signal_type='drive'):
        if signal_type == 'drive' or signal_type == 'measure':  #TODO: If it ever becomes channel-dependent, just make signal_type hold said information etc...
            return 1.0/2e9
        elif signal_type == 'flux':
            return 1.0/2.0e9    #TODO: Should this be a Python fraction object instead as it's a recurring decimal?
        else:
            assert False, f"Invalid signal ZI line type: {signal_type}."
