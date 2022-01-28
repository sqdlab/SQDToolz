from sqdtoolz.Experiment import Experiment
from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.HAL.ACQvna import*
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

lab = Laboratory(instr_config_file = "tests\\VNA_Agilent_N5232A_Test.yaml", save_dir = "mySaves\\")

#Sample Clock
lab.load_instrument('vna') #('vna_agilent')
test_vna = ACQvna('VNA', lab, 'vna') #'vna_agilent')

test_vna.FrequencyStart = 10e6
test_vna.FrequencyEnd = 6e9

# test_vna.FrequencySingle = 500e6
# test_vna.SweepMode = 'Time-1f'
# x_var = 'time' #'power' #'frequency'

# test_vna.setup_segmented_sweep([(10e6,100e6,5), (500e6,1000e6,5), (1000e6,5000e6,5)])
# x_var = 'frequency'

# test_vna.SweepMode = 'Linear'
# x_var = 'frequency'

# test_vna.set_measurement_parameters([(2,1)])

# test_vna.SweepPoints = 801

# test_vna.AveragesEnable = False
# test_vna.AveragesNum = 8s_data_raw
# test_vna.Bandwidth = 100e3

lab.HAL('VNA').FrequencyCentre = 6.817e9
lab.HAL('VNA').FrequencySpan = 20e6
lab.HAL('VNA').Power = -20
lab.HAL('VNA').SweepMode = 'Linear'
lab.HAL('VNA').set_measurement_parameters([(2,1)])
lab.HAL('VNA').SweepPoints = 10001
lab.HAL('VNA').AveragesEnable = False
lab.HAL('VNA').AveragesNum = 1
lab.HAL('VNA').Bandwidth = 200



# cur_time = time.time()
# test_vna.NumRepetitions = 200
# leData = test_vna.get_data()
# cur_time = time.time() - cur_time

expConfig = ExperimentConfiguration('vna_sweep', lab, 0, [], "VNA")
vna_sweep = Experiment("VNA_coarse_sweep", lab.CONFIG('vna_sweep'))
leData = lab.run_single(vna_sweep)

arr = leData.get_numpy_array()
s23s = np.sqrt(arr[0][:,0]**2 + arr[0][:,1]**2)
plt.plot(leData.param_vals[1], s23s)
# s22s = np.sqrt(leData['data']['S11_real']**2 + leData['data']['S11_imag']**2)
# plt.plot(leData['parameter_values'][x_var], s22s[0])
plt.show()

input('press <ENTER> to continue')
