from sqdtoolz.Experiment import Experiment
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

from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*

from sqdtoolz.HAL.Processors.ProcessorFPGA import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDCFIR import FPGA_DDCFIR
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDC import FPGA_DDC
from sqdtoolz.HAL.Processors.FPGA.FPGA_Decimation import FPGA_Decimation
from sqdtoolz.HAL.Processors.FPGA.FPGA_Integrate import FPGA_Integrate
from sqdtoolz.HAL.Processors.FPGA.FPGA_FFT import FPGA_FFT

from sqdtoolz.HAL.Decisions.DEC_SVM import DEC_SVM

import time
import unittest
import matplotlib.pyplot as plt

#Wiring requirements:
#   AWG CH1 to ADC CH1
#   AWG CH2 to ADC CH2
#
#The outputs should contain:
#   - Overlapping sine waves - i.e. raw samples and averaged samples
#   - FFT should show ~70MHz (i.e. 400MHz input with 330MHz demodulation)
#   - Stars with black centres denoting averages.

# Create New Laboratory Class
lab = Laboratory(instr_config_file = "tests\\AWG_Tabor_Test_ADCDSP.yaml", save_dir = "mySaves\\")

# Load the Tabor into the lab class to use
lab.load_instrument('TaborAWG')

WFMT_ModulationIQ("OscMod", lab, 100e6)
lab.WFMT("OscMod").IQUpperSideband = False

pt_centre = np.array([0,0])
num_corners = 12
poly_size = 0.05

def add_segments_circle(awg_wfm, pt_centre, num_corners, poly_size):
    awg_wfm.clear_segments()
    awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 96e-9, 0.25))
    read_segs = []
    for c in range(num_corners):
        iq_val = pt_centre + (((c % 2) + 1)*0.5 * poly_size)*np.array([np.cos(2*np.pi/num_corners*c), np.sin(2*np.pi/num_corners*c)])
        ampl, phs = np.sqrt(iq_val[0]**2+iq_val[1]**2), np.arctan2(iq_val[1], iq_val[0])
        awg_wfm.add_waveform_segment(WFS_Constant(f"pad{c}", None, 512e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Constant(f"constel{c}", lab.WFMT("OscMod").apply(phase=phs), 2048e-9, ampl))
        read_segs += [f"constel{c}"]
    awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))

    # Setup trigger 
    awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(read_segs)

# Setup waveforms
awg_wfm = WaveformAWG("Waveform", lab,  [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH2')], 2.0e9, 40e-6)

acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
acq_module.NumSamples = 5040    #(72*70)
acq_module.NumSegments = 1
acq_module.NumRepetitions = int(num_corners*3)
acq_module.SampleRate = 2.5e9
acq_module.ChannelStates = (True, True)

filt_coeffs = scipy.signal.firwin(51, 10e6, fs=lab._get_instrument('TaborAWG').ACQ.sample_rate())
# acq_module._instr_acq.setup_data_path(ddc_mode = "REAL", ddr_store = "DIR")

ProcessorFPGA('fpga_dsp', lab)

acq_module.NumRepetitions = 30
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 2048e-9, 0.25))
awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))
# Setup trigger 
awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(['init'])
# Prepare waveforms and output them
awg_wfm.prepare_initial()
awg_wfm.prepare_final()
# Set output channel to true
awg_wfm.get_output_channel(0).Output = True
awg_wfm.get_output_channel(1).Output = True
#
# lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}, {'fLO':105e6, 'fc':10e6, 'Taps':40}]]))
lab.PROC('fpga_dsp').reset_pipeline()
lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[105e6],[100e6]]))
lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
acq_module.set_data_processor(lab.PROC('fpga_dsp'))
leData = acq_module.get_data()
#
lab.PROC('fpga_dsp').reset_pipeline()
lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[105e6],[100e6]]))
lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('repetition'))
#
acq_module.set_data_processor(lab.PROC('fpga_dsp'))
leData2 = acq_module.get_data()
#
fig, ax = plt.subplots(nrows=2)
for r in range(acq_module.NumRepetitions) :
    for s in range(acq_module.NumSegments) :
        times = np.arange(acq_module.NumSamples/10)/(acq_module.SampleRate/10) * 1e9
        ax[0].plot(times, leData['data']['CH1_0_I'][r][s])
        ax[1].plot(times, leData['data']['CH1_0_Q'][r][s])
        # ax[0].plot(leData['data']['CH1_1_I'][r][s])
        # ax[1].plot(leData['data']['CH1_1_Q'][r][s])
