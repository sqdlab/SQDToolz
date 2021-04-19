from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\SGS100A_Test.yaml", save_dir = "mySaves\\")


#Can be done in YAML
# instr_ddg = DDG_DG645('ddg_real')
# new_exp.add_instrument(instr_ddg)

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
ddg_module = DDG(new_lab._station.load_pulser())
ddg_module.get_trigger_output('AB').TrigPulseLength = 50e-9
ddg_module.get_trigger_output('AB').TrigPolarity = 1
ddg_module.get_trigger_output('AB').TrigPulseDelay = 10e-9
ddg_module.get_trigger_output('CD').TrigPulseLength = 5e-6
ddg_module.get_trigger_output('CD').TrigPulseDelay = 0e-9
ddg_module.get_trigger_output('CD').TrigPolarity = 1
ddg_module.get_trigger_output('EF').TrigPulseLength = 400e-9
ddg_module.get_trigger_output('EF').TrigPulseDelay = 250e-9
ddg_module.get_trigger_output('EF').TrigPolarity = 0
ddg_module._instr_ddg.trigger_rate(0.1e6)

freq_module = GENmwSource(new_lab._station.load_SGS100A().get_output('RFOUT'))

freq_module.Power = 0
freq_module.Output = True
freq_module.Mode = 'PulseModulated'

input('press <ENTER> to continue')
