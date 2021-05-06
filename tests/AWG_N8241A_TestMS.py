from sqdtoolz.Experiment import Experiment
from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.HAL.DDG import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Drivers.Agilent_N8241A import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.GENmwSource import*
import numpy as np
from sqdtoolz.Variable import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*


new_lab = Laboratory(instr_config_file = "tests\\AWG_N8241A_TestMS.yaml", save_dir = "mySaves\\")

#Note the following:
# - Using a 1.25GHz clock source to split and driven into the EXT CLK IN inputs of both Agilent AWGs
# - SYNC CLK OUT on Master goes into SYNC CLK IN on Slave
# - Using M4 on master to trigger the slave AWG via Trigger 4 (could simply do this by just routing the clock lines to both AWGs...)
# - The DDG output triggers the first master AWG
# - Also using an external 10MHz reference on the AWG...

#Sample Clock
new_lab.load_instrument('SGS100A')
freq_module = GENmwSource('MW_sample_clock', new_lab, 'SGS100A', 'RFOUT')
freq_module.Output = True

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
new_lab.load_instrument('pulser')
ddg_module = DDG('ddg', new_lab, 'pulser')
ddg_module.get_trigger_output('AB').TrigPulseLength = 500e-9
ddg_module.get_trigger_output('AB').TrigPolarity = 1
ddg_module.get_trigger_output('AB').TrigPulseDelay = 0e-9
ddg_module.RepetitionTime = 2.5e-6

mod_freq_qubit = WFMT_ModulationIQ("QubitFreqMod", new_lab, 100e6)

new_lab.load_instrument('Agi1')
awg_wfm_q = WaveformAWG("Waveform 1", new_lab, [('Agi1', 'ch1'),('Agi1', 'ch2')], 1.25e9)
awg_wfm_q.add_waveform_segment(WFS_Constant("SEQ", None, 512e-9, 0.0))
awg_wfm_q.add_waveform_segment(WFS_Constant("init", mod_freq_qubit.apply(), 512e-9, 0.5))
awg_wfm_q.add_waveform_segment(WFS_Constant("zero1", None, 512e-9, 0.25))
awg_wfm_q.add_waveform_segment(WFS_Gaussian("init2", mod_freq_qubit.apply(), 512e-9, 0.5))
awg_wfm_q.add_waveform_segment(WFS_Constant("zero2", None, 512e-9*10, 0.0))
awg_wfm_q.get_output_channel(0).marker(1).set_markers_to_segments(["init"])
awg_wfm_q.get_output_channel(1).marker(0).set_markers_to_segments(["SEQ", "init"])
awg_wfm_q.AutoCompression = 'Basic'
awg_wfm_q.AutoCompressionLinkChannels = True

#Check multi-program works
# input('press <ENTER> to continue')
# awg_wfm_q.add_waveform_segment(WFS_Gaussian("init", mod_freq_qubit, 512e-9, 0.5))
# awg_wfm_q.program_AWG()

awg_wfm_q.get_output_channel(0).Output = True

new_lab.load_instrument('Agi2')
awg_wfm_q2 = WaveformAWG("Waveform 2", new_lab, [('Agi2', 'ch1'),('Agi2', 'ch2')], 1.25e9)
awg_wfm_q2.add_waveform_segment(WFS_Gaussian("init", None, 512e-9, 0.5))
awg_wfm_q2.add_waveform_segment(WFS_Constant("zero1", mod_freq_qubit.apply(), 512e-9, 0.25))
awg_wfm_q2.add_waveform_segment(WFS_Gaussian("init2", mod_freq_qubit.apply(), 512e-9, 0.5))
awg_wfm_q2.add_waveform_segment(WFS_Constant("zero2", None, 512e-9*10, 0.0))
awg_wfm_q2.get_output_channel(0).marker(0).set_markers_to_segments(["init","init2"])
awg_wfm_q2.AutoCompression = 'Basic'
awg_wfm_q.AutoCompressionLinkChannels = True

awg_wfm_q.prepare_initial()
awg_wfm_q2.prepare_initial()
awg_wfm_q.prepare_final()
awg_wfm_q2.prepare_final()
awg_wfm_q.activate()
awg_wfm_q2.activate()

input('press <ENTER> to continue')
