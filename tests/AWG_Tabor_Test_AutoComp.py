from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformModulations import*
import numpy as np
from sqdtoolz.Parameter import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\TaborTest.yaml", save_dir = "mySaves\\")

#Can be done in YAML
# instr_ddg = DDG_DG645('ddg_real')
# new_exp.add_instrument(instr_ddg)

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
ddg_module = DDG(new_lab.station.load_pulser())
ddg_module.get_trigger_output('AB').TrigPulseLength = 500e-9
ddg_module.get_trigger_output('AB').TrigPolarity = 1
ddg_module.get_trigger_output('AB').TrigPulseDelay = 0e-9
ddg_module.get_trigger_output('CD').TrigPulseLength = 100e-9
ddg_module.get_trigger_output('CD').TrigPulseDelay = 50e-9
ddg_module.get_trigger_output('CD').TrigPolarity = 1
ddg_module.get_trigger_output('EF').TrigPulseLength = 50e-9
ddg_module.get_trigger_output('EF').TrigPulseDelay = 10e-9
ddg_module.get_trigger_output('EF').TrigPolarity = 0
# awg.set_trigger_source(ddg_module.get_trigger_source('A'))

new_lab.station.load_pulser().trigger_rate(300e3)

inst_tabor = new_lab.station.load_TaborAWG()

mod_freq_qubit = WM_SinusoidalIQ("QubitFreqMod", 10e6)

awg_wfm_q = WaveformAWG("Waveform 2 CH", [(inst_tabor.AWG, 'CH1'),(inst_tabor.AWG, 'CH2')], 1e9)
read_segs = []
for m in range(4):
    awg_wfm_q.add_waveform_segment(WFS_Gaussian(f"init{m}", mod_freq_qubit, 512e-9, 0.5-0.1*m))
    awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero1{m}", None, 512e-9, 0.01*m))
    awg_wfm_q.add_waveform_segment(WFS_Gaussian(f"init2{m}", mod_freq_qubit, 512e-9, 0.5-0.1*m))
    awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero2{m}", None, 576e-9, 0.0))
    read_segs += [f"init{m}"]
# awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(["init0","init2"])
awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(read_segs)
awg_wfm_q.AutoCompression = 'Basic'
awg_wfm_q.program_AWG()

awg_wfm_q.get_output_channel(0).Output = True
awg_wfm_q.get_output_channel(1).Output = True
inst_tabor.AWG._get_channel_output('CH1').marker1_output(True)
inst_tabor.AWG._get_channel_output('CH1').marker2_output(True)

# my_param1 = VariableInstrument("len1", awg_wfm2, 'IQFrequency')
# my_param2 = VariableInstrument("len2", awg_wfm2, 'IQPhase')

# tc = TimingConfiguration(1.2e-6, [ddg_module], [awg_wfm2], None)
# lePlot = tc.plot().show()
# leData = new_exp.run(tc, [(my_param1, np.linspace(20e6,35e6,10)),(my_param2, np.linspace(0,3,3))])

inst_tabor.ACQ.TriggerInputEdge = 1
acq_module = ACQ(inst_tabor.ACQ)
acq_module.NumSamples = 2400
acq_module.NumSegments = 2
acq_module.NumRepetitions = 2
leData = inst_tabor.ACQ.get_data()
import matplotlib.pyplot as plt
for r in range(2):
    for s in range(2):
        plt.plot(leData[0][r][s])
plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
input('press <ENTER> to continue')

awg_wfm_A = WaveformAWG("Waveform 2 CH", [(inst_tabor.AWG, 'CH1')], 1e9)
awg_wfm_A.add_waveform_segment(WFS_Gaussian("init", None, 512e-9, 0.5))
awg_wfm_A.add_waveform_segment(WFS_Constant("zero1", None, 512e-9, 0.25))
awg_wfm_A.add_waveform_segment(WFS_Gaussian("init2", None, 512e-9, 0.5))
awg_wfm_A.add_waveform_segment(WFS_Constant("zero2", None, 512e-9, 0.0))
awg_wfm_A.get_output_channel(0).marker(0).set_markers_to_segments(["init","init2"])
awg_wfm_A.get_output_channel(0).marker(1).set_markers_to_segments(["zero1","zero2"])
awg_wfm_A.program_AWG()

awg_wfm_B = WaveformAWG("Waveform 2 CH", [(inst_tabor.AWG, 'CH1')], 1e9)
awg_wfm_B.add_waveform_segment(WFS_Gaussian("init", None, 512e-9, -0.5))
awg_wfm_B.add_waveform_segment(WFS_Constant("zero1", None, 512e-9, 0.25))
awg_wfm_B.add_waveform_segment(WFS_Gaussian("init2", None, 512e-9, -0.5))
awg_wfm_B.add_waveform_segment(WFS_Constant("zero2", None, 512e-9, 0.0))
awg_wfm_B.get_output_channel(0).marker(0).set_markers_to_segments(["init","init2"])
awg_wfm_B.get_output_channel(0).marker(1).set_markers_to_segments(["zero1","zero2"])
awg_wfm_B.program_AWG()

inst_tabor.AWG._get_channel_output('CH1').Output = True
inst_tabor.AWG._get_channel_output('CH2').Output = True
inst_tabor.AWG._get_channel_output('CH1').marker1_output(True)


input('press <ENTER> to continue')