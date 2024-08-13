from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\WindFreak.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('MWS_Windfreak')
new_lab.load_instrument('MW_IF')

#LO First Stage (Windfreak Channel A) - 3.4 GHz used, 2.4GHz also possible but not recommended - Lower limit is 1.6 GHz for this mixer
freq_module_A = GENmwSource("MW_TestA", new_lab, 'MWS_Windfreak', 'RFoutA')
freq_module_A.Power = 12
freq_module_A.Output = True
freq_module_A.Frequency = 3.4e9
freq_module_A.Mode = 'Continuous'

#IF - Using MW source - 500 MHz used
IF_source = GENmwSource("IF", new_lab, 'MW_IF', 'RFOUT')
IF_source.Power = 10
IF_source.Output = True
IF_source.Frequency = 400e6
IF_source.Mode = 'Continuous'

#LO Second Stage (Windfreak Channel B) - Lower limit for this mixer is 3.7 GHz
freq_module_B = GENmwSource("MW_TestB", new_lab, 'MWS_Windfreak', 'RFoutB')
freq_module_B.Power = 12
freq_module_B.Output = True
freq_module_B.Frequency = 8.6e9
freq_module_B.Mode = 'Continuous'

input('press <ENTER> to continue')

