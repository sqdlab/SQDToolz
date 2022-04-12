from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*
import numpy as np
from sqdtoolz.Variable import*
from sqdtoolz.Laboratory import*

from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*

new_lab = Laboratory(instr_config_file = "tests\\TaborTest.yaml", save_dir = "mySaves\\")

#Can be done in YAML
# instr_ddg = DDG_DG645('ddg_real')
# new_exp.add_instrument(instr_ddg)

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
# ddg_module = DDG(new_lab._station.load_pulser())
# ddg_module.get_trigger_output('AB').TrigPulseLength = 500e-9
# ddg_module.get_trigger_output('AB').TrigPolarity = 1
# ddg_module.get_trigger_output('AB').TrigPulseDelay = 0e-9
# ddg_module.get_trigger_output('CD').TrigPulseLength = 100e-9
# ddg_module.get_trigger_output('CD').TrigPulseDelay = 50e-9
# ddg_module.get_trigger_output('CD').TrigPolarity = 1
# ddg_module.get_trigger_output('EF').TrigPulseLength = 50e-9
# ddg_module.get_trigger_output('EF').TrigPulseDelay = 10e-9
# ddg_module.get_trigger_output('EF').TrigPolarity = 0
# awg.set_trigger_source(ddg_module.get_trigger_source('A'))
# new_lab._station.load_pulser().trigger_rate(300e3)

new_lab.load_instrument('TaborAWG')

# WFMT_ModulationIQ("QubitFreqMod", new_lab, 100e6)

# # awg_wfm_q = WaveformAWG("Waveform 2 CH", new_lab, [(['TaborAWG', 'AWG'], 'CH1'),(['TaborAWG', 'AWG'], 'CH2')], 2e9)
# # read_segs = []
# # for m in range(4):
# #     awg_wfm_q.add_waveform_segment(WFS_Constant(f"init{m}", new_lab.WFMT('QubitFreqMod').apply(), 512e-9-384e-9, 0.5-0.1*m))#WFS_Gaussian
# #     awg_wfm_q.add_waveform_segment(WFS_Cosine(f"zero1{m}", None, 512e-9+384e-9, 0.05, 200e6))
# #     awg_wfm_q.add_waveform_segment(WFS_Constant(f"init2{m}", new_lab.WFMT('QubitFreqMod').apply(), 512e-9, 0.0*(0.5-0.1*m)))
# #     awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero2{m}", None, 576e-9, 0.0))
# #     read_segs += [f"init{m}"]

# awg_wfm_q = WaveformAWG("CosSrc", new_lab, [(['TaborAWG', 'AWG'], 'CH1'),(['TaborAWG', 'AWG'], 'CH2')], 1e9, total_time=1024e-9)
# read_segs = []
# new_lab.HAL('CosSrc').add_waveform_segment(WFS_Cosine("LO1", None, 100e-9, 0.5, 100e6))
# new_lab.HAL('CosSrc').add_waveform_segment(WFS_Cosine("LO2", None, 100e-9, 0.05, 200e6))
# new_lab.HAL('CosSrc').add_waveform_segment(WFS_Cosine("LO3", None, 100e-9, 0.05, 300e6))
# new_lab.HAL('CosSrc').add_waveform_segment(WFS_Constant("True Pad", None, -1, 0.00))

# new_lab.HAL('CosSrc').get_output_channel(0).marker(0).set_markers_to_segments(['LO1'])
# new_lab.HAL('CosSrc').get_output_channel(0).marker(1).set_markers_to_segments(['LO1'])
# new_lab.HAL('CosSrc').get_output_channel(1).marker(0).set_markers_to_segments(['LO2'])
# new_lab.HAL('CosSrc').get_output_channel(1).marker(1).set_markers_to_segments(['LO3'])

# # awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(["init0","init2"])
# # awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(read_segs)
# awg_wfm_q.prepare_initial()
# awg_wfm_q.prepare_final()

