import sqdtoolz as stz
from sqdtoolz.Experiments.Experimental.ExpVNAPointTrigger import ExpVNAPointTrigger
import numpy as np

lab = stz.Laboratory(instr_config_file = r'tests/VNA_P9373A.yaml',save_dir = r'mySaves/')

lab.load_instrument('vna')
stz.ACQvna('VNA', lab, 'vna')

stz.VariableInternal('dummy', lab)

lab.HAL('VNA').Power = 10 # dBm
lab.HAL('VNA').FrequencySingle = 9.381794e9
lab.HAL('VNA').SweepMode = 'Time-1f'
lab.HAL('VNA').set_measurement_parameters([(2,1)])
lab.HAL('VNA').SweepPoints = 201
lab.HAL('VNA').AveragesEnable = False
lab.HAL('VNA').AveragesNum = 1
lab.HAL('VNA').Bandwidth = 100e3

stz.ExperimentConfiguration('vna_time', lab, 0, [], "VNA")

trig_exp = ExpVNAPointTrigger('trig_exp', lab.CONFIG('vna_time'))

leData = lab.run_single(trig_exp, [(lab.VAR('dummy'), np.arange(201))])

print('DONE')