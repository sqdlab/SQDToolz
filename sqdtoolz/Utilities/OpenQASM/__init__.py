
class QASMCompatibleQubitSingle:
    def get_gate_duration(self, gate:str):
        raise NotImplementedError()

    def get_measure_duration(self):
        raise NotImplementedError()

class QASMCompatibleQubitMultiple:
    def get_gate_duration(self, gate:list[str]|tuple[str], qubits:list):
        raise NotImplementedError()

class ScheduleParametersBase:
    def get_duration(self, qubit_index:int, gate_type: str) -> float:
        raise NotImplementedError()

    def get_duration2QG(self, qubit1_index:int, qubit2_index:int, gate_type: str) -> float:
        raise NotImplementedError()

    @property
    def dt(self):
        raise NotImplementedError()


