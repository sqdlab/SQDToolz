from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformModulations import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyACQex import*
from sqdtoolz.Drivers.dummyAWG import*
from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Parameter import*
from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_Max import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*

new_lab = Laboratory(instr_config_file = "", save_dir = "mySaves\\")

#Can be done in YAML
instr_ddg = DummyDDG('ddg')
new_lab.add_instrument(instr_ddg)
instr_acq = DummyACQex('acq')
new_lab.add_instrument(instr_acq)
instr_awg = DummyAWG('awg_test_instr')
new_lab.add_instrument(instr_awg)
instr_fsrc = DummyGENmwSrc('freq_src_instr')
new_lab.add_instrument(instr_fsrc)

ddg_module = DDG('DDG', new_lab, 'ddg')
awg_wfm_q = WaveformAWG("Waveform 2", new_lab, [('awg_test_instr', 'CH3'),('awg_test_instr', 'CH4')], 1e9)
acq_module = ACQ('ACQ', new_lab, 'acq')
freq_src_module = GENmwSource('MWS', new_lab, 'freq_src_instr', 'CH1')

param_cav_freq = new_lab.add_parameter_property('Cavity Frequency', freq_src_module, 'Frequency')

#Setup the trigger and instrument relations
ddg_module.set_trigger_output_params('A', 0.0, 50e-9)
acq_module.set_trigger_source(awg_wfm_q.get_output_channel(0).marker(0))
awg_wfm_q.set_trigger_source_all(ddg_module.get_trigger_output('A'))
acq_module.SampleRate = 1e9
acq_module.NumSamples = 100
acq_module.NumSegments = 1
acq_module.NumRepetitions = 200
#Cement the parameters into the experiment configuration
exp_config = ExperimentConfiguration(100e-9, [ddg_module, awg_wfm_q, freq_src_module], acq_module)

#Create a blank waveform with a marker to trigger the acquisition
awg_wfm_q.add_waveform_segment(WFS_Gaussian("blank", None, 128e-9, 0.0))
awg_wfm_q.add_waveform_segment(WFS_Constant("pad", None, 128e-9, 0.0))
awg_wfm_q.get_output_channel().marker(0).set_markers_to_trigger()
awg_wfm_q.get_output_channel().marker(0).TrigPulseDelay = 0e-9
awg_wfm_q.get_output_channel().marker(0).TrigPulseLength = 30e-9
# awg_wfm_q.AutoCompression = 'Basic'

# exp_config.plot().show()
# input('press <ENTER> to continue')

myProc = ProcessorCPU()
myProc.add_stage(CPU_Max('sample'))
myProc.add_stage(CPU_Max('segment'))
# myProc.add_stage(CPU_Mean('repetition'))    #This should cause an error when run
myProc.add_stage_end(CPU_Mean('repetition'))
acq_module.set_data_processor(myProc)

param_blank_amp = new_lab.add_parameter_property('Blank Amplitude', awg_wfm_q.get_waveform_segment("pad"), 'Value')

new_exp = Experiment("cav_exp", exp_config)
leData = new_lab.run_single(new_exp, [(param_cav_freq, np.linspace(100e9,500e9,500))])
# leData = new_lab.run_single(new_exp, [(param_blank_amp, np.linspace(1,5,500))])
a=0
