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
ZIQubit('Q0', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/0'))
ZIQubit('Q1', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/1/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/1'))
ZIQubit('Q2', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/2/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/2'))
ZIQubit('Q3', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/3/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/3'))
ZIQubit('Q4', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/4/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/4'))
ZIQuantumElement('Cpl02', lab, TunableTransmonCouplerFixed, flux='Q2/flux')
ZIQuantumElement('Cpl12', lab, TunableTransmonCouplerFixed, flux='Q2/flux')
ZIQuantumElement('Cpl32', lab, TunableTransmonCouplerFixed, flux='Q2/flux')
ZIQuantumElement('Cpl42', lab, TunableTransmonCouplerFixed, flux='Q2/flux')

SOFTqpu('QPU', lab)
lab.HAL('QPU').add_qubit(lab.HAL('Q0'))
lab.HAL('QPU').add_qubit(lab.HAL('Q1'))
lab.HAL('QPU').add_qubit(lab.HAL('Q2'))
lab.HAL('QPU').add_qubit(lab.HAL('Q3'))
lab.HAL('QPU').add_qubit(lab.HAL('Q4'))
lab.HAL('QPU').add_qubit_coupling('Q0', 'Q2', lab.HAL('Cpl02'))
lab.HAL('QPU').add_qubit_coupling('Q1', 'Q2', lab.HAL('Cpl12'))
lab.HAL('QPU').add_qubit_coupling('Q3', 'Q2', lab.HAL('Cpl32'))
lab.HAL('QPU').add_qubit_coupling('Q4', 'Q2', lab.HAL('Cpl42'))

# SOFTqpu.create_summary_config_from_json('tests/ZI_Test_QASM_config.json', 'tests/ZI_test_QASM_JSONScheduler_summary.json')
SOFTqpu.load_config(lab, file_path='tests/ZI_Test_QASM_config.json')

acq_params = {}
acq_params['AcquisitionMode'] = "DISCRIMINATION"
acq_params['AveragingOrder'] = 'SingleShot'
#
for cur_qubit in ['Q0', 'Q1', 'Q2', 'Q3', 'Q4']:
    if acq_params['AcquisitionMode'] == "DISCRIMINATION":
        lab.HAL(cur_qubit).ReadoutKernelType = 'optimal'

ZIACQ('ZIacq', lab, 'zi_boxes')
ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')
exp = ExpZIQASM('test', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q1', 'Q2', 'Q3', 'Q4'], 'tests/ZI_Test_QASM3.qasm', source_dirs=['tests/'])
qregs = exp.get_qubit_regs()
# exp.set_qubit_reg_to_ZI_mappings({('q',0):'Qubit2',('q',1):'Qubit4'})
lab.run_single(exp, debug_skip_experiment=True, override_ACQ_params=acq_params, raw_pulse_sheet_duration=1e-3)
