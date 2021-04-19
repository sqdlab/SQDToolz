from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\WFSynthHDProV2_Test.yaml", save_dir = "mySaves\\")

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
ddg_module = DDG(new_lab._station.load_pulser())
ddg_module.get_trigger_output('AB').TrigPulseLength = 500e-9
ddg_module.get_trigger_output('AB').TrigPolarity = 1
ddg_module.get_trigger_output('AB').TrigPulseDelay = 10e-9
new_lab._station.load_pulser().trigger_rate(500e3)

instr_freq = new_lab._station.load_MWS_Windfreak()
freq_module = GENmwSource(instr_freq.get_output('RFoutA'))
freq_module2 = GENmwSource(instr_freq.get_output('RFoutB'))

freq_module.Power = 0
freq_module.Output = True
freq_module.Frequency = 4e9
freq_module.Mode = 'Continuous'

freq_module2.Power = 0
freq_module2.Output = True
freq_module2.Frequency = 7e9
freq_module2.Mode = 'Continuous'

input('press <ENTER> to continue')
