import unittest
from sqdtoolz.Utilities.OpenQASM.ParserOpenQASM import ParserOpenQASM
from sqdtoolz.Utilities.OpenQASM.ScheduleParametersJSONConfigZI import ScheduleParametersJSONConfigZI
import numpy as np

class TestQasmAlignment(unittest.TestCase):
    ERR_TOL = 5e-13

    def initialise(self):
        pass
    
    def cleanup(self):
        pass

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL
    
    def _get_table(self, qasm_path, schedule_params_path, qreg_phys_mapping):
        oqasm = ParserOpenQASM(qasm_path, [], measure_label='QMEAS')
        oqasm.set_qreg_physical_mapping(qreg_phys_mapping)
        oqasm.perform_parsing()
        leScheduleParams = ScheduleParametersJSONConfigZI.fromFile(schedule_params_path)
        leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
        leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
        oqasm.check_ZI_compatibility(leSchedule, leScheduleParams)
        return oqasm, leScheduleParams, leScheduleTable

    def test_Alignment(self):
        self.initialise()
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/BasicAlignment1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 1, "BasicAlignment1 has synthesis error where there is not exactly 1 X gate."
        assert len(Y) == 1, "BasicAlignment1 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "BasicAlignment1 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 1, "BasicAlignment1 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "BasicAlignment1 has synthesis error where Y does not follow X correctly."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "BasicAlignment1 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/BasicAlignment2.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 1, "BasicAlignment2 has synthesis error where there is not exactly 1 X gate."
        assert len(Y) == 1, "BasicAlignment2 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "BasicAlignment2 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "BasicAlignment2 has synthesis error where Y gate is not on qubit 2."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"]) < 1e-12, "BasicAlignment2 has synthesis error where X and Y are not in parallel."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "BasicAlignment2 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/BasicAlignment3.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 1, "BasicAlignment3 has synthesis error where there is not exactly 1 X gate."
        assert len(Y) == 1, "BasicAlignment3 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "BasicAlignment3 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "BasicAlignment3 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "BasicAlignment3 has synthesis error where Y does not follow X correctly."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "BasicAlignment3 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/BasicAlignment4.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "BasicAlignment4 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "BasicAlignment4 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "BasicAlignment4 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "BasicAlignment4 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "BasicAlignment4 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "BasicAlignment4 has synthesis error where the second X does not follow Y correctly."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "BasicAlignment4 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/BasicAlignment5.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "BasicAlignment5 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "BasicAlignment5 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "BasicAlignment5 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "BasicAlignment5 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "BasicAlignment5 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "BasicAlignment5 has synthesis error where the second X does not follow Y correctly."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "BasicAlignment5 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()

    def test_Delays(self):
        self.initialise()
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Delay1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay1 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay1 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay1 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay1 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay1 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - 5e-9) < 1e-12, "Delay1 has synthesis error where the second X does not follow Y correctly after the prescribed 5ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay1 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Delay2.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay2 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay2 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay2 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay2 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay2 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - 300e-9) < 1e-12, "Delay2 has synthesis error where the second X does not follow Y correctly after the prescribed 300ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay2 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Delay3.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay3 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay3 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay3 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay3 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay3 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - 400e-9) < 1e-12, "Delay3 has synthesis error where the second X does not follow Y correctly after the prescribed 400ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay3 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Delay4.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay4 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay4 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay4 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay4 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay4 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - (400e-9*2+1e-9)) < 1e-12, "Delay4 has synthesis error where the second X does not follow Y correctly after the prescribed 400ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay4 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Delay5.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay4 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay4 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay4 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay4 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay4 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - ((400e-9-ledt)/2-5*ledt)) < 1e-12, "Delay4 has synthesis error where the second X does not follow Y correctly after the prescribed 400ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay4 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()

