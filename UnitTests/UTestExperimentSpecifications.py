from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.ExperimentSpecification import*
from sqdtoolz.Laboratory import*

from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*

from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformMapper import*

import numpy as np


new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir')

new_lab.load_instrument('virACQ')
new_lab.load_instrument('virDDG')
new_lab.load_instrument('virAWG')
new_lab.load_instrument('virMWS')
new_lab.load_instrument('virMWS2')

#Initialise test-modules
hal_acq = ACQ("dum_acq", new_lab, 'virACQ')
hal_ddg = DDG("ddg", new_lab, 'virDDG', )
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
awg_wfm2 = WaveformAWG("Wfm2", new_lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9)
hal_mw = GENmwSource("MW-Src", new_lab, 'virMWS', 'CH1')
hal_mw2 = GENmwSource("MW-Src2", new_lab, 'virMWS2', 'CH1')

ExperimentSpecification('cavity', new_lab)
new_lab.SPEC('cavity').add('Frequency', 0, hal_mw, 'Frequency')

hal_mw.Frequency = 4
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq, ['cavity'])
assert hal_mw.Frequency == 4, "HAL property incorrectly set."
expConfig.init_instruments()
assert hal_mw.Frequency == 0, "HAL property incorrectly loaded from ExperimentSpecification."
new_lab.SPEC('cavity')['Frequency'] = 5.8
assert hal_mw.Frequency == 0, "HAL property incorrectly set."
expConfig.init_instruments()
assert hal_mw.Frequency == 5.8, "HAL property incorrectly set from the ExperimentSpecification."
hal_mw.Frequency = 5
assert hal_mw.Frequency == 5, "HAL property incorrectly set."
expConfig.init_instruments()
assert hal_mw.Frequency == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."

expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq, ['cavity'])
VariableProperty('SrcFreq', new_lab, new_lab.HAL("MW-Src"), 'Frequency')
VariableProperty('DncFreq', new_lab, new_lab.HAL("MW-Src2"), 'Frequency')
VariableSpaced('cavFreq', new_lab, 'SrcFreq', 'DncFreq', 3.5)
new_lab.VAR('cavFreq').Value = 15
assert new_lab.VAR('SrcFreq').Value == 15, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 18.5, "HAL property incorrectly set."
new_lab.SPEC('cavity').set_destination('Frequency', new_lab.VAR('cavFreq'))
assert new_lab.VAR('SrcFreq').Value == 15, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 18.5, "HAL property incorrectly set."
expConfig.init_instruments()
assert new_lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
assert new_lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."
new_lab.VAR('DncFreq').Value = 21
assert new_lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 21, "HAL property incorrectly set."
expConfig.init_instruments()
assert new_lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
assert new_lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."


print("ExperimentSpecification Unit Tests completed successfully.")
