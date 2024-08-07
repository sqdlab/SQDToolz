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
import os

#Wiring requirements:
#   AWG CH1 to ADC CH1
#   AWG CH2 to ADC CH2
#   DDG AB to AWG TRIG1
#
#The outputs should contain:
#   - Overlapping sine waves - i.e. raw samples and averaged samples
#   - FFT should show ~70MHz (i.e. 400MHz input with 330MHz demodulation)
#   - Stars with black centres denoting averages.

# Create New Laboratory Class

if os.path.exists('AWG_Tabor_Test_ADCDSP.yaml'):
    yaml_file = 'AWG_Tabor_Test_ADCDSP.yaml'
    plot_stuff = False
else:
    yaml_file = 'tests/AWG_Tabor_Test_ADCDSP.yaml'
    plot_stuff = True
lab = Laboratory(instr_config_file = yaml_file, save_dir = "mySaves\\")

# Load the Tabor into the lab class to use
lab.load_instrument('TaborAWG')

lab.load_instrument('pulser')
DDG('DDG', lab, 'pulser')
lab.HAL("DDG").RepetitionTime = 5e-6
lab.HAL('DDG').get_trigger_output('AB').TrigPulseLength = 50e-9
lab.HAL('DDG').get_trigger_output('AB').TrigPolarity = 1
lab.HAL('DDG').get_trigger_output('AB').TrigPulseDelay = 0
lab.HAL('DDG').get_trigger_output('AB').TrigEnable = True 

WFMT_ModulationIQ("OscMod", lab, 100e6)
lab.WFMT("OscMod").IQUpperSideband = False

pt_centre = np.array([0,0])
num_corners = 12
poly_size = 0.05

# Setup waveforms
awg_wfm = WaveformAWG("Waveform", lab,  [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH2')], 2.0e9, 40e-6)

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


acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
acq_module.NumSegments = 1
acq_module.SampleRate = 2.5e9
acq_module.ChannelStates = (True, True)

acq_module._instr_acq._parent._debug = True

ProcessorFPGA('fpga_dsp', lab)

def dump_now():
    f = open("DUMP.txt", "w")
    f.write(acq_module._instr_acq._parent._debug_logs)
    f.close()




def test_basic_time_traces(lab, skip_normal=False):
    awg_wfm = lab.HAL('Waveform')
    acq_module = lab.HAL('TaborACQ')

    acq_module.NumSamples = 5040    #(72*70)
    acq_module.NumRepetitions = int(num_corners*3)

    filt_coeffs = scipy.signal.firwin(51, 10e6, fs=lab._get_instrument('TaborAWG').ACQ.sample_rate())
    # acq_module._instr_acq.setup_data_path(ddc_mode = "REAL", ddr_store = "DIR")

    acq_module.NumRepetitions = 30
    awg_wfm.clear_segments()
    awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 2048e-9, 0.25))
    awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))
    # Setup trigger 
    awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(['init'])
    awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(['init'])
    # Prepare waveforms and output them
    awg_wfm.prepare_initial()
    awg_wfm.prepare_final()
    # Set output channel to true
    awg_wfm.get_output_channel(0).Output = True
    awg_wfm.get_output_channel(1).Output = True
    #
    fig, ax = plt.subplots(nrows=2, ncols=2)
    if not skip_normal:
        # lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}, {'fLO':105e6, 'fc':10e6, 'Taps':40}]]))
        lab.PROC('fpga_dsp').reset_pipeline()
        lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[105e6],[105e6]]))
        lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
        acq_module.set_data_processor(lab.PROC('fpga_dsp'))
        leData = acq_module.get_data()['data']
        #
        for r in range(acq_module.NumRepetitions) :
            times = np.arange(acq_module.NumSamples/10)/(acq_module.SampleRate/10) * 1e9
            ax[0,0].plot(times, leData['data']['CH1_0_I'][r])
            ax[1,0].plot(times, leData['data']['CH1_0_Q'][r])
            ax[0,1].plot(times, leData['data']['CH2_0_I'][r])
            ax[1,1].plot(times, leData['data']['CH2_0_Q'][r])
            # ax[0].plot(leData['data']['CH1_1_I'][r][s])
            # ax[1].plot(leData['data']['CH1_1_Q'][r][s])
    #
    dump_now()
    #
    acq_module.NumSamples = 5100
    lab.PROC('fpga_dsp').reset_pipeline()
    lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[105e6],[105e6]]))
    lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
    lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('repetition'))
    acq_module.set_data_processor(lab.PROC('fpga_dsp'))
    leData2 = acq_module.get_data()['data']
    #
    times = np.arange(acq_module.NumSamples/10)/(acq_module.SampleRate/10) * 1e9
    ax[0,0].plot(times, leData2['data']['CH1_0_I']/acq_module.NumRepetitions, 'r-')
    ax[1,0].plot(times, leData2['data']['CH1_0_Q']/acq_module.NumRepetitions, 'r-')
    ax[0,1].plot(times, leData2['data']['CH2_0_I']/acq_module.NumRepetitions, 'r-')
    ax[1,1].plot(times, leData2['data']['CH2_0_Q']/acq_module.NumRepetitions, 'r-')