# awg_wfm_q.get_output_channel(0).Output = True
# awg_wfm_q.get_output_channel(1).Output = True
# # inst_tabor.AWG._get_channel_output('CH1').marker1_output(True)
# # inst_tabor.AWG._get_channel_output('CH1').marker2_output(True)

# # my_param1 = VariableInstrument("len1", awg_wfm2, 'IQFrequency')
# # my_param2 = VariableInstrument("len2", awg_wfm2, 'IQPhase')

# # tc = TimingConfiguration(1.2e-6, [ddg_module], [awg_wfm2], None)
# # lePlot = tc.plot().show()
# # leData = new_exp.run(tc, [(my_param1, np.linspace(20e6,35e6,10)),(my_param2, np.linspace(0,3,3))])


# #Connected M1 to TRIG1 and AWG-CH1 to ADC-CH1

# GENvoltSource('CH1offset', new_lab, ['TaborAWG', 'AWG', 'CH1'])

# instr = new_lab._get_instrument('TaborAWG')


# instr._set_cmd(':DIG:MODE', 'DUAL')
# instr._set_cmd(':DIG:FREQ', 2500e6)
# instr._set_cmd(':DIG:CHAN', 'CH1')
# instr._set_cmd(':DIG:DDC:MODE', 'COMPlex')
# instr._set_cmd(':DIG:CHAN', 'CH2')
# instr._set_cmd(':DIG:DDC:MODE', 'COMPlex')
# instr._set_cmd(':DIG:DDC:CFR1', 100e6)
# instr._set_cmd(':DIG:DDC:CFR2', 100e6)
# instr._chk_err("")

# instr._set_cmd(':DSP:STOR1', 'DIRECT1')
# instr._set_cmd(':DSP:STOR2', 'DIRECT2')

# instr._set_cmd(':DSP:STOR1', 'DSP1')





# #Set DSP Path 1 to IQ
# instr._set_cmd(':DSP:DEC:IQP:SEL', 1)
# instr._chk_err("")
# # instr._set_cmd(':DSP:DEC:IQP:INP', 'IQ')
# instr._set_cmd(':DSP:DEC:IQP:INP', 'AMPH')
# instr._chk_err("")

# instr._set_cmd(':DSP:DEC:FRAM', 240)
# instr._chk_err("")
# instr._set_cmd(':DSP:DEC:IQP:OUTP', 'THR')
# instr._chk_err("")

# #Try some MATH operations
# instr._set_cmd(':DSP:MATH:OPERation', 'I1, -2, 10')   #Scale Offset
# instr._set_cmd(':DSP:MATH:OPERation', 'Q1, 1, 0')
# instr._chk_err("")

acq_module = ACQ("TabourACQ", new_lab, ['TaborAWG', 'ACQ'])
acq_module.NumSamples = 480
acq_module.NumSegments = 2
acq_module.NumRepetitions = 2

myProc = ProcessorCPU("DDC", new_lab)
myProc.add_stage(CPU_DDC([100e6]*2))
myProc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 10e6, 'Win' : 'hamming'}]*4))
# acq_module.set_data_processor(myProc)

leData = acq_module.get_data()
# leDecisions = instr.ACQ.get_frame_data()

import matplotlib.pyplot as plt
for r in range(2):
    for s in range(2):
        data = leData['data']['ch1'][r][s][1::2]    #I
        plt.plot(data)
        data = leData['data']['ch1'][r][s][0::2]    #Q
        plt.plot(data)
plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
input('press <ENTER> to continue')


#Inspect in Debug Console:
#np.sum((leData['data']['ch1'][1][1][1::2]-16384.0)*-2.0+10) for I
#np.sum((leData['data']['ch1'][1][0][::2]-16384.0)*1.0+0) for Q
#np.sum(np.sqrt( ((leData['data']['ch1'][1][0][1::2]-16384.0)*-2.0+10)**2 + ((leData['data']['ch1'][1][0][::2]-16384.0)*1.0+0)**2 )) for Amplitude

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