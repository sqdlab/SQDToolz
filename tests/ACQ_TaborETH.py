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

import numpy as np
import scipy.signal
from sqdtoolz.Variable import*
from sqdtoolz.Laboratory import*
import sqdtoolz as stz

import matplotlib.pyplot as plt

#SETUP:
# Connected Tabor AWG CH1 to ETH FPGA CH1
# Connected Tabor AWG CH2 to ETH FPGA CH2
# Connected DDG AB to Tabor AWG TRIG1
# Connected Tabor CH1 M2 to ETH FPGA TRIG

#Running:
# test_traces - should show two sets of concurrent traces on both IQ-channels with the black trace being the average of all (should appear in middle). Given the phases, the diagonal plots should look similar...
# test_averaging - should produce a star with the colours all concurrent on its corners. CH2 should have its star rotated by 90°




lab = Laboratory(instr_config_file = "tests\\ACQ_TaborETH.yaml", save_dir = "mySaves\\")

lab.load_instrument('fpga1')
stz.ACQ('ETHFPGA', lab, 'fpga1')

lab.load_instrument('pulser')
stz.DDG("DDG", lab, 'pulser')

lab.load_instrument('TaborAWG')

lab.HAL('DDG').get_trigger_output('AB').TrigPulseLength = 50e-9
lab.HAL('DDG').get_trigger_output('AB').TrigPolarity = 1
lab.HAL('DDG').get_trigger_output('AB').TrigPulseDelay = 0.0e-9
lab.HAL('DDG').get_trigger_output('AB').TrigEnable = True ###


def test_traces(lab):
    WFMT_ModulationIQ("OscMod", lab, 25e6)

    #Set AWG to trigger ETHFPGA
    stz.WaveformAWG("WfmConRes", lab, [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH2')], 2.0e9)
    lab.HAL("WfmConRes").set_valid_total_time(99e-6)
    lab.HAL("WfmConRes").clear_segments()
    lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("zeros", None, 1e-6, 0.0))
    lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("pulse", lab.WFMT("OscMod").apply(phase = 0), 20e-6, 0.25))
    lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("zeros1", None, 30e-6, 0.0))
    lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("pulse2", lab.WFMT("OscMod").apply(phase = np.pi), 20e-6, 0.125))
    lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("zeros2", None, -1, 0.0))
    #lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("pad", None, 64e-9, 0.0))
    #lab.HAL("WfmConRes").add_waveform_segment(stz.WFS_Constant("pulse", lab.WFMT('QubitFreqGE').apply(), 2**17 * 2e-9, 0.2)) # set the amplitude to roughly the pi amplitude
    lab.HAL("WfmConRes").get_output_channel(0).marker(0).set_markers_to_segments(['pulse','pulse2'])
    lab.HAL("WfmConRes").get_output_channel(0).marker(1).set_markers_to_segments(['pulse','pulse2'])
    lab.HAL("WfmConRes").set_trigger_source_all(lab.HAL("DDG").get_trigger_output('AB'))
    lab.HAL("ETHFPGA").set_trigger_source(lab.HAL("WfmConRes").get_output_channel(0).marker(1))

    lab.HAL("DDG").RepetitionTime = 500e-6#1.1e-3 1e-6

    lab.HAL("ETHFPGA").set_acq_params(reps=6, segs=1, samples=4096)
    lab.HAL("ETHFPGA").ChannelStates = (True, True)

    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6], [25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 1e6, 'Taps' : 40, 'Win' : 'hamming'}]]*2))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))

    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))

    ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
    new_exp = Experiment('test', lab.CONFIG('contMeas'))
    leData = lab.run_single(new_exp, [])
    arr = leData.get_numpy_array()

    fig, ax = plt.subplots(nrows=2,ncols=2); ax[0,0].set_title('CH1 I-Channel'); ax[1,0].set_title('CH1 Q-Channel'); ax[0,1].set_title('CH2 I-Channel'); ax[1,1].set_title('CH2 Q-Channel')
    for r in range(lab.HAL("ETHFPGA").NumRepetitions) :
        for s in range(lab.HAL("ETHFPGA").NumSegments) :
            ax[0,0].plot(arr[r,s,:,0])
            ax[1,0].plot(arr[r,s,:,1])
            ax[0,1].plot(arr[r,s,:,2])
            ax[1,1].plot(arr[r,s,:,3])

    #Now test averaged traces...

    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6], [25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 1e6, 'Taps' : 40, 'Win' : 'hamming'}]]*2))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))
    lab.PROC('fpga_dsp').add_stage(FPGA_Mean('repetition'))

    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))

    ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
    new_exp = Experiment('test', lab.CONFIG('contMeas'))
    leData = lab.run_single(new_exp, [])
    arr = leData.get_numpy_array()

    for s in range(lab.HAL("ETHFPGA").NumSegments):
        ax[0,0].plot(arr[s,:,0], 'k-')
        ax[1,0].plot(arr[s,:,1], 'k-')
        ax[0,1].plot(arr[s,:,2], 'k-')
        ax[1,1].plot(arr[s,:,3], 'k-')

def test_averaging(lab, num_corners=12):
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
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)

        awg_wfm.prepare_initial()
        awg_wfm.prepare_final()
        # Set output channel to true
        awg_wfm.get_output_channel(0).Output = True
        awg_wfm.get_output_channel(1).Output = True
    #
    lab.HAL("DDG").RepetitionTime = 500e-6  #26*12 = 312us
    add_segments_circle(lab.HAL("WfmConRes"), np.array([0.1,0.1]), num_corners, poly_size=0.1)
    lab.HAL("ETHFPGA").set_acq_params(reps=int(num_corners*5), segs=1, samples=512)
    #
    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6], [25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]*2))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('segment'))
    lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))
    #

    ExperimentConfiguration('contMeas', lab, 500e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
    new_exp = Experiment('test', lab.CONFIG('contMeas'))
    leData = lab.run_single(new_exp, [])
    arr = leData.get_numpy_array()

    fig, ax = plt.subplots(ncols=2); ax[0].set_title('CH1 IQ-Plane'); ax[1].set_title('CH2 IQ-Plane')
    for r in range(num_corners):
        ax[0].plot(arr[r::num_corners,0], arr[r::num_corners,1], '*')
        ax[1].plot(arr[r::num_corners,2], arr[r::num_corners,3], '*')


    #Plot the average now...

    lab.HAL("ETHFPGA").NumRepetitions = num_corners
    #
    ProcessorFPGA('fpga_dsp', lab)
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6], [25e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]*2))
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

    ax[0].plot([arr[0]], [arr[1]], 'k*')
    ax[1].plot([arr[2]], [arr[3]], 'k*')


test_traces(lab)
test_averaging(lab)

plt.show()
a=0
