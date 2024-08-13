from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.GENmwSrcAWG import GENmwSrcAWG
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
#   - First column should show sine-waves that are growing in 2-3 steps in amplitude
#   - Second column should show sine-waves that are nothing, then beating, and finally pure


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
awg_wfm = WaveformAWG("Waveform", lab,  [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH3')], 2.0e9, 4.9e-6)

genmwawg = GENmwSrcAWG('MWAWG', lab, (['TaborAWG', 'AWG'], 'CH2'), 2, 2.0e9, 4e-6)

acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
acq_module.NumSegments = 1
acq_module.SampleRate = 2.5e9
acq_module.ChannelStates = (True, True)

acq_module._instr_acq._parent._debug = False

ProcessorFPGA('fpga_dsp', lab)
lab.PROC('fpga_dsp').reset_pipeline()
lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[105e6],[105e6]]))
lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 10))
acq_module.set_data_processor(lab.PROC('fpga_dsp'))

acq_module.NumSamples = 5040
acq_module.NumRepetitions = 30
awg_wfm.set_valid_total_time(4.9e-6)
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant(f"init", lab.WFMT("OscMod").apply(phase=0), 2048e-9, 0.2))
awg_wfm.add_waveform_segment(WFS_Constant(f"init2", lab.WFMT("OscMod").apply(phase=0), 1024e-9, 0.25))
awg_wfm.add_waveform_segment(WFS_Constant(f"init3", lab.WFMT("OscMod").apply(phase=0), 1024e-9, 0.3))
awg_wfm.add_waveform_segment(WFS_Constant(f"pad", None, -1, 0.0))
# Setup trigger 
awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(['init'])
awg_wfm.get_output_channel(0).marker(2).set_markers_to_segments(['init2'])
awg_wfm.get_output_channel(0).reset_software_triggers(2)
awg_wfm.get_output_channel(0).software_trigger(0).set_markers_to_segments(['init2'])
awg_wfm.get_output_channel(0).software_trigger(1).set_markers_to_segments(['init2', 'init3'])
awg_wfm.set_trigger_source_all(lab.HAL('DDG').get_trigger_output('AB'))

genmwawg.get_rf_channel(0).Power = -10
genmwawg.get_rf_channel(1).Power = -10
genmwawg.get_rf_channel(0).Frequency = 96e6
genmwawg.get_rf_channel(1).Frequency = 102e6
genmwawg.get_rf_channel(0).set_trigger_source(awg_wfm.get_output_channel(0).software_trigger(0))
genmwawg.get_rf_channel(1).set_trigger_source(awg_wfm.get_output_channel(0).software_trigger(1))

ExperimentConfiguration('test', lab, 5e-6, ['DDG', 'Waveform', 'MWAWG'], 'TaborACQ')
exp = Experiment('test', lab.CONFIG('test'))
leData = lab.run_single(exp)

arr = leData.get_numpy_array()

fig, ax = plt.subplots(2,2)
for r in range(acq_module.NumRepetitions) :
    times = np.arange(acq_module.NumSamples/10)/(acq_module.SampleRate/10) * 1e9
    ax[0,0].plot(times, arr[r,:,0])
    ax[1,0].plot(times, arr[r,:,1])
    ax[0,1].plot(times, arr[r,:,2])
    ax[1,1].plot(times, arr[r,:,3])
plt.show()

a=0




