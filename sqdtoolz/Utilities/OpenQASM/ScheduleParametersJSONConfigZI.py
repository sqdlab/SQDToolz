from sqdtoolz.Utilities.OpenQASM import ScheduleParametersBase, QASMCompatibleQubitSingle
import json

class ScheduleParametersJSONConfigZI(ScheduleParametersBase):
    def __init__(self, json_dict:dict):
        """
        NOTE: json_dict is the output from SOFTqpu.create_summary_config_from_json.
        TODO: Given that it's only 2-3 attributes, it's left hard-coded. But it must change as ExpZIqubit starts to support other qubit types...
        """
        self.config_data = json_dict
    
    @classmethod
    def fromFile(cls, json_file_path):
        """
        NOTE: json_file_path is the output from SOFTqpu.create_summary_config_from_json.
        TODO: Given that it's only 2-3 attributes, it's left hard-coded. But it must change as ExpZIqubit starts to support other qubit types...
        """
        with open(json_file_path, 'r') as f:
            config_data = json.load(f)
        return cls(config_data)

    def get_duration(self, phys_qubit_index:int, gate_type:list|tuple) -> float:
        cur_qubit = self.config_data['Qubits'][phys_qubit_index]
        gate = gate_type[0]
        if gate[0] == '-':
            gate = gate[1:]
        match gate:
            case 'D':
                return gate_type[1]
            case 'Measure':
                return self.get_measurement_params(phys_qubit_index)['duration']
            case 'X' | 'X/2' | 'Y' | 'Y/2' | 'H':
                return cur_qubit['DriveGETime']
            case 'Z' | 'Z/2':
                return 0
            case 'Reset':
                return cur_qubit['ResetTime']

    def get_measurement_params(self, phys_qubit_index:int):
        return {'duration': self.config_data['Qubits'][phys_qubit_index]['ReadoutTime'], 'align_step': 8e-9}    #Assuming 2Gs/s

    def get_duration2QG(self, qubit1_phys_index:int, qubit2_phys_index:int, gate_type:list) -> dict:
        #Find the coupler...
        found = False
        for cur_cplr in self.config_data['Couplers']:
            qubit1 = cur_cplr['Linkage'][0]
            qubit2 = cur_cplr['Linkage'][1]
            if self.config_data['Qubits'][qubit1_phys_index]['Name'] == qubit1 and self.config_data['Qubits'][qubit2_phys_index]['Name'] == qubit2:
                found = True
                break
        assert found, f"There is no 2-qubit coupling between physical qubits {qubit1_phys_index} and {qubit2_phys_index}"
        assert gate_type[0] == 'ctrl' and gate_type[1][0] == 'Z', "Only supporting CZ at the moment..."
        #
        cur_signal_qubits = cur_cplr['qubits_involved']
        cur_phys_qubits_signals = [next((m for m, item in enumerate(self.config_data['Qubits']) if item["Name"] == x), -1) for x in cur_signal_qubits]
        cur_phys_qubits_signals = [x for x in cur_phys_qubits_signals if x != qubit1_phys_index and x != qubit2_phys_index]
        #
        return {
            'duration': cur_cplr['Length'],
            'aux_qubits': cur_phys_qubits_signals
        }
    
    def dt(self, signal_type='drive'):
        if signal_type == 'drive' or signal_type == 'measure':
            return 1.0/2e9
        elif signal_type == 'flux':
            return 1.0/2.0e9    #TODO: Should this be a Python fraction object instead as it's a recurring decimal?
        else:
            assert False, f"Invalid signal ZI line type: {signal_type}."