class TestQasmGeneral(unittest.TestCase):
    ERR_TOL = 5e-13

    def initialise(self):
        pass
    
    def cleanup(self):
        pass

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL
    
    def _get_table(self, qasm_path, schedule_params_path, qreg_phys_mapping):
        oqasm = ParserOpenQASM(qasm_path, [], measure_label='QMEAS')
        oqasm.set_qreg_physical_mapping(qreg_phys_mapping)
        oqasm.perform_parsing()
        leScheduleParams = ScheduleParametersJSONConfigZI.fromFile(schedule_params_path)
        leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
        leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
        oqasm.check_ZI_compatibility(leSchedule, leScheduleParams)
        return oqasm, leScheduleParams, leScheduleTable

    def test_GateDefs(self):
        self.initialise()
        
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/GateDef1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        #Should be
        # Q1   X  o
        #         |
        # Q2 **Y  Z *Y*
        #with hidden zero-time Z gates placed at the * points...
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        Z = leScheduleTable[leScheduleTable["operation"] == "Z"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert Z.iloc[0]["start_time"] == 0, "The first Z-rotation is at the wrong spot in time."
        assert Z.iloc[0]["qubits"] == 2, "The first Z-rotation is on the wrong qubit."
        assert np.abs(Z.iloc[0]["angle"] + np.pi/2) < 1e-12, "The first Z-rotation is of the wrong angle."
        assert Z.iloc[1]["start_time"] == 0, "The second Z-rotation is at the wrong spot in time."
        assert Z.iloc[1]["qubits"] == 2, "The second Z-rotation is on the wrong qubit."
        assert np.abs(Z.iloc[1]["angle"] - np.pi) < 1e-12, "The second Z-rotation is of the wrong angle."
        leGateTime = leScheduleParams.get_duration(1, ('X',np.pi))
        assert X.iloc[0]["start_time"] == 0, "The first X-rotation is scheduled at the wrong time."
        assert Y.iloc[0]["qubits"] == 2, "The first Y-rotation is on the wrong qubit."
        assert Y.iloc[0]["start_time"] == 0, "The first Y-rotation is scheduled at the wrong time."
        leGateTime2 = leScheduleParams.get_duration2QG(1,2,['ctrl',('Z',np.pi)])['duration']
        assert Z.iloc[2]['qubitsAux'] == 1, "The CZ gate has the wrong control qubit."
        assert Z.iloc[2]["start_time"] == leGateTime, "The CZ gate is at the wrong spot in time."
        #
        assert Y.iloc[1]["start_time"] == leGateTime+leGateTime2, "The second Y-rotation is scheduled at the wrong time."
        assert Z.iloc[3]["start_time"] == leGateTime+leGateTime2, "The fourth Z-rotation is scheduled at the wrong time."
        assert Z.iloc[3]["qubits"] == 2, "The fourth Z-rotation is on the wrong qubit."
        assert Z.iloc[4]["start_time"] == leGateTime+leGateTime2+leGateTime, "The fifth Z-rotation is scheduled at the wrong time."
        assert Z.iloc[4]["qubits"] == 2, "The fifth Z-rotation is on the wrong qubit."
        #
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay1 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()
    
    def test_classical_vars(self):
        self.initialise()
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ClassicalVars1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay4 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay4 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay4 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay4 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay4 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - ((400e-9-ledt)/2-8*ledt)) < 1e-12, "Delay4 has synthesis error where the second X does not follow Y correctly after the prescribed 400ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay4 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ClassicalVars2.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay4 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay4 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay4 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay4 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay4 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - ((400e-9-ledt)/5-7*ledt)) < 1e-12, "Delay4 has synthesis error where the second X does not follow Y correctly after the prescribed 400ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay4 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ClassicalVars3.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay4 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay4 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay4 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay4 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay4 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - ((400e-9-ledt)/12-3*ledt)) < 1e-12, "Delay4 has synthesis error where the second X does not follow Y correctly after the prescribed 400ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay4 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ClassicalVars4.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Delay4 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 1, "Delay4 has synthesis error where there is not exactly 1 Y gate."
        assert X.iloc[0]["qubits"] == 1, "Delay4 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 2, "Delay4 has synthesis error where Y gate is not on qubit 1."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - leScheduleParams.get_duration2QG(2,1,['ctrl',('Z',np.pi)])['duration']) < 1e-12, "Delay4 has synthesis error where Y does not follow X correctly."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi)) - ((400e-9-ledt)/(15/9)-8*ledt)) < 1e-12, "Delay4 has synthesis error where the second X does not follow Y correctly after the prescribed 400ns."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Delay4 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()

    def test_measure(self):
        self.initialise()
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Measure1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        R = leScheduleTable[leScheduleTable["operation"] == "R"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Measure1 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 2, "Measure1 has synthesis error where there are not exactly 1 Y gates."
        assert X.iloc[0]["qubits"] == 1, "Measure1 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 1, "Measure1 has synthesis error where the first Y gate is not on qubit 1."
        assert Y.iloc[1]["qubits"] == 2, "Measure1 has synthesis error where the second Y gate is not on qubit 2."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "Measure1 has synthesis error where Y does not follow X correctly."
        assert np.abs(R.iloc[0]["start_time"] - Y.iloc[0]["end_time"]) < 1e-12, "Measure1 has incorrectly scheduled the Measure."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["end_time"] - leScheduleParams.get_duration(0, ('Reset',))) < 1e-12, "Measure1 has synthesis error where Y does not follow X correctly."
        assert np.abs(Y.iloc[1]["start_time"]) < 1e-12, "Measure1 has synthesis error where the second Y does not start at the beginning."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Measure1 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        #Multi-qubit Measure
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Measure2.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        R = leScheduleTable[leScheduleTable["operation"] == "R"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Measure2 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 2, "Measure2 has synthesis error where there are not exactly 1 Y gates."
        assert X.iloc[0]["qubits"] == 1, "Measure2 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 1, "Measure2 has synthesis error where the first Y gate is not on qubit 1."
        assert Y.iloc[1]["qubits"] == 2, "Measure2 has synthesis error where the second Y gate is not on qubit 2."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "Measure2 has synthesis error where Y does not follow X correctly."
        assert np.abs(R.iloc[0]["start_time"] - Y.iloc[0]["end_time"]) < 1e-12, "Measure2 has incorrectly scheduled the Measure."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["end_time"] - leScheduleParams.get_duration(0, ('Reset',))) < 1e-12, "Measure2 has synthesis error where Y does not follow X correctly."
        assert np.abs(Y.iloc[1]["start_time"] - leScheduleParams.get_duration(1, ('Reset',))) < 1e-12, "Measure2 has synthesis error where the second Y does not start at the beginning."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Measure2 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()

    def test_reset(self):
        self.initialise()
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Reset1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        R = leScheduleTable[leScheduleTable["operation"] == "R"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Reset1 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 2, "Reset1 has synthesis error where there are not exactly 1 Y gates."
        assert X.iloc[0]["qubits"] == 1, "Reset1 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 1, "Reset1 has synthesis error where the first Y gate is not on qubit 1."
        assert Y.iloc[1]["qubits"] == 2, "Reset1 has synthesis error where the second Y gate is not on qubit 2."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "Reset1 has synthesis error where Y does not follow X correctly."
        assert np.abs(R.iloc[0]["start_time"] - Y.iloc[0]["end_time"]) < 1e-12, "Reset1 has incorrectly scheduled the reset."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["end_time"] - leScheduleParams.get_duration(0, ('Reset',))) < 1e-12, "Reset1 has synthesis error where Y does not follow X correctly."
        assert np.abs(Y.iloc[1]["start_time"]) < 1e-12, "Reset1 has synthesis error where the second Y does not start at the beginning."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Reset1 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        #Multi-qubit reset
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Reset2.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        R = leScheduleTable[leScheduleTable["operation"] == "R"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Reset2 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 2, "Reset2 has synthesis error where there are not exactly 1 Y gates."
        assert X.iloc[0]["qubits"] == 1, "Reset2 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 1, "Reset2 has synthesis error where the first Y gate is not on qubit 1."
        assert Y.iloc[1]["qubits"] == 2, "Reset2 has synthesis error where the second Y gate is not on qubit 2."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "Reset2 has synthesis error where Y does not follow X correctly."
        assert np.abs(R.iloc[0]["start_time"] - Y.iloc[0]["end_time"]) < 1e-12, "Reset2 has incorrectly scheduled the reset."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["end_time"] - leScheduleParams.get_duration(0, ('Reset',))) < 1e-12, "Reset2 has synthesis error where Y does not follow X correctly."
        assert np.abs(Y.iloc[1]["start_time"] - leScheduleParams.get_duration(1, ('Reset',))) < 1e-12, "Reset2 has synthesis error where the second Y does not start at the beginning."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Reset2 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()

    def test_indexed_decl(self):
        self.initialise()
       
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Indexed1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        R = leScheduleTable[leScheduleTable["operation"] == "R"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Indexed1 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 2, "Indexed1 has synthesis error where there are not exactly 1 Y gates."
        assert X.iloc[0]["qubits"] == 1, "Indexed1 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 1, "Indexed1 has synthesis error where the first Y gate is not on qubit 1."
        assert Y.iloc[1]["qubits"] == 2, "Indexed1 has synthesis error where the second Y gate is not on qubit 2."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "Indexed1 has synthesis error where Y does not follow X correctly."
        assert np.abs(R.iloc[0]["start_time"] - Y.iloc[0]["end_time"]) < 1e-12, "Indexed1 has incorrectly scheduled the reset."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["end_time"] - leScheduleParams.get_duration(0, ('Reset',))) < 1e-12, "Indexed1 has synthesis error where Y does not follow X correctly."
        assert np.abs(Y.iloc[1]["start_time"]) < 1e-12, "Indexed1 has synthesis error where the second Y does not start at the beginning."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Indexed1 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        #Individual registers...
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/Indexed2.qasm', 'UnitTests/QASM/config_summary.json', {('q1',0):1,('q2',0):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Y = leScheduleTable[leScheduleTable["operation"] == "Y"]
        R = leScheduleTable[leScheduleTable["operation"] == "R"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 2, "Indexed2 has synthesis error where there are not exactly 2 X gates."
        assert len(Y) == 2, "Indexed2 has synthesis error where there are not exactly 1 Y gates."
        assert X.iloc[0]["qubits"] == 1, "Indexed2 has synthesis error where X gate is not on qubit 1."
        assert Y.iloc[0]["qubits"] == 1, "Indexed2 has synthesis error where the first Y gate is not on qubit 1."
        assert Y.iloc[1]["qubits"] == 2, "Indexed2 has synthesis error where the second Y gate is not on qubit 2."
        assert np.abs(Y.iloc[0]["start_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "Indexed2 has synthesis error where Y does not follow X correctly."
        assert np.abs(R.iloc[0]["start_time"] - Y.iloc[0]["end_time"]) < 1e-12, "Indexed2 has incorrectly scheduled the reset."
        assert np.abs(X.iloc[1]["start_time"] - Y.iloc[0]["end_time"] - leScheduleParams.get_duration(0, ('Reset',))) < 1e-12, "Indexed2 has synthesis error where Y does not follow X correctly."
        assert np.abs(Y.iloc[1]["start_time"]) < 1e-12, "Indexed2 has synthesis error where the second Y does not start at the beginning."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "Indexed2 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()

class TestQasmControlFlows(unittest.TestCase):
    ERR_TOL = 5e-13

    def initialise(self):
        pass
    
    def cleanup(self):
        pass

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL
    
    def _get_table(self, qasm_path, schedule_params_path, qreg_phys_mapping):
        oqasm = ParserOpenQASM(qasm_path, [], measure_label='QMEAS')
        oqasm.set_qreg_physical_mapping(qreg_phys_mapping)
        oqasm.perform_parsing()
        leScheduleParams = ScheduleParametersJSONConfigZI.fromFile(schedule_params_path)
        leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
        leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
        oqasm.check_ZI_compatibility(leSchedule, leScheduleParams)
        return oqasm, leScheduleParams, leScheduleTable

    def test_ForLoops(self):
        self.initialise()

        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ControlFlow1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert X.iloc[0]["start_time"] == 0, "Start time before For Loop is incorrect for the X-Gate."
        t1QG = leScheduleParams.get_duration(1, ('X',np.pi))
        #
        assert np.abs(X.iloc[1]["start_time"] - t1QG) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[2]["start_time"] - t1QG*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[3]["start_time"] - t1QG*3 - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[4]["start_time"] - t1QG*4 - 15e-9/9) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = t1QG*5 + 15e-9/9
        #
        assert np.abs(X.iloc[5]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[6]["start_time"] - fin_time - t1QG - 2e-9) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[7]["start_time"] - fin_time - t1QG - 2e-9 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[8]["start_time"] - fin_time - t1QG - 2e-9 - t1QG - 15e-9/9 - t1QG - 3e-9) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9 + t1QG + 15e-9/9 + t1QG + 3e-9 + t1QG
        #
        assert np.abs(X.iloc[9]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[10]["start_time"] - fin_time - t1QG - 2e-9*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[11]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[12]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9 - t1QG - 3e-9*2) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9*2 + t1QG + 15e-9/9 + t1QG + 3e-9*2 + t1QG
        #
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "For Loop did not leave both qubits aligned exactly."

        #Recheck the shadowing of the variables as with the previous case...
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ControlFlow2.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Z = leScheduleTable[leScheduleTable["operation"] == "Z"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert X.iloc[0]["start_time"] == 0, "Start time before For Loop is incorrect for the X-Gate."
        t1QG = leScheduleParams.get_duration(1, ('X',np.pi))
        #
        assert np.abs(X.iloc[1]["start_time"] - t1QG) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[2]["start_time"] - t1QG*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[3]["start_time"] - t1QG*3 - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[4]["start_time"] - t1QG*4 - 15e-9/9) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = t1QG*5 + 15e-9/9
        #
        assert np.abs(X.iloc[5]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[6]["start_time"] - fin_time - t1QG - 2e-9) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[7]["start_time"] - fin_time - t1QG - 2e-9 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[8]["start_time"] - fin_time - t1QG - 2e-9 - t1QG - 15e-9/9 - t1QG - 3e-9) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9 + t1QG + 15e-9/9 + t1QG + 3e-9 + t1QG
        #
        assert np.abs(X.iloc[9]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[10]["start_time"] - fin_time - t1QG - 2e-9*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[11]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[12]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9 - t1QG - 3e-9*2) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9*2 + t1QG + 15e-9/9 + t1QG + 3e-9*2 + t1QG
        #
        assert np.abs(Z.iloc[0]["start_time"] - fin_time - 8e-9) < 1e-12, "CZ after For Loop is incorrectly scheduled."
        #
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "The CZ gate did not leave both qubits aligned exactly."

        #Check loop with step...
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ControlFlow3.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Z = leScheduleTable[leScheduleTable["operation"] == "Z"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert X.iloc[0]["start_time"] == 0, "Start time before For Loop is incorrect for the X-Gate."
        t1QG = leScheduleParams.get_duration(1, ('X',np.pi))
        #
        assert np.abs(X.iloc[1]["start_time"] - t1QG) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[2]["start_time"] - t1QG*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[3]["start_time"] - t1QG*3 - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[4]["start_time"] - t1QG*4 - 15e-9/9) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = t1QG*5 + 15e-9/9
        #
        assert np.abs(X.iloc[5]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[6]["start_time"] - fin_time - t1QG - 2e-9*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[7]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[8]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9 - t1QG - 3e-9*2) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9*2 + t1QG + 15e-9/9 + t1QG + 3e-9*2 + t1QG
        #
        assert np.abs(X.iloc[9]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[10]["start_time"] - fin_time - t1QG - 2e-9*4) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[11]["start_time"] - fin_time - t1QG - 2e-9*4 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[12]["start_time"] - fin_time - t1QG - 2e-9*4 - t1QG - 15e-9/9 - t1QG - 3e-9*4) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9*4 + t1QG + 15e-9/9 + t1QG + 3e-9*4 + t1QG
        #
        assert np.abs(Z.iloc[0]["start_time"] - fin_time - 8e-9) < 1e-12, "CZ after For Loop is incorrectly scheduled."
        #
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "The CZ gate did not leave both qubits aligned exactly."

        #Check loop with step and non-inclusive end-point...
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ControlFlow4.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Z = leScheduleTable[leScheduleTable["operation"] == "Z"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert X.iloc[0]["start_time"] == 0, "Start time before For Loop is incorrect for the X-Gate."
        t1QG = leScheduleParams.get_duration(1, ('X',np.pi))
        #
        assert np.abs(X.iloc[1]["start_time"] - t1QG) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[2]["start_time"] - t1QG*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[3]["start_time"] - t1QG*3 - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[4]["start_time"] - t1QG*4 - 15e-9/9) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = t1QG*5 + 15e-9/9
        #
        assert np.abs(X.iloc[5]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[6]["start_time"] - fin_time - t1QG - 2e-9*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[7]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[8]["start_time"] - fin_time - t1QG - 2e-9*2 - t1QG - 15e-9/9 - t1QG - 3e-9*2) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9*2 + t1QG + 15e-9/9 + t1QG + 3e-9*2 + t1QG
        #
        assert np.abs(X.iloc[9]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[10]["start_time"] - fin_time - t1QG - 2e-9*4) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[11]["start_time"] - fin_time - t1QG - 2e-9*4 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[12]["start_time"] - fin_time - t1QG - 2e-9*4 - t1QG - 15e-9/9 - t1QG - 3e-9*4) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG + 2e-9*4 + t1QG + 15e-9/9 + t1QG + 3e-9*4 + t1QG
        #
        assert np.abs(Z.iloc[0]["start_time"] - fin_time - 8e-9) < 1e-12, "CZ after For Loop is incorrectly scheduled."
        #
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "The CZ gate did not leave both qubits aligned exactly."

        #Nested loop with parametric end-condition...
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/ControlFlow5.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        ledt = leScheduleParams.dt()
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        Z = leScheduleTable[leScheduleTable["operation"] == "Z"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert X.iloc[0]["start_time"] == 0, "Start time before For Loop is incorrect for the X-Gate."
        t1QG = leScheduleParams.get_duration(1, ('X',np.pi))
        #
        assert np.abs(X.iloc[1]["start_time"] - t1QG) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[2]["start_time"] - t1QG*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[3]["start_time"] - t1QG*3 - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[4]["start_time"] - t1QG*4 - 15e-9/9) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = t1QG*5 + 15e-9/9
        #
        assert np.abs(X.iloc[5]["start_time"] - fin_time) < 1e-12, "First X-Gate in nested For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[6]["start_time"] - fin_time - t1QG) < 1e-12, "First X-Gate in nested For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[7]["start_time"] - fin_time - t1QG*2) < 1e-12, "First X-Gate in nested For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[8]["start_time"] - fin_time - t1QG*3 - 2e-9*2) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[9]["start_time"] - fin_time - t1QG*3 - 2e-9*2 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[10]["start_time"] - fin_time - t1QG*3 - 2e-9*2 - t1QG - 15e-9/9 - t1QG - 3e-9*2) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG*3 + 2e-9*2 + t1QG + 15e-9/9 + t1QG + 3e-9*2 + t1QG
        #
        assert np.abs(X.iloc[11]["start_time"] - fin_time) < 1e-12, "First X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[12]["start_time"] - fin_time - t1QG) < 1e-12, "First X-Gate in nested For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[13]["start_time"] - fin_time - t1QG*2) < 1e-12, "First X-Gate in nested For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[14]["start_time"] - fin_time - t1QG*3) < 1e-12, "First X-Gate in nested For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[15]["start_time"] - fin_time - t1QG*4) < 1e-12, "First X-Gate in nested For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[16]["start_time"] - fin_time - t1QG*5 - 2e-9*4) < 1e-12, "Second X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[17]["start_time"] - fin_time - t1QG*5 - 2e-9*4 - t1QG - 15e-9/9) < 1e-12, "Third X-Gate in For Loop is incorrectly scheduled."
        assert np.abs(X.iloc[18]["start_time"] - fin_time - t1QG*5 - 2e-9*4 - t1QG - 15e-9/9 - t1QG - 3e-9*4) < 1e-12, "Fourth X-Gate in For Loop is incorrectly scheduled."
        fin_time = fin_time + t1QG*5 + 2e-9*4 + t1QG + 15e-9/9 + t1QG + 3e-9*4 + t1QG
        #
        assert np.abs(Z.iloc[0]["start_time"] - fin_time - 8e-9) < 1e-12, "CZ after For Loop is incorrectly scheduled."
        #
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "The CZ gate did not leave both qubits aligned exactly."

        self.cleanup()

