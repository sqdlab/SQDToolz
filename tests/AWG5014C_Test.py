from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*
from sqdtoolz.HAL.GENvoltSource import GENvoltSource

lab = Laboratory(instr_config_file = "tests\\AWG5014C_Test.yaml", save_dir = "mySaves\\")


lab.load_instrument('awg5014C')

WFMT_ModulationIQ('QubitFreqGE', lab, 100e6)

# WaveformAWG("wfm_test", lab, [('awg5014C', 'CH1'), ('awg5014C', 'CH2')], 1.2e9)
# lab.HAL("wfm_test").add_waveform_segment(WFS_Constant("pulse", lab.WFMT('QubitFreqGE').apply(), 2**20 * 2e-9, 0.5)) #0.005 #0.0025
# lab.HAL("wfm_test").add_waveform_segment(WFS_Constant("pad", None, 64e-9, 0.0))
# lab.HAL("wfm_test").get_output_channel(0).marker(0).set_markers_to_segments(['pulse'])
# lab.HAL("wfm_test").AutoCompression = 'None'

WaveformAWG("WfmConMixer", lab, [('awg5014C', 'CH1'), ('awg5014C', 'CH2')], 1.2e9, total_time=1.024e-3)
lab.HAL("WfmConMixer").clear_segments()
lab.HAL("WfmConMixer").add_waveform_segment(WFS_Constant("pad", None, -1, 0.0)) # 64e-9, 
lab.HAL("WfmConMixer").add_waveform_segment(WFS_Constant("pulse", lab.WFMT('QubitFreqGE').apply(), 2**17 * 2e-9, 0.5)) #0.005 #0.0025

lab.HAL("WfmConMixer").get_output_channel(0).marker(0).set_markers_to_segments(['pulse'])


lab.HAL("WfmConMixer").prepare_initial()
lab.HAL("WfmConMixer").prepare_final()

ExperimentConfiguration('testConfig', lab, 2.5e-3, ['WfmConMixer'], None)

lab.CONFIG('testConfig').init_instruments()
lab.CONFIG('testConfig').prepare_instruments()


#Test DC Outputs...
GENvoltSource('vTest', lab, ['awg5014C', 'DC1'])
lab.HAL('vTest').Voltage = 0.1

# awg_wfm_q.plot_waveforms().show()
input('press <ENTER> to continue')
