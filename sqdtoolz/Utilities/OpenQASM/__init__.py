
class QASMCompatibleQubitSingle:
    def get_gate_duration(self, gate:str|list|tuple):
        raise NotImplementedError()

    def get_measure_duration(self):
        raise NotImplementedError()

class QASMCompatibleQubitMultiple:
    def get_gate_duration(self, gate:list|tuple, qubits:list):
        raise NotImplementedError()

class ScheduleParametersBase:
    def get_duration(self, phys_qubit_index:int, gate_type:str|list|tuple) -> float:
        raise NotImplementedError()
    
    def get_duration_measurement(self, phys_qubit_index:int):
        return NotImplementedError()

    def get_duration2QG(self, qubit1_phys_index:int, qubit2_phys_index:int, gate_type:list) -> float:
        raise NotImplementedError()

    def dt(self, signal_type=''):
        raise NotImplementedError()