def test_FFT(lab):
    awg_wfm = lab.HAL('Waveform')
    acq_module = lab.HAL('TaborACQ')

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
    leData = acq_module.get_data()['data']
    #
    fig, ax = plt.subplots(nrows=2)
    for r in range(acq_module.NumRepetitions) :
        freqs = np.linspace(0, acq_module.SampleRate/10, 1024,endpoint=False)[:int(acq_module.NumSamples/10)]
        ax[0].plot(freqs, np.abs(leData['data']['fft_real'][r] + 1j*leData['data']['fft_imag'][r]))
        ax[1].plot(leData['data']['debug_time_I'][r])
        ax[1].plot(leData['data']['debug_time_Q'][r])
    #
    lab.WFMT("OscMod").IQFrequency = 100e6


def test_averaging(lab, num_points_per_corner=3, num_corners=12, dual=True):
    awg_wfm = lab.HAL('Waveform')
    acq_module = lab.HAL('TaborACQ')

    acq_module.NumSamples = 5040
    acq_module.NumRepetitions = int(num_corners*num_points_per_corner)
    if dual:
        fig, ax = plt.subplots(ncols=2)
    else:
        fig, ax = plt.subplots(1)
    cols = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for s in range(4):
        pt_ampl = 0.1
        if s == 0:
            pt_ampl = 0.2
        pt_centre = pt_ampl*np.array([np.cos(2*np.pi/4*s), np.sin(2*np.pi/4*s)])

        add_segments_circle(awg_wfm, pt_centre, num_corners, poly_size)
        # Prepare waveforms and output them
        awg_wfm.prepare_initial()
        awg_wfm.prepare_final()
        # Set output channel to true
        awg_wfm.get_output_channel(0).Output = True
        awg_wfm.get_output_channel(1).Output = True

        lab.PROC('fpga_dsp').reset_pipeline()
        lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}], [{'fLO':100e6, 'fc':10e6, 'Taps':40}]]))
        lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
        lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))

        acq_module.set_data_processor(lab.PROC('fpga_dsp'))
        leData = acq_module.get_data()['data']

        lab.PROC('fpga_dsp').reset_pipeline()
        lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}], [{'fLO':100e6, 'fc':10e6, 'Taps':40}]]))
        lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
        lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
        lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('repetition'))

        acq_module.set_data_processor(lab.PROC('fpga_dsp'))
        leData2 = acq_module.get_data()['data']

        for c in range(num_corners):
            if dual:
                ax[0].scatter(leData['data']['CH1_0_I'][c::num_corners], leData['data']['CH1_0_Q'][c::num_corners], marker=str(s+1), color=cols[c%len(cols)])
                ax[1].scatter(leData['data']['CH2_0_I'][c::num_corners], leData['data']['CH2_0_Q'][c::num_corners], marker=str(s+1), color=cols[c%len(cols)])
            else:
                ax.scatter(leData['data']['CH1_0_I'][c::num_corners], leData['data']['CH1_0_Q'][c::num_corners], marker=str(s+1), color=cols[c%len(cols)])
        if dual:
            ax[0].plot(leData2['data']['CH1_0_I']/acq_module.NumRepetitions, leData2['data']['CH1_0_Q']/acq_module.NumRepetitions, 'ko')
            ax[0].plot(leData2['data']['CH1_0_I']/acq_module.NumRepetitions, leData2['data']['CH1_0_Q']/acq_module.NumRepetitions, marker=str(s+1), color='white')
            ax[1].plot(leData2['data']['CH2_0_I']/acq_module.NumRepetitions, leData2['data']['CH2_0_Q']/acq_module.NumRepetitions, 'ko')
            ax[1].plot(leData2['data']['CH2_0_I']/acq_module.NumRepetitions, leData2['data']['CH2_0_Q']/acq_module.NumRepetitions, marker=str(s+1), color='white')
            for m in range(2):
                x_vals = ax[m].get_xlim()
                ax[m].plot(x_vals, np.array(x_vals), 'k-')
                ax[m].plot(x_vals, -np.array(x_vals), 'k-')
        else:
            ax.plot(leData2['data']['CH1_0_I']/acq_module.NumRepetitions, leData2['data']['CH1_0_Q']/acq_module.NumRepetitions, 'ko')
            ax.plot(leData2['data']['CH1_0_I']/acq_module.NumRepetitions, leData2['data']['CH1_0_Q']/acq_module.NumRepetitions, marker=str(s+1), color='white')
            x_vals = ax.get_xlim()
            ax.plot(x_vals, np.array(x_vals), 'k-')
            ax.plot(x_vals, -np.array(x_vals), 'k-')
    if dual:
        ax[0].set_aspect('equal', 'box')
        ax[1].set_aspect('equal', 'box')
    else:
        ax.set_aspect('equal', 'box')


