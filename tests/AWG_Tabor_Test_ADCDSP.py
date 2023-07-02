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
awg_wfm = WaveformAWG("Waveform", lab,  [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH2')], 2e9)

# Add Segments
awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(), 2048e-9-384e-9, 0.25))
awg_wfm.add_waveform_segment(WFS_Constant(f"zero1", None, 2048e-9+384e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Constant(f"init2", lab.WFMT("OscMod").apply(), 2048e-9-384e-9, 0.125))
awg_wfm.add_waveform_segment(WFS_Constant(f"zero12", None, 2048e-9+384e-9, 0.0))
awg_wfm.add_waveform_segment(WFS_Constant(f"zero22", None, 576e-9, 0.0))

# Setup trigger 
awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(["init", "init2"])


acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
acq_module.NumSamples = 5184    #(72*72)
acq_module.NumSegments = 1
acq_module.NumRepetitions = 6
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

leData = acq_module.get_data()
leFrames = acq_module._instr_acq.get_frame_data(1)
leFrames2 = acq_module._instr_acq.get_frame_data(2)

import matplotlib.pyplot as plt
# for r in range(acq_module.NumRepetitions) :
#     for s in range(acq_module.NumSegments) :
#         times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
#         plt.plot(times[::12], leData['data']['CH1'][r][s][::12])
#         plt.plot(times[::12], leData['data']['CH1'][r][s][1::12])

fig, ax = plt.subplots(nrows=2)
for r in range(acq_module.NumRepetitions) :
    for s in range(acq_module.NumSegments) :
        times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
        ax[0].plot(leData['data']['CH1'][r][s][1::12])
        ax[1].plot(leData['data']['CH1'][r][s][0::12])

exp_decs = [((leData['data']['CH1'][x][0][1::12]-2**15)*0.5).sum()+1j*((leData['data']['CH1'][x][0][0::12]-2**15)*0.5).sum() for x in range(acq_module.NumRepetitions)]
act_decs = [x.real1_dec+1j*x.im1_dec for x in leFrames]

plt.show()
awg_wfm.get_output_channel(0).Output = False
input('Press ENTER to finish test.')

