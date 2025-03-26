from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.Experiment import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*

from sqdtoolz.HAL.Processors.ProcessorFPGA import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDC import FPGA_DDC
from sqdtoolz.HAL.Processors.FPGA.FPGA_FIR import FPGA_FIR
from sqdtoolz.HAL.Processors.FPGA.FPGA_Decimation import FPGA_Decimation
from sqdtoolz.HAL.Processors.FPGA.FPGA_Mean import FPGA_Mean
from sqdtoolz.HAL.Processors.FPGA.FPGA_Integrate import FPGA_Integrate
6
import numpy as np
import scipy.signal
from sqdtoolz.Variable import*
from sqdtoolz.Laboratory import*
import sqdtoolz as stz

import matplotlib.pyplot as plt

#SETUP:
# - AWG5014C CH1 to ETH-FPGA CH1
# - AWG5014C CH2 to ETH-FPGA CH2
# - AWG5014C CH1-Mkr1 to ETH-FPGA TRIG
# - DDG AB to AWG5014C Trigger
#
#Output:
# First Plot should show consistently overlapping/identical time-series:
#   - Small region of no signal
#   - Large region with a large step
#   - Large region with no signal
#   - Large region with a inverted large step
#   - Large region with no signal
# Second Plot should show the same time-series, but nice and time-averaged
# Third Plot should show neat starry constellations
# 

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

def test_time_series(lab):
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

    lab.HAL("DDG").RepetitionTime = 500e-6#1.1e-3 1e-6

    lab.HAL("ETHFPGA").set_acq_params(reps=6, segs=1, samples=10000)
    lab.HAL("ETHFPGA").ChannelStates = (True, False)

    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6]]*2))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]*2))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))

    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))

    ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
    new_exp = Experiment('test', lab.CONFIG('contMeas'))
    leData = lab.run_single(new_exp, [])
    arr = leData.get_numpy_array()

    fig, ax = plt.subplots(nrows=2)
    for r in range(lab.HAL("ETHFPGA").NumRepetitions) :
        for s in range(lab.HAL("ETHFPGA").NumSegments) :
            ax[0].plot(arr[r,s,:,0])
            ax[1].plot(arr[r,s,:,1])

stz.WaveformAWG("WfmConRes", lab, [('awg5014C', 'CH1'), ('awg5014C', 'CH2')], 1.2e9)

###################################
#TEST AVERAGING ACROSS REPETITIONS#

def test_avg_reps(lab):
    #Set AWG to trigger ETHFPGA    
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

    lab.HAL("DDG").RepetitionTime = 500e-6#1.1e-3 1e-6

    lab.HAL("ETHFPGA").set_acq_params(reps=6, segs=1, samples=10000)
    lab.HAL("ETHFPGA").ChannelStates = (True, False)

    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))
    lab.PROC('fpga_dsp').add_stage(FPGA_Mean('repetition'))

    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))

    ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
    new_exp = Experiment('test', lab.CONFIG('contMeas'))
    leData = lab.run_single(new_exp, [])
    arr = leData.get_numpy_array()

    fig, ax = plt.subplots(nrows=2)
    for s in range(lab.HAL("ETHFPGA").NumSegments) :
        ax[0].plot(arr[s,:,0])
        ax[1].plot(arr[s,:,0])


####################
#Try constellations#

def test_constellations(lab, num_corners = 6, num_points_per_corner = 5000):
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
    #
    lab.HAL("DDG").RepetitionTime = 500e-6  #26*12 = 312us
    add_segments_circle(lab.HAL("WfmConRes"), np.array([0.1,0.1]), num_corners, poly_size=0.1)
    lab.HAL("ETHFPGA").set_acq_params(reps=int(num_corners*num_points_per_corner), segs=1, samples=64)
    #
    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('segment'))
    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))
    #

    ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
    new_exp = Experiment('test', lab.CONFIG('contMeas'))
    leData = lab.run_single(new_exp, [])
    arr = leData.get_numpy_array()

    fig, ax = plt.subplots(1)
    for r in range(num_corners):
        ax.plot(arr[r::num_corners,0], arr[r::num_corners,1], '*')


    #Plot the average now...

    lab.HAL("ETHFPGA").NumRepetitions = num_corners
    #
    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('segment'))
    lab.PROC('fpga_dsp').add_stage(FPGA_Mean('repetition'))
    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))
    #


    ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
    new_exp = Experiment('test', lab.CONFIG('contMeas'))
    leData = lab.run_single(new_exp, [])
    arr = leData.get_numpy_array()

    ax.plot([arr[0]], [arr[1]], 'k*')



def test_point_averaging(lab):
    WFMT_ModulationIQ("OscMod", lab, 25e6)
    lab.WFMT("OscMod").IQUpperSideband = False

    lab.HAL("WfmConRes").set_valid_total_time(19e-6)
    lab.HAL("WfmConRes").clear_segments()
    lab.HAL("WfmConRes").add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 1e-6, 0.0))
    lab.HAL("WfmConRes").add_waveform_segment(WFS_Constant(f"pad1", None, 2e-6, 0.0))
    lab.HAL("WfmConRes").add_waveform_segment(WFS_Constant(f"constel1", lab.WFMT("OscMod").apply(), 15e-6, 0.09))
    lab.HAL("WfmConRes").add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))

    # Setup trigger 
    lab.HAL("WfmConRes").get_output_channel(0).marker(0).set_markers_to_segments([f"constel1"])

    lab.HAL("WfmConRes").prepare_initial()
    lab.HAL("WfmConRes").prepare_final()
    # Set output channel to true
    lab.HAL("WfmConRes").get_output_channel(0).Output = True
    lab.HAL("WfmConRes").get_output_channel(1).Output = True
    #
    lab.HAL("DDG").RepetitionTime = 20e-6  #26*12 = 312us

    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('segment'))
    lab.PROC('fpga_dsp').add_stage(FPGA_Mean('repetition'))
    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))
    
    stz.VariableInternal('dummy', lab)
    fig, axs = plt.subplots(nrows=2)
    rep_nums = [2**x for x in range(0,16,2)]
    sds_I  = []
    sds_Q  = []
    for reps in rep_nums:
        lab.HAL("ETHFPGA").set_acq_params(reps=int(reps), segs=1, samples=1024)

        ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
        new_exp = Experiment('test', lab.CONFIG('contMeas'))
        leData = lab.run_single(new_exp, [(lab.VAR('dummy'), np.arange(100))])
        arr = leData.get_numpy_array()

        axs[0].plot(arr[:,0])
        axs[1].plot(arr[:,1])
        sds_I.append(np.std(arr[:,0]))
        sds_Q.append(np.std(arr[:,1]))
    axs[0].legend(rep_nums)
    fig, ax = plt.subplots(1)
    ax.loglog(sds_I)
    ax.loglog(sds_Q)
    ax.grid()


# test_time_series(lab)
# test_avg_reps(lab)
# test_constellations(lab, num_corners=6, num_points_per_corner=5000)
test_constellations(lab, num_corners=12, num_points_per_corner=2500)
# test_point_averaging(lab)


plt.show()
a=0


