from sqdtoolz.Utilities.OpenQASM.ParserOpenQASM import ParserOpenQASM
from sqdtoolz.Utilities.OpenQASM.ScheduleParametersJSONConfigZI import ScheduleParametersJSONConfigZI

oqasm = ParserOpenQASM('tests/ZI_Test_Bell.qasm', ['tests/'])
oqasm.set_qreg_physical_mapping({('q',0):0,('q',1):2})
oqasm.perform_parsing()
leScheduleParams = ScheduleParametersJSONConfigZI.fromFile('tests/ZI_test_QASM_JSONScheduler.json')
leSchedule = oqasm.create_schedule(leScheduleParams, flatten_blocks=True)
leScheduleTable = oqasm.tabulate_schedule(leSchedule, leScheduleParams)
print(leScheduleTable)
