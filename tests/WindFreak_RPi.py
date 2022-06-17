from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\WindFreak_RPi.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('MWS_Windfreak')
freq_module = GENmwSource("MW_TestA", new_lab, 'MWS_Windfreak', 'RFoutA')

freq_module.Power = 0
freq_module.Output = True
freq_module.Frequency = 4e9
freq_module.Mode = 'Continuous'

input('press <ENTER> to continue')
