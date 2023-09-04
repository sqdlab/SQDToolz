from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*
import numpy as np
import scipy
from sqdtoolz.Variable import*
from sqdtoolz.Laboratory import*
import sqdtoolz as stz

import matplotlib.pyplot as plt

lab = Laboratory(instr_config_file = "tests\\ACQ_ETHFPGA.yaml", save_dir = "mySaves\\")

lab.load_instrument('fpga1')
stz.ACQ('ETHFPGA', lab, 'fpga1')

lab.load_instrument('pulser')
stz.DDG("DDG", lab, 'pulser')

#Load AWG
lab.load_instrument('awg5014C')
stz.WaveformAWG("wfm_test", lab, [('awg5014C', 'CH1'), ('awg5014C', 'CH2')], 1.2e9)


#Set DDG to trigger ETHFPGA
#lab.HAL("ETHFPGA").set_trigger_source(lab.HAL("DDG").get_trigger_output('AB'))
lab.HAL('DDG').get_trigger_output('AB').TrigPulseLength = 50e-9
lab.HAL('DDG').get_trigger_output('AB').TrigPolarity = 1
lab.HAL('DDG').get_trigger_output('AB').TrigPulseDelay = 0.0e-9
lab.HAL('DDG').get_trigger_output('AB').TrigEnable = True ###

#Set AWG to trigger ETHFPGA
stz.WaveformAWG("WfmConRes", lab, [('awg5014C', 'CH1'), ('awg5014C', 'CH2')], 1.2e9)
lab.HAL("WfmConRes").set_valid_total_time(99e-6)
lab.HAL("WfmConRes").clear_segments()
lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("zeros", None, 1e-6, 0.0))
lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Cosine("pulse", None, 20e-6, 0.25, 25e6))
lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("zeros1", None, 30e-6, 0.0))
lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Cosine("pulse2", None, 20e-6, 0.125, 25e6, np.pi))
lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("zeros2", None, -1, 0.0))
#lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("pad", None, 64e-9, 0.0))
#lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("pulse", lab.WFMT('QubitFreqGE').apply(), 2**17 * 2e-9, 0.2)) # set the amplitude to roughly the pi amplitude
lab.HAL("WfmConRes").get_output_channel(0).marker(0).set_markers_to_segments(['pulse','pulse2'])
lab.HAL("WfmConRes").set_trigger_source_all(lab.HAL("DDG").get_trigger_output('AB'))

# Prepare waveforms and output them
lab.HAL("WfmConRes").prepare_initial()
lab.HAL("WfmConRes").prepare_final()
# Set output channel to true
lab.HAL("WfmConRes").get_output_channel(0).Output = True
lab.HAL("WfmConRes").get_output_channel(1).Output = True

time.sleep(3)

# lab.HAL("ETHFPGA").set_data_processor(myProc)

lab.HAL("DDG").RepetitionTime = 500e-6#1.1e-3 1e-6

lab.HAL("ETHFPGA").set_acq_params(reps=5, segs=1, samples=1024)
lab.HAL("ETHFPGA").ChannelStates = (True, False)

leData = lab.HAL("ETHFPGA").get_data()

lab.HAL("ETHFPGA")._instr_acq._set('tv_averages', 1)
fig, ax = plt.subplots(nrows=2)
for r in range(lab.HAL("ETHFPGA").NumRepetitions) :
    for s in range(lab.HAL("ETHFPGA").NumSegments) :
        ax[0].plot(leData['data']['ch1_I'][r][s])
        ax[1].plot(leData['data']['ch1_Q'][r][s])

lab.HAL("ETHFPGA")._instr_acq._set('tv_averages', 4)
leData = lab.HAL("ETHFPGA").get_data()
fig, ax = plt.subplots(nrows=2)
for r in range(lab.HAL("ETHFPGA").NumRepetitions) :
    for s in range(lab.HAL("ETHFPGA").NumSegments) :
        ax[0].plot(leData['data']['ch1_I'][r][s])
        ax[1].plot(leData['data']['ch1_Q'][r][s])


WFMT_ModulationIQ("OscMod", lab, 25e6)
lab.WFMT("OscMod").IQUpperSideband = False

def add_segments_circle(awg_wfm, pt_centre, num_corners, poly_size):
    awg_wfm.set_valid_total_time(26e-6*num_corners)
    awg_wfm.clear_segments()
    awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 1e-6, 0.0))
    read_segs = []
    for c in range(num_corners):
        iq_val = pt_centre + (((c % 2) + 1)*0.5 * poly_size)*np.array([np.cos(2*np.pi/num_corners*c), np.sin(2*np.pi/num_corners*c)])
        ampl, phs = np.sqrt(iq_val[0]**2+iq_val[1]**2), np.arctan2(iq_val[1], iq_val[0])
        awg_wfm.add_waveform_segment(WFS_Constant(f"pad{c}", None, 5e-6, 0.0))
        awg_wfm.add_waveform_segment(WFS_Constant(f"constel{c}", lab.WFMT("OscMod").apply(phase=phs), 20e-6, ampl))
        read_segs += [f"constel{c}"]
    awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))

    # Setup trigger 
    awg_wfm.get_output_channel(0).marker(0).set_markers_to_segments(read_segs)

    awg_wfm.prepare_initial()
    awg_wfm.prepare_final()
    # Set output channel to true
    awg_wfm.get_output_channel(0).Output = True
    awg_wfm.get_output_channel(1).Output = True


num_corners = 12
add_segments_circle(lab.HAL("WfmConRes"), np.array([0.1,0.1]), num_corners, poly_size=0.1)
lab.HAL("ETHFPGA").set_acq_params(reps=int(num_corners*5), segs=1, samples=512)

time.sleep(3)

lab.HAL("ETHFPGA")._instr_acq._set('tv_averages', 1)
leData = lab.HAL("ETHFPGA").get_data()
fig, ax = plt.subplots(1)
# for r in range(lab.HAL("ETHFPGA").NumRepetitions) :
#     for s in range(lab.HAL("ETHFPGA").NumSegments) :
#         ax.plot([np.sum(leData['data']['ch1_I'][r][s], axis=-1)], [np.sum(leData['data']['ch1_Q'][r][s], axis=-1)], '*')
for r in range(num_corners):
    for s in range(lab.HAL("ETHFPGA").NumSegments):
        ax.plot(np.sum(leData['data']['ch1_I'][r::num_corners,s,:], axis=-1), np.sum(leData['data']['ch1_Q'][r::num_corners,s,:], axis=-1), '*')

lab.HAL("ETHFPGA").NumRepetitions=1
lab.HAL("ETHFPGA")._instr_acq._set('tv_averages', num_corners)
leData = lab.HAL("ETHFPGA").get_data()
for s in range(lab.HAL("ETHFPGA").NumSegments):
    ax.plot(np.sum(leData['data']['ch1_I'][:,s,:], axis=-1), np.sum(leData['data']['ch1_Q'][:,s,:], axis=-1), 'k*')

# lab.HAL("ETHFPGA")._instr_acq._set('fir_integration')

plt.show()
a=0
#Not required except when running an experiment that does not actively set the frequency...
#lab.VAR('Cavity').Value = lab.VAR('Cavity').Value


