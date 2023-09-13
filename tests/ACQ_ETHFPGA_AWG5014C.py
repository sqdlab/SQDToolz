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
# - 

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

# # Prepare waveforms and output them
# lab.HAL("WfmConRes").prepare_initial()
# lab.HAL("WfmConRes").prepare_final()
# # Set output channel to true
# lab.HAL("WfmConRes").get_output_channel(0).Output = True
# lab.HAL("WfmConRes").get_output_channel(1).Output = True

lab.HAL("DDG").RepetitionTime = 500e-6#1.1e-3 1e-6

lab.HAL("ETHFPGA").set_acq_params(reps=6, segs=1, samples=4096)
lab.HAL("ETHFPGA").ChannelStates = (True, False)

ProcessorFPGA('fpga_dsp', lab)
lab.PROC('fpga_dsp').reset_pipeline()
lab.PROC('fpga_dsp').add_stage(FPGA_DDC([[25e6]]))
lab.PROC('fpga_dsp').add_stage(FPGA_FIR([[{'Type' : 'low', 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]))
lab.PROC('fpga_dsp').add_stage(FPGA_Decimation('sample', 4))

lab.HAL("ETHFPGA").set_data_processor(lab.PROC('fpga_dsp'))

ExperimentConfiguration('contMeas', lab, 8e-6, ['DDG', "WfmConRes"], 'ETHFPGA')
new_exp = Experiment('cav_exp', lab.CONFIG('contMeas'))
stz.VariableInternal('omg', lab)
cavSpecData = lab.run_single(new_exp, [(lab.VAR('omg'), np.arange(10))]) 
