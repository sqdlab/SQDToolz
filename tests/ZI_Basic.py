import numpy as np
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

from sqdtoolz.HAL.ZI.ZIQubit import ZIQubit
from sqdtoolz.HAL.ZI.ZIACQ import ZIACQ
from sqdtoolz.HAL.SOFTqpu import SOFTqpu
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit


lab = Laboratory(instr_config_file = "tests/ZI_Basic.yaml", save_dir = "mySaves\\")

lab.load_instrument('zi_boxes')
ZIQubit('Qubit1', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'))
ZIQubit('Qubit1', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/1/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'))

SOFTqpu('QPU', lab)
lab.HAL('QPU').add_qubit(lab.HAL('Qubit1'))

ZIACQ('ZIacq', lab, 'zi_boxes')

from laboneq_applications.experiments import (
    qubit_spectroscopy,
    qubit_spectroscopy_amplitude,
)

ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')

exp = ExpZIqubit('test', lab.CONFIG('ZI'), qubit_spectroscopy, lab.HAL('QPU'), ['Qubit1'], frequencies=[np.linspace(5.8e9, 6.2e9, 101)])
lab.run_single(exp)
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

