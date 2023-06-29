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

# Setup trigger 
awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(["init"])


acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
acq_module.NumSamples = 4800
acq_module.NumSegments = 1
acq_module.NumRepetitions = 6
acq_module.SampleRate = 2.5e9
acq_module.ChannelStates = (True, True)

# Prepare waveforms and output them
awg_wfm.prepare_initial()
awg_wfm.prepare_final()

# Set output channel to true
awg_wfm.get_output_channel(0).Output = True
awg_wfm.get_output_channel(1).Output = True

instr = lab._get_instrument('TaborAWG')



leData = acq_module.get_data()
#leDecisions = instr.ACQ.get_frame_data()

import matplotlib.pyplot as plt
for r in range(acq_module.NumRepetitions) :
    for s in range(acq_module.NumSegments) :
        times = np.arange(acq_module.NumSamples)/acq_module.SampleRate * 1e9
        plt.plot(times, leData['data']['CH1'][r][s])
        plt.plot(times, leData['data']['CH2'][r][s])            
plt.show()
awg_wfm.get_output_channel(0).Output = False
input('Press ENTER to finish test.')

