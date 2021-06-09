from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Experiment import*
from sqdtoolz.Laboratory import*

from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*

from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformMapper import*

import numpy as np
import time


new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

new_lab.load_instrument('virACQ')
new_lab.load_instrument('virDDG')
new_lab.load_instrument('virAWG')
new_lab.load_instrument('virMWS')

#Initialise test-modules
hal_acq = ACQ("dum_acq", new_lab, 'virACQ')
hal_ddg = DDG("ddg", new_lab, 'virDDG', )
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
awg_wfm2 = WaveformAWG("Wfm2", new_lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9)
hal_mw = GENmwSource("MW-Src", new_lab, 'virMWS', 'CH1')

ExperimentConfiguration('testConf', new_lab, 1.0, ['ddg'], 'dum_acq')
#
VariableInternal('myFreq', new_lab)
VariableInternal('testAmpl', new_lab)

new_lab.group_open("test_group")
for m in range(3,6):
    exp = Experiment("test", new_lab.CONFIG('testConf'))
    res = new_lab.run_single(exp, [(new_lab.VAR("myFreq"), np.arange(m))])
    time.sleep(1)
new_lab.group_close()

new_lab.group_open("test_group")
for m in new_lab.VAR("testAmpl").arange(0,4,1):
    exp = Experiment("test", new_lab.CONFIG('testConf'))
    res = new_lab.run_single(exp, [(new_lab.VAR("myFreq"), np.arange(3))])
    time.sleep(1)
new_lab.group_close()