for s in range(acq_module.NumSegments):
    # times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
    ax[0].plot(times, leData2['data']['CH1_0_I'][s]/acq_module.NumRepetitions)
    ax[1].plot(times, leData2['data']['CH1_0_Q'][s]/acq_module.NumRepetitions)

###########
#FFT TESTS#
###########
lab.WFMT("OscMod").IQFrequency = 400e6
acq_module.NumRepetitions = 3
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 2048e-9, 0.25))
awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))
# Setup trigger 
awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(['init'])
# Prepare waveforms and output them
awg_wfm.prepare_initial()
awg_wfm.prepare_final()
# Set output channel to true
awg_wfm.get_output_channel(0).Output = True
awg_wfm.get_output_channel(1).Output = True
#
lab.PROC('fpga_dsp').reset_pipeline()
lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[330e6],[]]))
lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
lab.PROC('fpga_dsp').add_stage(FPGA_FFT())
acq_module.set_data_processor(lab.PROC('fpga_dsp'))
acq_module.NumSamples = 10080
leData = acq_module.get_data()
#
fig, ax = plt.subplots(nrows=2)
for r in range(acq_module.NumRepetitions) :
    for s in range(acq_module.NumSegments) :
        freqs = np.linspace(0, acq_module.SampleRate/10, 1024,endpoint=False)[:int(acq_module.NumSamples/10)]
        ax[0].plot(freqs, np.abs(leData['data']['fft_real'][r][s] + 1j*leData['data']['fft_imag'][r][s]))
        ax[1].plot(leData['data']['debug_time_I'][r][s])
        ax[1].plot(leData['data']['debug_time_Q'][r][s])
#
lab.WFMT("OscMod").IQFrequency = 100e6

# plt.show()

#################
#AVERAGING TESTS#
#################
acq_module.NumSamples = 5040
acq_module.NumRepetitions = int(num_corners*3)
fig, ax = plt.subplots(1)
for s in range(4):
    pt_centre = 0.1*np.array([np.cos(2*np.pi/4*s), np.sin(2*np.pi/4*s)])

    add_segments_circle(awg_wfm, pt_centre, num_corners, poly_size)
    # Prepare waveforms and output them
    awg_wfm.prepare_initial()
    awg_wfm.prepare_final()
    # Set output channel to true
    awg_wfm.get_output_channel(0).Output = True
    awg_wfm.get_output_channel(1).Output = True

    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}, {'fLO':100e6, 'fc':10e6, 'Taps':40}]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))

    acq_module.set_data_processor(lab.PROC('fpga_dsp'))
    leData = acq_module.get_data()

    state_mkrs = ["o", ",", "d", "^", "s", "p", "h", "P"]
    headers = acq_module._instr_acq.get_header_data(1)
    headers = [state_mkrs[x['state1']] for x in headers]

    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}, {'fLO':100e6, 'fc':10e6, 'Taps':40}]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('repetition'))

    acq_module.set_data_processor(lab.PROC('fpga_dsp'))

    # acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:SEL DSP1')
    # acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:OUTP SVM')
    # acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:LINE 1,1,0')
    # acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:LINE 2,-1,0')
    # acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:LINE 3,0,0')

    leData2 = acq_module.get_data()

    plt.gca().set_prop_cycle(None)
    for sg in range(acq_module.NumSegments) :
        times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
        for c in range(num_corners):
            ax.scatter(leData['data']['CH1_0_I'][sg][c::num_corners], leData['data']['CH1_0_Q'][sg][c::num_corners], marker=str(s+1))
        for m in range(len(headers)):
            ax.scatter([leData['data']['CH1_0_I'][sg][m]], [leData['data']['CH1_0_Q'][sg][m]], c='black', alpha=0.1, marker=headers[m])
    ax.plot(leData2['data']['CH1_0_I']/acq_module.NumRepetitions, leData2['data']['CH1_0_Q']/acq_module.NumRepetitions, 'ko')
    ax.plot(leData2['data']['CH1_0_I']/acq_module.NumRepetitions, leData2['data']['CH1_0_Q']/acq_module.NumRepetitions, marker=str(s+1))
    x_vals = ax.get_xlim()
    ax.plot(x_vals, np.array(x_vals), 'k-')
    ax.plot(x_vals, -np.array(x_vals), 'k-')
