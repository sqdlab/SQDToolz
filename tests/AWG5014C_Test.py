from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformModulations import*


new_lab = Laboratory(instr_config_file = "tests\\AWG5014C_Test.yaml", save_dir = "mySaves\\")

instrAWG = new_lab._station.load_awg5014C()
# ch1 = instrAWG.get_output_channel('CH1')
# ch1.output

mod_freq_qubit = WM_SinusoidalIQ("QubitFreqMod", 100e6)

awg_wfm_q = WaveformAWG("Waveform 2 CH", [(instrAWG, 'CH2'),(instrAWG, 'CH3')], 1e9)
awg_wfm_q.add_waveform_segment(WFS_Gaussian("init", mod_freq_qubit, 512e-9, 0.5))
awg_wfm_q.add_waveform_segment(WFS_Constant("zero1", None, 512e-9, 0.25))
awg_wfm_q.add_waveform_segment(WFS_Gaussian("init2", mod_freq_qubit, 512e-9, 0.5))
awg_wfm_q.add_waveform_segment(WFS_Constant("zero2", None, 512e-9, 0.0))
awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(["init","init2"])
awg_wfm_q.program_AWG()

awg_wfm_q.plot_waveforms().show()
input('press <ENTER> to continue')
