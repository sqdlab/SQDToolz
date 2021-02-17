from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformModulations import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyACQ import*
from sqdtoolz.Drivers.dummyAWG import*
from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Parameter import*

new_lab = Laboratory(instr_config_file = "", save_dir = "mySaves\\")

#Can be done in YAML
instr_ddg = DummyDDG('ddg')
new_lab.add_instrument(instr_ddg)
instr_acq = DummyACQ('acq')
new_lab.add_instrument(instr_acq)
instr_awg = DummyAWG('awg_test_instr')
new_lab.add_instrument(instr_awg)
instr_fsrc = DummyGENmwSrc('freq_src_instr')
new_lab.add_instrument(instr_fsrc)

ddg_module = DDG(instr_ddg)
awg_wfm_q = WaveformAWG("Waveform 2 CH", [(instr_awg, 'CH3'),(instr_awg, 'CH4')], 1e9)
acq_module = ACQ(instr_acq)
freq_src_module = GENmwSource(instr_fsrc.get_output('CH1'))

param_cav_freq = new_lab.add_parameter_property('Cavity Frequency', freq_src_module, 'Frequency')

#Setup the trigger and instrument relations
ddg_module.set_trigger_output_params('A', 0.0, 50e-9)
acq_module.set_trigger_source(awg_wfm_q.get_output_channel(0).marker(0))
awg_wfm_q.set_trigger_source_all(ddg_module.get_trigger_output('A'))
acq_module.SampleRate = 1e9
acq_module.NumSamples = 100
#Cement the parameters into the experiment configuration
exp_config = ExperimentConfiguration(100e-9, [ddg_module], [awg_wfm_q], acq_module, [freq_src_module])

#Create a blank waveform with a marker to trigger the acquisition
awg_wfm_q.add_waveform_segment(WFS_Gaussian("blank", None, 75e-9, 0.0))
awg_wfm_q.get_output_channel().marker(0).set_markers_to_trigger()
awg_wfm_q.get_output_channel().marker(0).TrigPulseDelay = 0e-9
awg_wfm_q.get_output_channel().marker(0).TrigPulseLength = 30e-9

# exp_config.plot().show()
# input('press <ENTER> to continue')

new_exp = Experiment("cav_exp", exp_config)
leData = new_lab.run_single(new_exp, [(param_cav_freq, np.linspace(100e9,500e9,5))])
