from sqdtoolz.HAL.ZI.ZIQubit import ZIQubit
from sqdtoolz.HAL.ZI.ZIACQ import ZIACQ
from sqdtoolz.HAL.SOFTqpu import SOFTqpu
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.HAL.ZI.ZIQuantumElement import ZIQuantumElement
from sqdtoolz.HAL.ZI.QuantumElements.TunableTransmonCouplerFixed import TunableTransmonCouplerFixed
from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.ExperimentConfiguration import ExperimentConfiguration
from sqdtoolz.Experiments.Experimental.ExpZIQASM import ExpZIQASM

lab = Laboratory(instr_config_file = "tests/ZI_Basic.yaml", save_dir = "mySaves\\")

lab.load_instrument('zi_boxes')
ZIQubit('Qubit1', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/0'))
ZIQubit('Qubit2', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/1/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/1'))
ZIQubit('Qubit3', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/2/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/2'))
ZIQubit('Qubit4', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/3/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/3'))
ZIQuantumElement('Cpl12', lab, TunableTransmonCouplerFixed, flux='Qubit1/flux')
ZIQuantumElement('Cpl34', lab, TunableTransmonCouplerFixed, flux='Qubit3/flux')
# lab.HAL('Cpl12').QubitFlux = 'Qubit1'

SOFTqpu('QPU', lab)
lab.HAL('QPU').add_qubit(lab.HAL('Qubit1'))
lab.HAL('QPU').add_qubit(lab.HAL('Qubit2'))
lab.HAL('QPU').add_qubit(lab.HAL('Qubit3'))
lab.HAL('QPU').add_qubit(lab.HAL('Qubit4'))
lab.HAL('QPU').add_qubit_coupling('Qubit1', 'Qubit2', lab.HAL('Cpl12'))
lab.HAL('QPU').add_qubit_coupling('Qubit3', 'Qubit4', lab.HAL('Cpl34'))

from sqdtoolz.Utilities.OpenQASM.ParserOpenQASM import ParserOpenQASM, ScheduleParametersSoftQPUZI
poqasm = ParserOpenQASM('tests/ZI_test_QASM_DSL.qasm',['tests/'])
qubit_params = ScheduleParametersSoftQPUZI(lab.HAL('QPU'))
leSchedule = poqasm.create_schedule(qubit_params)
leTable = poqasm.tabulate_schedule(leSchedule, qubit_params)
poqasm.plot_schedule(leSchedule, qubit_params, 'output.html')
a=0

# ZIACQ('ZIacq', lab, 'zi_boxes')
# ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')
# exp = ExpZIQASM('test', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Qubit1', 'Qubit2', 'Qubit3', 'Qubit4'], 'tests/ZI_test_QASM_DSL.qasm', source_dirs=['tests/'])
# lab.run_single(exp, debug_skip_experiment=True)
