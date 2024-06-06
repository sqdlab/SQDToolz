from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyACQex import*
from sqdtoolz.Drivers.dummyAWG import*
from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Variable import*
from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_Max import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*

import numpy as np

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
acq_module = ACQ('ACQ', new_lab, 'acq')
freq_src_module = GENmwSource('mwSrc', new_lab, 'freq_src_instr', 'CH1')

mod_freq_qubit = WFMT_ModulationIQ("QubitFreqMod", new_lab, 100e6)

awg_wfm = WaveformAWG("wfm_test", new_lab, [('awg_test_instr', 'CH1'),('awg_test_instr', 'CH2')], 1e9, 4e-6)
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", mod_freq_qubit.apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
awg_wfm.get_output_channel(0).reset_software_triggers(2)
awg_wfm.get_output_channel(0).software_trigger(0).set_markers_to_segments([ 'init' ])
awg_wfm.get_output_channel(0).software_trigger(1).set_markers_to_segments([ 'zero1', 'zero2' ])

#Setup the trigger and instrument relations
ddg_module.set_trigger_output_params('A', 0.0, 50e-9)
acq_module.set_trigger_source(awg_wfm.get_output_channel(0).marker(0))
awg_wfm.set_trigger_source_all(ddg_module.get_trigger_output('A'))
acq_module.SampleRate = 1e9
acq_module.NumSamples = 100
acq_module.NumRepetitions = 100
#Attach a CPU post-processor
myProc = ProcessorCPU('leProc', new_lab)
myProc.add_stage(CPU_Max('sample'))
myProc.add_stage(CPU_Mean('repetition'))
acq_module.set_data_processor(myProc)

#Cement the parameters into the experiment configuration
exp_config = ExperimentConfiguration('V_sweep', new_lab, 5e-6, ['DDG', 'wfm_test'], 'ACQ')

#Check that the properties for software triggers are saved properly...
leConfig = exp_config.save_config()
awg_wfm.get_output_channel(0).reset_software_triggers()
exp_config.update_config(leConfig)

exp_config.plot()
plt.show()

input('press <ENTER> to continue')

exp_rabi = Experiment("myRabi", exp_config)
leData = new_lab.run_single(exp_rabi)
# input('press <ENTER> to continue')

# lePlot = exp_config.plot().show()
# input('press <ENTER> to continue')
