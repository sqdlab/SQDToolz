from sqdtoolz.Laboratory import*
from sqdtoolz.HAL.AWG import*
import numpy as np

new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir')
new_lab.load_instrument('virAWG')
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)

ERR_TOL = 5e-13

#
#Test IQ-Modulation
#
#Create unmodulated waveforms first
read_segs = []
read_segs2 = []
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
read_segs += ["init"]
read_segs2 += ["zero2"]
awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
#Gather initial arrays
wfm_unmod = np.vstack(awg_wfm.get_raw_waveforms())
#
#Okay now modulate...
WFMT_ModulationIQ('IQmod', new_lab, 47e7)
WFMT_ModulationIQ('IQmod2', new_lab, 13e7)
#
#Changing phases Test
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled."
#
#Trying two modulation areas
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45) + 60))
temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45) + 60))
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled."
#
#Trying two different modulation areas
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod2').apply(), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega2*1e-9*(np.arange(45) + 60))
temp[1, init2_stencil] *= np.sin(omega2*1e-9*(np.arange(45) + 60))
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when using 2 different modulations."
#
#Trying to manipulate the phase now...
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod').apply(phase=0), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45)))
temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45)))
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when resetting phase to zero."
#
#Trying to manipulate the phase to a non-zero value...
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod').apply(phase=np.pi/2), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45))+np.pi/2)
temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45))+np.pi/2)
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when changing phase to non-zero value."
#
#Trying to manipulate the phase to a negative non-zero value...
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod').apply(phase=-0.4125), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45))-0.4125)
temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45))-0.4125)
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when changing phase to a negative value."
#
#Trying to manipulate the phase offset...
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod').apply(phase_offset=-0.91939), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45)+60)-0.91939)
temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45)+60)-0.91939)
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when changing phase offset."
#
#Trying to manipulate the phase offset and checking relation down the track...
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod').apply(phase_offset=-0.91939), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", new_lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
init3_stencil = np.s_[182:227]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45)+60)-0.91939)
temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45)+60)-0.91939)
temp[0, init3_stencil] *= np.cos(omega*1e-9*(np.arange(45)+182)-0.91939)
temp[1, init3_stencil] *= np.sin(omega*1e-9*(np.arange(45)+182)-0.91939)
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when changing phase offset in a previous waveform segment."
#
#Trying to manipulate the phase and checking relation down the track...
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod').apply(phase=0.1), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", new_lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
init3_stencil = np.s_[182:227]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45))+0.1)
temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45))+0.1)
temp[0, init3_stencil] *= np.cos(omega*1e-9*(np.arange(45)+182-60)+0.1)
temp[1, init3_stencil] *= np.sin(omega*1e-9*(np.arange(45)+182-60)+0.1)
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when changing phase in a previous waveform segment."
#
#Trying to manipulate the phase and checking relation down the track with 2 separate frequencies!...
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(phase=0.1), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", new_lab.WFMT('IQmod2').apply(), 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", new_lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
init2_stencil = np.s_[60:105]
init3_stencil = np.s_[182:227]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
omega2 = 2*np.pi*new_lab.WFMT('IQmod2').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20))+0.1)
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20))+0.1)
temp[0, init2_stencil] *= np.cos(omega2*1e-9*(np.arange(45)+60))
temp[1, init2_stencil] *= np.sin(omega2*1e-9*(np.arange(45)+60))
temp[0, init3_stencil] *= np.cos(omega*1e-9*(np.arange(45)+182-10)+0.1)
temp[1, init3_stencil] *= np.sin(omega*1e-9*(np.arange(45)+182-10)+0.1)
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "The IQ waveform was incorrectly compiled when changing phase in a previous waveform segment with 2 frequencies in play."

#
#Verify the waveform memory requirement checks
#
#Multiple of N check
read_segs = []
read_segs2 = []
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
read_segs += ["init"]
read_segs2 += ["zero2"]
awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
assert_found = False
try:
    awg_wfm.prepare_initial()
    awg_wfm.prepare_final()
except AssertionError:
    assert_found = True
assert assert_found, "The waveform preparation function incorrectly accepts a waveform that does not satisfy the instrument's memory requirement (multiple of 8)."
#
#Minimum N check
read_segs = []
read_segs2 = []
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 1e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 1e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("zero2", None, 1e-9, 0.5-0.1))
read_segs += ["init"]
read_segs2 += ["zero2"]
awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
assert_found = False
try:
    awg_wfm.prepare_initial()
    awg_wfm.prepare_final()
except AssertionError:
    assert_found = True
assert assert_found, "The waveform preparation function incorrectly accepts a waveform that does not satisfy the instrument's memory requirement (minimum of 8)."
#
#Check normal programming works...
read_segs = []
read_segs2 = []
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 12e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 4e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("zero2", None, 8e-9, 0.5-0.1))
read_segs += ["init"]
read_segs2 += ["zero2"]
awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
assert_found = False
awg_wfm.prepare_initial()
awg_wfm.prepare_final()

#
#Check the valid length functions
#
assert awg_wfm.get_valid_length_from_time(12e-9) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
assert awg_wfm.get_valid_length_from_time(16e-9) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
assert awg_wfm.get_valid_length_from_time(5e-9) == [8e-9, 8e-9], "Valid time lengths for a given time are incorrect."
#
assert awg_wfm.get_valid_length_from_pts(12) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
assert awg_wfm.get_valid_length_from_pts(16) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
assert awg_wfm.get_valid_length_from_pts(5) == [8e-9, 8e-9], "Valid time lengths for a given time are incorrect."


#
#Test WFM_Group
#
#Default test with an elastic segment
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "Default waveform compilation failed."
#
#Test a basic WFS_Group construct
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                WFS_Constant("zero1", None, 30e-9, 0.1),
                                WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                ]))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "WFS_Group failed in waveform compilation."
#
#Test a basic WFS_Group construct with elastic time-frame
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init", new_lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                WFS_Constant("zero1", None, -1, 0.1),
                                WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                ], time_len=75e-9))
awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
init_stencil = np.s_[10:30]
temp = wfm_unmod*1.0
omega = 2*np.pi*new_lab.WFMT('IQmod').IQFrequency
temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
assert np.max(np.abs(temp - wfm_mod)) < ERR_TOL, "WFS_Group failed in waveform compilation."



# import matplotlib.pyplot as plt
# plt.plot(wfm_mod[0,:])
# plt.plot(temp[0,:])
# plt.show()
#

print("Waveform Unit Tests completed successfully.")


