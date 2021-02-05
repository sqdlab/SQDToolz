from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.TimingConfiguration import*
from sqdtoolz.Drivers.Agilent_N8241A import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.ACQ import*
import numpy as np
from sqdtoolz.Parameter import*

new_exp = Experiment(instr_config_file = "tests\\BenchTest.yaml", save_dir = "", name="test")

awg_agilent1 = Agilent_N8241A('awg_agilent1', ivi_dll=r'C:\Program Files\IVI Foundation\IVI\Bin\AGN6030A.dll', 
                                    address='TCPIP::192.168.1.103::INSTR', reset=True) 


#Can be done in YAML
# instr_ddg = DDG_DG645('ddg_real')
# new_exp.add_instrument(instr_ddg)

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
ddg_module = DDG(new_exp.station.load_pulser())
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
new_exp.station.load_pulser().trigger_rate(500e3)

# awg_wfm = WaveformAWG([(awg_agilent1, 'ch1')], 1e9)
# awg_wfm.add_waveform_segment(WFS_Gaussian("init", 256e-9, 0.5))
# awg_wfm.add_waveform_segment(WFS_Constant("hold", 256e-9, 0.5))
# awg_wfm.add_waveform_segment(WFS_Constant("read", 512e-9, 0.0))
# awg_wfm.get_marker_output(0).set_markers_to_none()
# awg_wfm.get_marker_output(1).set_markers_to_none()
# awg_wfm.program_AWG()

awg_wfm2 = WaveformAWGIQ([(awg_agilent1, 'ch1'),(awg_agilent1, 'ch2')], 1.25e9, 10e6, global_factor=1)#Clocks were out of sync - so hence 26MHz (it was beating with the DDC sinusoids and the AWG one!)
awg_wfm2.IQdcOffset = (0,0)
# awg_wfm2.add_waveform_segment(WFS_Gaussian("init", 512e-9, 1.0))
# awg_wfm2.add_waveform_segment(WFS_Constant("zero1", 128e-9, 0.0))
# awg_wfm2.add_waveform_segment(WFS_Constant("hold", 1024e-9, 0.5))
# awg_wfm2.add_waveform_segment(WFS_Constant("zero2", 128e-9, 0.0))
# awg_wfm2.add_waveform_segment(WFS_Gaussian("pulse", 512e-9, 1.0))
# awg_wfm2.add_waveform_segment(WFS_Constant("read", 512e-9, 0.0))
awg_wfm2.add_waveform_segment(WFS_Gaussian("init", 512e-9, 0.5))
awg_wfm2.add_waveform_segment(WFS_Constant("zero1", 128e-9*2, 0.25))
awg_wfm2.add_waveform_segment(WFS_Gaussian("init2", 512e-9, 0.5))
awg_wfm2.add_waveform_segment(WFS_Constant("zero2", 512e-9, 0.0))


awg_wfm2.get_output_channel(0).Amplitude = 0.5
awg_wfm2.get_output_channel(1).Amplitude = 0.5
awg_wfm2.get_marker_output(0,0).set_markers_to_segments(["init","init2"])
awg_wfm2.get_marker_output(1,0).set_markers_to_segments(["zero1","zero2"])
awg_wfm2.get_marker_output(0,1).set_markers_to_segments(["init","zero1"])
awg_wfm2.get_marker_output(1,1).set_markers_to_segments(["zero1","init2"])
# awg_wfm2.get_marker_output(0).set_markers_to_none()
# awg_wfm2.get_marker_output(1).set_markers_to_none()
awg_wfm2.program_AWG()
# lePlot = awg_wfm2.plot_waveforms().show()

# acq_module = ACQ(new_exp.station.load_fpgaACQ())
# acq_module.NumSamples = 248
# acq_module.NumSegments = 1
# acq_module.SampleRate = 1e9
# acq_module.TriggerEdge = 0
# acq_module.set_trigger_source(ddg_module, 'AB')

# my_param1 = VariableInstrument("len1", awg_wfm2, 'IQFrequency')
# my_param2 = VariableInstrument("len2", awg_wfm2, 'IQPhase')

# tc = TimingConfiguration(1.2e-6, [ddg_module], [awg_wfm], acq_module)
# lePlot = tc.plot().show()
# leData = new_exp.run(tc, [(my_param1, np.linspace(20e6,35e6,10)),(my_param2, np.linspace(0,3,3))])

# import matplotlib.pyplot as plt
# plt.plot(np.abs(leData[0][0][:]))
# plt.show()


input('press <ENTER> to continue')
