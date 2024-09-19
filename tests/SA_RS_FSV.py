from sqdtoolz.Experiment import Experiment
from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.HAL.ACQsa import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Drivers.Agilent_N8241A import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.GENmwSource import*
import numpy as np
from sqdtoolz.Variable import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*

import matplotlib.pyplot as plt
import time

lab = Laboratory(instr_config_file = "tests\\SA_RS_FSV.yaml", save_dir = "mySaves\\")

#Sample Clock
lab.load_instrument('specAnal') #('vna_agilent')
test_sa = ACQsa('SA', lab, 'specAnal') #'vna_agilent')

test_sa.FrequencyStart = 8.0e6
test_sa.FrequencyEnd = 8.5e9
test_sa.Bandwidth = 100e3

expConfig = ExperimentConfiguration('sa_sweep', lab, 0, [], "SA")
sa_sweep = Experiment("SA_coarse_sweep", lab.CONFIG('sa_sweep'))
leData = lab.run_single(sa_sweep)

arr = leData.get_numpy_array()

plt.plot(leData.param_vals[0], arr)
# s22s = np.sqrt(leData['data']['S11_real']**2 + leData['data']['S11_imag']**2)
# plt.plot(leData['parameter_values'][x_var], s22s[0])
plt.show()

input('press <ENTER> to continue')



