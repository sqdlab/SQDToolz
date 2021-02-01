from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyACQ import*
from sqdtoolz.Drivers.dummyAWG import*
from sqdtoolz.TimingConfiguration import*

new_exp = Experiment(instr_config_file = "", save_dir = "C:\\Users\\uqppakk1\\Desktop\\WorkUQ\\sqdtoolz\\save_dir\\", name="test")

#Can be done in YAML
instr_ddg = DummyDDG('ddg')
new_exp.add_instrument(instr_ddg)
instr_acq = DummyACQ('acq')
new_exp.add_instrument(instr_acq)
instr_awg = DummyAWG('awg')
new_exp.add_instrument(instr_awg)

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

awg_wfm = WaveformAWG([(instr_awg, 'CH2')], 1e9)
awg_wfm.add_waveform_segment(WFS_Gaussian("init", 35e-9, 0.8))
awg_wfm.add_waveform_segment(WFS_Constant("hold", 25e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Constant("read", 50e-9, 0.0))
awg_wfm.get_output_channel().Amplitude = 1.0
awg_wfm.get_trigger_output().set_markers_to_trigger()
awg_wfm.get_trigger_output().TrigPulseDelay = 25e-9
awg_wfm.get_trigger_output().TrigPulseLength = 30e-9
awg_wfm.program_AWG()
#
awg_wfm2 = WaveformAWGIQ([(instr_awg, 'CH3'),(instr_awg, 'CH4')], 1e9, 100e6)
awg_wfm2.add_waveform_segment(WFS_Gaussian("init", 75e-9, 1.0))
awg_wfm2.add_waveform_segment(WFS_Constant("hold", 45e-9, 0.5))
awg_wfm2.add_waveform_segment(WFS_Gaussian("pulse", 75e-9, 1.0))
awg_wfm2.add_waveform_segment(WFS_Constant("read", 150e-9, 0.0))
awg_wfm2.get_output_channel(0).Amplitude = 1.0
awg_wfm2.get_trigger_output(0).set_markers_to_segments(["hold"])
awg_wfm2.get_trigger_output(1).set_markers_to_none()
awg_wfm2.program_AWG()
# lePlot = awg_wfm2.plot_waveforms().show()
# input('press <ENTER> to continue')
#
# acq_module.set_trigger_source(awg_wfm, 0)

# awg.set_trigger_source(ddg_module, 'A')

tc = TimingConfiguration(1e-6, [ddg_module], [awg_wfm,awg_wfm2], acq_module)
configTc = tc.save_config()
ddg_module.get_trigger_output('C').TrigPolarity = 1
acq_module.set_trigger_source(ddg_module, 'C')
tc.update_config(configTc)


# lePlot = tc.plot().show()
# input('press <ENTER> to continue')

leData = new_exp.run(tc)

input('press <ENTER> to continue')


# new_exp.savetc(tc, 'base')
# ;;;;;;;;
# new_exp.savetc(tc, 'cav')

# new_exp.load.   
