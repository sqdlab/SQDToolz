from sqdtoolz.Utilities.OpenQASM import ScheduleParametersBase, QASMCompatibleQubitSingle
from sqdtoolz.HAL.SOFTqpu import SOFTqpu


class ScheduleParametersSoftQPUZI(ScheduleParametersBase):
    def __init__(self, softQPU_ZI:SOFTqpu, mapping:dict):
        self._qpu = softQPU_ZI
        self.mapping = mapping  #This maps the physical qubit index in QASM onto the softQPU IDs...
    
    def get_duration(self, phys_qubit_index:int, gate_type:str|list|tuple) -> float:
        if isinstance(gate_type, (list,tuple)):
            if gate_type[0] == 'D':
                return gate_type[1]
            elif gate_type[0] == 'Measure':
                return self.get_duration_measurement(phys_qubit_index)
        return self._qpu.get_qubit_obj(self.mapping[phys_qubit_index]).get_gate_duration(gate_type)
    
    def get_duration_measurement(self, phys_qubit_index:int):
        return self._qpu.get_qubit_obj(self.mapping[phys_qubit_index]).get_measure_duration()

    def get_duration2QG(self, qubit1_phys_index:int, qubit2_phys_index:int, gate_type:list) -> float:
        zi_elem,_ = self._qpu.get_qubit_coupling_objs(self.mapping[qubit1_phys_index], self.mapping[qubit2_phys_index])[0].get_ZI_parameters()
        return zi_elem.get_gate_duration(gate_type, [self._qpu.get_qubit_obj(self.mapping[qubit1_phys_index]), self._qpu.get_qubit_obj(self.mapping[qubit2_phys_index])])
    
    def dt(self, signal_type='drive'):
        if signal_type == 'drive' or signal_type == 'measure':  #TODO: If it ever becomes channel-dependent, just make signal_type hold said information etc...
            return 1.0/2e9
        elif signal_type == 'flux':
            return 1.0/2.4e9    #TODO: Should this be a Python fraction object instead as it's a recurring decimal?
        else:
            assert False, f"Invalid signal ZI line type: {signal_type}."
