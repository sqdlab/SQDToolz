
class QASMCompatibleQubitSingle:
    def get_gate_duration(self, gate:str|list|tuple):
        raise NotImplementedError()

    def get_measure_duration(self):
        raise NotImplementedError()

class QASMCompatibleQubitMultiple:
    def get_gate_duration(self, gate:list|tuple, qubits:list):
        raise NotImplementedError()

class ScheduleParametersBase:
    def get_duration(self, qubit_index:int, gate_type:str|list|tuple) -> float:
        raise NotImplementedError()
    
    def get_duration_measurement(self, qubit_index:int):
        return NotImplementedError()

    def get_duration2QG(self, qubit1_index:int, qubit2_index:int, gate_type:list) -> float:
        raise NotImplementedError()

    @property
    def dt(self):
        raise NotImplementedError()