ax.set_aspect('equal', 'box')


####################
#SVM DECISION TESTS#
####################
num_pts_axis = 10
acq_module.NumSamples = 5040
acq_module.NumRepetitions = int(num_pts_axis * num_pts_axis * 3)
fig, ax = plt.subplots(1)
#
awg_wfm.set_valid_total_time(499e-6)
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 96e-9, 0.25))
read_segs = []
#Form a grid in the IQ plane...
for x in np.linspace(-0.1,0.1, num_pts_axis):
    for y in np.linspace(-0.1,0.1, num_pts_axis):
        ampl, phs = np.sqrt(x**2+y**2), np.arctan2(y, x)
        awg_wfm.add_waveform_segment(WFS_Constant(f"pad{x}{y}", None, 512e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Constant(f"constel{x}{y}", lab.WFMT("OscMod").apply(phase=phs), 2048e-9, ampl))
        read_segs += [f"constel{x}{y}"]
awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))
awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(read_segs)
awg_wfm.prepare_initial()
awg_wfm.prepare_final()
awg_wfm.get_output_channel(0).Output = True
awg_wfm.get_output_channel(1).Output = True
#
lab.PROC('fpga_dsp').reset_pipeline()
lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}, {'fLO':100e6, 'fc':10e6, 'Taps':40}]]))
lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
#
# acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:SEL DSP1')
# acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:OUTP SVM')
# acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:LINE 1,1,0')
# acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:LINE 2,-1,0')
# acq_module._instr_acq._parent._send_cmd(':DSP:DEC:IQP:LINE 3,0,0')
acq_module.set_decision_block([DEC_SVM([(-1,1,0), (1,1,0), (0,1,0)]), None])
#
acq_module.set_data_processor(lab.PROC('fpga_dsp'))
leData = acq_module.get_data()
#
state_mkrs = ["o", ",", "d", "^", "s", "p", "h", "P"]
headers = acq_module._instr_acq.get_header_data(1)
headers = [state_mkrs[x['state1']] for x in headers]
#
plt.gca().set_prop_cycle(None)
for sg in range(acq_module.NumSegments) :
    times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
    # for c in range(num_corners):
    #     ax.scatter(leData['data']['CH1_0_I'][sg][c::num_corners], leData['data']['CH1_0_Q'][sg][c::num_corners], marker=str(s+1))
    for m in range(len(headers)):
        ax.scatter([leData['data']['CH1_0_I'][sg][m]], [leData['data']['CH1_0_Q'][sg][m]], c='black', alpha=0.1, marker=headers[m])
x_vals = ax.get_xlim()
ax.plot(x_vals, np.array(x_vals), 'k-')
ax.plot(x_vals, -np.array(x_vals), 'k-')
ax.plot(x_vals, 0*np.array(x_vals), 'k-')
ax.set_aspect('equal', 'box')

plt.show()
awg_wfm.get_output_channel(0).Output = False
awg_wfm.get_output_channel(1).Output = False
input('Press ENTER to finish test.')