def test_SVM(lab):
    awg_wfm = lab.HAL('Waveform')
    acq_module = lab.HAL('TaborACQ')

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
    rawData = acq_module.get_data()
    leData = rawData['data']
    #
    state_mkrs = ["o", ",", "d", "^", "s", "p", "h", "P"]
    headers = rawData['decisions']
    headers = [state_mkrs[x] for x in headers['data']['state1']]
    #
    plt.gca().set_prop_cycle(None)
    times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
    # for c in range(num_corners):
    #     ax.scatter(leData['data']['CH1_0_I'][sg][c::num_corners], leData['data']['CH1_0_Q'][sg][c::num_corners], marker=str(s+1))
    for m in range(len(headers)):
        ax.scatter([leData['data']['CH1_0_I'][m]], [leData['data']['CH1_0_Q'][m]], c='black', alpha=0.1, marker=headers[m])
    x_vals = ax.get_xlim()
    ax.plot(x_vals, np.array(x_vals), 'k-')
    ax.plot(x_vals, -np.array(x_vals), 'k-')
    ax.plot(x_vals, 0*np.array(x_vals), 'k-')
    ax.set_aspect('equal', 'box')

    ExperimentConfiguration("test", lab, 1e-3, ['Waveform'], 'TaborACQ')
    exp = Experiment('test', lab.CONFIG('test'))
    leData = lab.run_single(exp)

def benchmark_sample_integration(lab, num_points_per_corner=3, num_corners=12, dual=True):
    awg_wfm = lab.HAL('Waveform')
    acq_module = lab.HAL('TaborACQ')

    acq_module.NumSamples = 5040
    acq_module.NumRepetitions = 8192*2

    cur_time = time.time()
    if dual:
        fig, ax = plt.subplots(ncols=2)
    else:
        fig, ax = plt.subplots(1)
    cols = plt.rcParams['axes.prop_cycle'].by_key()['color']
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
        lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}], [{'fLO':100e6, 'fc':10e6, 'Taps':40}]]))
        lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
        # lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
        acq_module.set_data_processor(lab.PROC('fpga_dsp'))

        ProcessorCPU('cpu_dsp', lab)
        lab.PROC('cpu_dsp').reset_pipeline()
        lab.PROC('cpu_dsp').add_stage(CPU_Integrate('sample'))
        acq_module.set_extra_post_processors([lab.PROC('cpu_dsp')])

        leData = acq_module.get_data()['data']
        a=0

    cur_time = time.time() - cur_time
    print(f'Expected Time: {lab.HAL("DDG").RepetitionTime * lab.HAL("TaborACQ").NumRepetitions * 4}s')
    print(f'Actual Time: {cur_time}s')

# test_basic_time_traces(lab, skip_normal=False)
# test_FFT(lab)
# test_averaging(lab, num_points_per_corner=3)

# vprof -c p  test.py --port 8001 
benchmark_sample_integration(lab)

if plot_stuff:
    plt.show()
    awg_wfm.get_output_channel(0).Output = False
    awg_wfm.get_output_channel(1).Output = False
    input('Press ENTER to finish test.')

