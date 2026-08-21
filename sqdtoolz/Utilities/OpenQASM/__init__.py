
class QASMCompatibleQubitSingle:
    def get_gate_duration(self, gate:str|list|tuple):
        raise NotImplementedError()

    def get_measure_duration(self):
        raise NotImplementedError()

class QASMCompatibleQubitMultiple:
    def get_gate_duration(self, gate:list|tuple, qubits:list):
        raise NotImplementedError()

class ScheduleParametersBase:
    def get_phys_qubit_ids(self) -> list[int]:
        raise NotImplementedError()

    def get_duration(self, phys_qubit_index:int, gate_type:str|list|tuple) -> float:
        raise NotImplementedError()
    
    def get_measurement_params(self, phys_qubit_index:int) -> dict:
        return NotImplementedError()

    def get_duration2QG(self, qubit1_phys_index:int, qubit2_phys_index:int, gate_type:list) -> dict:
        raise NotImplementedError()

    def dt(self, signal_type=''):
        raise NotImplementedError()
