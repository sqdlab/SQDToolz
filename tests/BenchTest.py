from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.TimingConfiguration import*

new_exp = Experiment(instr_config_file = "tests\\BenchTest.yaml", save_dir = "", name="test")

#Can be done in YAML
# instr_ddg = DDG_DG645('ddg_real')
# new_exp.add_instrument(instr_ddg)

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
ddg_module = DDG(new_exp._station.load_pulser())
ddg_module.get_trigger_output('AB').TrigPulseLength = 50e-9
ddg_module.get_trigger_output('AB').TrigPolarity = 1
ddg_module.get_trigger_output('AB').TrigPulseDelay = 10e-9
ddg_module.get_trigger_output('CD').TrigPulseLength = 100e-9
ddg_module.get_trigger_output('CD').TrigPulseDelay = 50e-9
ddg_module.get_trigger_output('CD').TrigPolarity = 1
ddg_module.get_trigger_output('EF').TrigPulseLength = 400e-9
ddg_module.get_trigger_output('EF').TrigPulseDelay = 250e-9
ddg_module.get_trigger_output('EF').TrigPolarity = 0


acq_module = ACQ(new_exp._station.load_fpgaACQ())
acq_module.NumSamples = 50
acq_module.NumSegments = 1
# acq_module.SampleRate = 1e9
# acq_module.TriggerEdge = 0
acq_module.set_trigger_source(ddg_module, 'AB')

# awg.set_trigger_source(ddg_module.get_trigger_source('A'))

tc = TimingConfiguration(1e-6, [ddg_module], [], acq_module)
# lePlot = tc.plot().show()
leData = new_exp.run(tc)
input('press <ENTER> to continue')