class TestQasmOpenPulse(unittest.TestCase):
    ERR_TOL = 5e-13

    def initialise(self):
        pass
    
    def cleanup(self):
        pass

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL
    
    def _get_table(self, qasm_path, schedule_params_path, qreg_phys_mapping):
        oqasm = ParserOpenQASM(qasm_path, [], measure_label='QMEAS')
        oqasm.set_qreg_physical_mapping(qreg_phys_mapping)
        oqasm.perform_parsing()
        leScheduleParams = ScheduleParametersJSONConfigZI.fromFile(schedule_params_path)
        leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
        leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
        oqasm.check_ZI_compatibility(leSchedule, leScheduleParams)
        return oqasm, leScheduleParams, leScheduleTable

    def test_Substitution(self):
        self.initialise()

        #Check that the X-gate on Qubit 2 is overridden...
        oqasm, leScheduleParams, leScheduleTable = self._get_table('UnitTests/QASM/OpenPulseSub1.qasm', 'UnitTests/QASM/config_summary.json', {('q',0):1,('q',1):2})
        #
        X = leScheduleTable[leScheduleTable["operation"] == "X"]
        W = leScheduleTable[leScheduleTable["operation"] == "W"]
        M = leScheduleTable[leScheduleTable["operation"] == "M"]
        assert len(X) == 1, "OpenPulseSub1 has synthesis error where there is not exactly one 'X' gate."
        assert X.iloc[0]["qubits"] == 1, "OpenPulseSub1 has synthesis error where X gate is not on qubit 1."
        assert W.iloc[0]["qubits"] == 2, "OpenPulseSub1 has synthesis error where overridden X gate is not on qubit 2."
        assert np.abs(X.iloc[0]["end_time"] - X.iloc[0]["start_time"] - leScheduleParams.get_duration(1, ('X',np.pi))) < 1e-12, "OpenPulseSub1 has synthesis error on X-gate duration."
        assert np.abs(X.iloc[0]["start_time"]) < 1e-12, "OpenPulseSub1 has synthesis error on X-gate scheduling."
        assert np.abs(W.iloc[0]["end_time"] - W.iloc[0]["start_time"] - 83e-9) < 1e-12, "OpenPulseSub1 has synthesis error on overridden X-gate duration."
        assert np.abs(W.iloc[0]["start_time"]) < 1e-12, "OpenPulseSub1 has synthesis error on overridden X-gate scheduling."
        assert len(M) == 2 and set(M["qubits"]) == {1, 2}, "OpenPulseSub1 has synthesis error where there is not exactly 2 aligned measurements on qubits 1 and 2"

        self.cleanup()

if __name__ == '__main__':
    temp = TestQasmOpenPulse()
    temp.test_Substitution()
    # unittest.main()

