from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyACQ import*
from sqdtoolz.TimingConfiguration import*

new_exp = Experiment(instr_config_file = "", save_dir = "", name="test")

#Can be done in YAML
instr_ddg = DummyDDG('ddg')
new_exp.add_instrument(instr_ddg)
instr_acq = DummyACQ('acq')
new_exp.add_instrument(instr_acq)

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
ddg_module = DDG(instr_ddg)
ddg_module.set_trigger_output_params('A', 50e-9)
ddg_module.get_trigger_output('B').TrigPulseLength = 100e-9
ddg_module.get_trigger_output('B').TrigPulseDelay = 50e-9
ddg_module.get_trigger_output('B').TrigPolarity = 1
ddg_module.get_trigger_output('C').TrigPulseLength = 400e-9
ddg_module.get_trigger_output('C').TrigPulseDelay = 250e-9
ddg_module.get_trigger_output('C').TrigPolarity = 0

temp_config = ddg_module._get_current_config()
ddg_module.get_trigger_output('C').TrigPolarity = 1
ddg_module._set_current_config(temp_config, instr_ddg)

acq_module = ACQ(instr_acq)
acq_module.NumSamples = 500
acq_module.SampleRate = 1e9
acq_module.TriggerEdge = 0
acq_module.set_trigger_source(ddg_module, 'B')

# awg.set_trigger_source(ddg_module, 'A')

tc = TimingConfiguration(1e-6, [ddg_module], acq_module)
configTc = tc.save_config()
ddg_module.get_trigger_output('C').TrigPolarity = 1
acq_module.set_trigger_source(ddg_module, 'C')
tc.update_config(configTc)

import json
with open('data.txt', 'w') as outfile:
    json.dump(configTc, outfile, indent=4)

lePlot = tc.plot().show()
input('press <ENTER> to continue')


# new_exp.savetc(tc, 'base')
# ;;;;;;;;
# new_exp.savetc(tc, 'cav')

# new_exp.load.   
