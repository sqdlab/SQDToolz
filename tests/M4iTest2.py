
from sqdtoolz.Experiment import Experiment
from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.HAL.DDG import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Drivers.Agilent_N8241A import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.GENmwSource import*
import numpy as np
from sqdtoolz.Variable import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformModulations import*
from sqdtoolz.Variable import*
from sqdtoolz.HAL.Processors.ProcessorGPU import*
from sqdtoolz.HAL.Processors.GPU.GPU_DDC import*
from sqdtoolz.HAL.Processors.GPU.GPU_FIR import*

import matplotlib.pyplot as plt

new_lab = Laboratory(instr_config_file = "tests\\M4iTest.yaml", save_dir = "mySaves\\")

#Note the following:
# - Using a 1.25GHz clock source to split and driven into the EXT CLK IN inputs of both Agilent AWGs
# - SYNC CLK OUT on Master goes into SYNC CLK IN on Slave
# - Using M4 on master to trigger the slave AWG via Trigger 4 (could simply do this by just routing the clock lines to both AWGs...)
# - The DDG output triggers the first master AWG
# - Also using an external 10MHz reference on the AWG...

#Sample Clock
freq_module = GENmwSource(new_lab._station.load_SGS100A().get_output('RFOUT'))
freq_module.Output = True

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
instr_ddg = new_lab._station.load_pulser()
ddg_module = DDG(instr_ddg)
ddg_module.get_trigger_output('AB').TrigPulseLength = 750e-9
ddg_module.get_trigger_output('AB').TrigPolarity = 1
ddg_module.get_trigger_output('AB').TrigPulseDelay = 0e-9
instr_ddg.trigger_rate(100e3)

mod_freq_qubit = WM_SinusoidalIQ("QubitFreqMod", 100e6)

instr_Agi1 = new_lab._station.load_Agi1()
awg_wfm_q = WaveformAWG("Waveform 1", [(instr_Agi1, 'ch1'), (instr_Agi1, 'ch2')], 1.25e9)
read_segs = []
awg_wfm_q.add_waveform_segment(WFS_Constant("SEQPAD", None, 102.4e-9, 0.0))
for m in range(4):
    awg_wfm_q.add_waveform_segment(WFS_Gaussian(f"init{m}", mod_freq_qubit, 512e-9, 0.5-0.1*m))
    awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero1{m}", None, 512e-9, 0.1*m))
    awg_wfm_q.add_waveform_segment(WFS_Gaussian(f"init2{m}", None, 512e-9, 0.5-0.1*m))
    awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero2{m}", None, 512e-9, 0.0))
    read_segs += [f"init{m}"]
# awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(["init","init2"])
awg_wfm_q.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
awg_wfm_q.get_output_channel(1).marker(0).set_markers_to_segments(['SEQPAD', 'init0'])
awg_wfm_q.AutoCompression = 'None'#'Basic'

# awg_wfm_q.plot_waveforms(True).show()
# input('Press ENTER')

# awg_wfm_q2 = WaveformAWG("Waveform 2", [(instr_Agi1, 'ch2')], 1.25e9)
# read_segs = []
# awg_wfm_q2.add_waveform_segment(WFS_Constant("SEQPAD", None, 102.4e-9, 0.0))
# for m in range(4):
#     awg_wfm_q2.add_waveform_segment(WFS_Gaussian(f"init{m}", None, 512e-9, 0.5-0.1*m))
#     awg_wfm_q2.add_waveform_segment(WFS_Constant(f"zero1{m}", None, 512e-9, 0.1*m))
#     awg_wfm_q2.add_waveform_segment(WFS_Gaussian(f"init2{m}", None, 512e-9, 0.5-0.1*m))
#     awg_wfm_q2.add_waveform_segment(WFS_Constant(f"zero2{m}", None, 512e-9, 0.0))
#     read_segs += [f"init{m}"]

awg_wfm_q.prepare_initial()
# awg_wfm_q2.prepare_initial()
awg_wfm_q.prepare_final()
# awg_wfm_q2.prepare_final()
awg_wfm_q.get_output_channel(0).Output = True

#CONNECTED CHANNEL 1 of Agi1 to Input 0 of digitizer and MARKER 2 of Agi1 to Input Trg0 of digitizer
instr_digi = new_lab._station.load_M4iDigitizer()
acq_module = ACQ(instr_digi)
acq_module.NumSamples = 512
acq_module.NumSegments = 4
acq_module.NumRepetitions = 5
acq_module.SampleRate = 500e6
acq_module.TriggerEdge = 1
# acq_module.set_trigger_source(awg_wfm_q.get_output_channel(0).marker(1))

#expConfig = ExperimentConfiguration(10e-6, [ddg_module], [awg_wfm_q], acq_module, [freq_module])
expConfig = ExperimentConfiguration(10e-6, [ddg_module], [], acq_module, [freq_module])
# lePlot = expConfig.plot().show()
# input('press <ENTER> to continue')


leData = expConfig.get_data()
# leData2 = expConfig.get_data()
for r in range(5):#acq_module.NumRepetitions):
    for s in range(acq_module.NumSegments):
        arr = leData['data']['ch0'][r][s]+4000*r
        plt.plot(arr.tolist())
plt.show()
input('press <ENTER> to continue')

myProc = ProcessorGPU()
myProc.add_stage(GPU_DDC([100e6]))
myProc.add_stage(GPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 25e6, 'Win' : 'hamming'}]*2))
acq_module.set_data_processor(myProc)
leData = expConfig.get_data()
leData2 = expConfig.get_data()
import matplotlib.pyplot as plt
for r in range(acq_module.NumRepetitions):
    for s in range(acq_module.NumSegments):
        plt.plot(leData['data']['ch0_I'][r][s].astype(np.float32)+4000*r)
plt.show()
input('press <ENTER> to continue')

