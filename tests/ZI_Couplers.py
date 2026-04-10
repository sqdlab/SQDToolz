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
lab.HAL('Cpl12').QubitFlux = 'Qubit1'

SOFTqpu('QPU', lab)
lab.HAL('QPU').add_qubit(lab.HAL('Qubit1'))
lab.HAL('QPU').add_qubit(lab.HAL('Qubit2'))
lab.HAL('QPU').add_qubit_coupling('Qubit1', 'Qubit2', lab.HAL('Cpl12'))

zi_qpu, zi_qubits, z_qcouplers = lab.HAL('QPU').get_ZI_parameters()

zi_qpu, zi_qubits, z_qcouplers = lab.HAL('QPU').get_ZI_parameters()

# zi_qpu.topology.plot()
# plt.show()

ZIACQ('ZIacq', lab, 'zi_boxes')

from sqdtoolz.Experiments.Experimental.ZI import calibrate_tunable_transmon_fixed_coupler

ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')

exp = ExpZIqubit('test', lab.CONFIG('ZI'), calibrate_tunable_transmon_fixed_coupler, lab.HAL('QPU'),
                 ['Qubit1', 'Qubit2'],
                 amplitudes=np.linspace(0.1, 1.0, 5),
                 wait_times=np.arange(1e-9, 10e-9, 2e-9))
lab.run_single(exp, debug_skip_experiment=True)
a=0

# lab.load_instrument('MW_IF')

# #LO First Stage (Windfreak Channel A) - 3.4 GHz used, 2.4GHz also possible but not recommended - Lower limit is 1.6 GHz for this mixer
# freq_module_A = GENmwSource("MW_TestA", lab, 'MWS_Windfreak', 'RFoutA')
# freq_module_A.Power = 12
# freq_module_A.Output = True
# freq_module_A.Frequency = 3.4e9
# freq_module_A.Mode = 'Continuous'

# #IF - Using MW source - 500 MHz used
# IF_source = GENmwSource("IF", lab, 'MW_IF', 'RFOUT')
# IF_source.Power = 10
# IF_source.Output = True
# IF_source.Frequency = 400e6
# IF_source.Mode = 'Continuous'

# #LO Second Stage (Windfreak Channel B) - Lower limit for this mixer is 3.7 GHz
# freq_module_B = GENmwSource("MW_TestB", lab, 'MWS_Windfreak', 'RFoutB')
# freq_module_B.Power = 12
# freq_module_B.Output = True
# freq_module_B.Frequency = 8.6e9
# freq_module_B.Mode = 'Continuous'

# input('press <ENTER> to continue')

