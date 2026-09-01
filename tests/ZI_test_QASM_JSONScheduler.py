from sqdtoolz.Utilities.OpenQASM.ParserOpenQASM import ParserOpenQASM
from sqdtoolz.Utilities.OpenQASM.ScheduleParametersJSONConfigZI import ScheduleParametersJSONConfigZI

# oqasm = ParserOpenQASM('tests/ZI_Test_Bell.qasm', ['tests/'])
# oqasm.set_qreg_physical_mapping({('q',0):0,('q',1):2})
# oqasm.perform_parsing()
# leScheduleParams = ScheduleParametersJSONConfigZI.fromFile('tests/ZI_test_QASM_JSONScheduler.json')
# leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
# leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
# print(leScheduleTable)


# my_script = r"""
# OPENQASM 3;
# include 'stdgates_transmon_fixed_coupler.inc';
 
# bit[2] c;
# qubit[2] q;
 
# z q[0];
# rx(pi/2) q[0];
 
# z q[1];
# ry(pi/2) q[1];
 
# ctrl @ z q[0], q[1];
 
# z q[1];
# ry(pi/2) q[1];
 
# delay[0]  q[0], q[1];
# c[0] = measure q[0];
# c[1] = measure q[1];
# """
# oqasm = ParserOpenQASM('', ['tests/'], main_qasm=my_script)
# oqasm.set_qreg_physical_mapping({('q',0):0,('q',1):2})
# oqasm.perform_parsing()
# leScheduleParams = ScheduleParametersJSONConfigZI.fromFile('tests/ZI_test_QASM_JSONScheduler.json')
# leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
# leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
# print(leScheduleTable)

# my_script = r"""
# OPENQASM 3.0;
# include "stdgates_transmon_fixed_coupler.inc";

# qubit[2] q;
# bit[2] c;
# h q[0];
# h q[1];
# cz q[0],q[1];
# h q[1];
# delay[0ns] q;
# c[0] = measure q[0];
# c[1] = measure q[1];
# """
# oqasm = ParserOpenQASM('', ['tests/'], main_qasm=my_script, measure_label='QMEAS')
# oqasm.set_qreg_physical_mapping({('q',0):1,('q',1):2})
# oqasm.perform_parsing()
# leScheduleParams = ScheduleParametersJSONConfigZI.fromFile('tests/ZI_test_QASM_JSONScheduler.json')
# leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
# leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
# oqasm.check_ZI_compatibility(leSchedule, leScheduleParams)
# print(leScheduleTable)


oqasm = ParserOpenQASM('tests/ZI_Test_QASM5.qasm', [], measure_label='QMEAS')
oqasm.set_qreg_physical_mapping({('q',0):1,('q',1):2})
oqasm.perform_parsing()
leScheduleParams = ScheduleParametersJSONConfigZI.fromFile('tests/ZI_test_QASM_JSONScheduler_summary.json')
leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
oqasm.check_ZI_compatibility(leSchedule, leScheduleParams)
oqasm.plot_schedule(leSchedule, leScheduleParams, 'mySaves/temp.html')
print(leScheduleTable)
