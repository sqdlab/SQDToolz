import numpy as np
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

from sqdtoolz.HAL.ZI.ZIQubit import ZIQubit
from sqdtoolz.HAL.ZI.ZIACQ import ZIACQ
from sqdtoolz.HAL.SOFTqpu import SOFTqpu
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.HAL.ZI.ZIQuantumElement import ZIQuantumElement
from sqdtoolz.HAL.ZI.QuantumElements.TunableTransmonCouplerFixed import TunableTransmonCouplerFixed

import matplotlib.pyplot as plt

lab = Laboratory(instr_config_file = "tests/ZI_Basic.yaml", save_dir = "mySaves\\")

lab.load_instrument('zi_boxes')
ZIQubit('Qubit1', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/0'))
ZIQubit('Qubit2', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/1/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', 'SIGOUTS/1'))

ZIQuantumElement('Cpl12', lab, TunableTransmonCouplerFixed, flux='Qubit1/flux')
# lab.HAL('Cpl12').QubitFlux = 'Qubit1'

SOFTqpu('QPU', lab)
lab.HAL('QPU').add_qubit(lab.HAL('Qubit1'))
lab.HAL('QPU').add_qubit(lab.HAL('Qubit2'))
lab.HAL('QPU').add_qubit_coupling('Qubit1', 'Qubit2', lab.HAL('Cpl12'))

zi_qpu, zi_qubits, z_qcouplers = lab.HAL('QPU').get_ZI_parameters()

zi_qpu, zi_qubits, z_qcouplers = lab.HAL('QPU').get_ZI_parameters()

lab.HAL('Qubit1').ResetTime = 50e-9
lab.HAL('Qubit2').ResetTime = 50e-9

# zi_qpu.topology.plot()
# plt.show()

ZIACQ('ZIacq', lab, 'zi_boxes')
lab.HAL('ZIacq').NumRepetitions = 2042

from sqdtoolz.Experiments.Experimental.ZI import flux_scope
from sqdtoolz.Experiments.Experimental.ZI import cryo_scope
from sqdtoolz.Experiments.Experimental.ExpZIFluxscope import ExpZIFluxscope
from laboneq.simulator.output_simulator import OutputSimulator

ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')
frequencies = lab.HAL('Qubit1').DriveGE + np.linspace(0, 500e6, 5)

flux_amplitudes = np.linspace(0.1,1.0,3)
flux_lengths = np.linspace(10e-9, 80e-9,3)

exp = ExpZIFluxscope('test', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Qubit1', 'Qubit2'])
exp.run(lab, debug_skip_experiment=True)     


# exp = ExpZIqubit('test', lab.CONFIG('ZI'), cryo_scope, lab.HAL('QPU'),
#                  ['Qubit1', 'Qubit2'], lengths = flux_lengths, amplitudes=flux_amplitudes)
# lab.run_single(exp, debug_skip_experiment=True)
