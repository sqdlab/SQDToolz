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

import time
import unittest
import matplotlib.pyplot as plt

# Create New Laboratory Class
lab = Laboratory(instr_config_file = "tests\\AWG_Tabor_Test_ADCDSP.yaml", save_dir = "mySaves\\")

# Load the Tabor into the lab class to use
lab.load_instrument('TaborAWG')

print("Running AWG Driver Test 2")
# Waveform transformation
WFMT_ModulationIQ("OscMod", lab, 100e6)

# Setup waveforms
awg_wfm = WaveformAWG("Waveform", lab,  [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH2')], 2.0e9, 10e-6)

# Add Segments
awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(), 2048e-9-384e-9, 0.25))
awg_wfm.add_waveform_segment(WFS_Constant(f"zero1", None, 2048e-9+384e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
# awg_wfm.add_waveform_segment(WFS_Constant(f"init2", lab.WFMT("OscMod").apply(), 2048e-9-384e-9, 0.125))
# awg_wfm.add_waveform_segment(WFS_Constant(f"zero12", None, 2048e-9+384e-9, 0.0))
# awg_wfm.add_waveform_segment(WFS_Constant(f"zero22", None, 576e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))

# Setup trigger 
awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(["init"])


acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
acq_module.NumSamples = 5040    #(72*70)
acq_module.NumSegments = 1
acq_module.NumRepetitions = 10
acq_module.SampleRate = 2.5e9
acq_module.ChannelStates = (True, True)

filt_coeffs = scipy.signal.firwin(51, 10e6, fs=lab._get_instrument('TaborAWG').ACQ.sample_rate())
# acq_module._instr_acq.setup_data_path(ddc_mode = "REAL", ddr_store = "DIR")

# Prepare waveforms and output them
awg_wfm.prepare_initial()
awg_wfm.prepare_final()

# Set output channel to true
awg_wfm.get_output_channel(0).Output = True
awg_wfm.get_output_channel(1).Output = True

instr = lab._get_instrument('TaborAWG')

ProcessorFPGA('fpga_dsp', lab)
# lab.PROC('fpga_dsp').add_stage(FPGA_DDCFIR([[{'fLO':100e6, 'fc':10e6, 'Taps':40}, {'fLO':105e6, 'fc':10e6, 'Taps':40}]]))
lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[105e6],[100e6]]))
lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
# lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('sample'))
lab.PROC('fpga_dsp').add_stage(FPGA_Integrate('repetition'))

acq_module.set_data_processor(lab.PROC('fpga_dsp'))
leData = acq_module.get_data()

# import matplotlib.pyplot as plt
# for r in range(acq_module.NumRepetitions) :
#     for s in range(acq_module.NumSegments) :
#         times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
#         plt.plot(times, leData['data']['CH1'][r][s])
#         # plt.plot(times, leData['data']['CH1'][r][s])

# fig, ax = plt.subplots(nrows=2)
# for r in range(acq_module.NumRepetitions) :
#     for s in range(acq_module.NumSegments) :
#         times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
#         ax[0].plot(leData['data']['CH1_0_I'][r][s])
#         ax[1].plot(leData['data']['CH1_0_Q'][r][s])
#         # ax[0].plot(leData['data']['CH1_1_I'][r][s])
#         # ax[1].plot(leData['data']['CH1_1_Q'][r][s])
#         ax[0].plot(leData['data']['CH2_0_I'][r][s])
#         ax[1].plot(leData['data']['CH2_0_Q'][r][s])

fig, ax = plt.subplots(nrows=2)
for s in range(acq_module.NumSegments) :
    times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
    ax[0].plot(leData['data']['CH1_0_I'][s])
    ax[1].plot(leData['data']['CH1_0_Q'][s])
    # ax[0].plot(leData['data']['CH1_1_I'][s])
    # ax[1].plot(leData['data']['CH1_1_Q'][s])
    ax[0].plot(leData['data']['CH2_0_I'][s])
    ax[1].plot(leData['data']['CH2_0_Q'][s])

# fig, ax = plt.subplots(nrows=2)
# for r in range(acq_module.NumRepetitions) :
#     for s in range(acq_module.NumSegments) :
#         times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
#         ax[0].plot(leData['data']['CH1'][r][s][::2]/9000)
#         ax[1].plot(leData['data']['CH1'][r][s][1::2]/9000)
#         ax[0].plot(leData['data']['CH2'][r][s][::2]/9000)
#         ax[1].plot(leData['data']['CH2'][r][s][1::2]/9000)
#         # ax[2].plot(np.abs(leData['data']['CH1'][r][s][::2]/9000+1j*leData['data']['CH1'][r][s][1::2]/9000))
#         # ax[2].plot(np.abs(leData['data']['CH2'][r][s][::2]/9000+1j*leData['data']['CH2'][r][s][1::2]/9000))

# exp_decs = [((leData['data']['CH1'][x][0][1::12]-2**15)*0.5).sum()+1j*((leData['data']['CH1'][x][0][0::12]-2**15)*0.5).sum() for x in range(acq_module.NumRepetitions)]
# act_decs = [x.real1_dec+1j*x.im1_dec for x in leFrames]

plt.show()
awg_wfm.get_output_channel(0).Output = False
input('Press ENTER to finish test.')

