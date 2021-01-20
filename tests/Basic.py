from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.TimingConfiguration import*

new_exp = Experiment(instr_config_file = "", save_dir = "", name="test")

#Can be done in YAML
instr_ddg = DummyDDG('ddg')
new_exp.add_instrument(instr_ddg)

ddg_module = DDG(instr_ddg)
ddg_module.get_output('A').TrigPulseLength = 50e-9
ddg_module.get_output('A').TrigPolarity = 1
ddg_module.get_output('B').TrigPulseLength = 100e-9
ddg_module.get_output('B').TrigPulseDelay = 50e-9
ddg_module.get_output('B').TrigPolarity = 1
ddg_module.get_output('C').TrigPulseLength = 400e-9
ddg_module.get_output('C').TrigPulseDelay = 250e-9
ddg_module.get_output('C').TrigPolarity = 0

tc = TimingConfiguration(1e-6, [ddg_module])
lePlot = tc.plot().show()
input('press <ENTER> to continue')
