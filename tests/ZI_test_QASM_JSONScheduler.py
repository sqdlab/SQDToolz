from sqdtoolz.Utilities.OpenQASM.ParserOpenQASM import ParserOpenQASM
from sqdtoolz.Utilities.OpenQASM.ScheduleParametersJSONConfigZI import ScheduleParametersJSONConfigZI

oqasm = ParserOpenQASM('tests/ZI_Test_Bell.qasm', ['tests/'])
oqasm.set_qreg_physical_mapping({('q',0):0,('q',1):2})
oqasm.perform_parsing()
leScheduleParams = ScheduleParametersJSONConfigZI.fromFile('tests/ZI_test_QASM_JSONScheduler.json')
leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
print(leScheduleTable)


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

