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




# ddg_module._instr_ddg.burst_period(1e-6)

awgs = [awg_agilent1]
# reset
for awg in reversed(awgs):
    #print('resetting {0:s}'.format(awg.get_name()))
    try:
        awg.reset()
    except Exception as e:
        print(e)
# awgs clocking and syncronization
for awg in awgs[:1]:
    # use external 10MHz ref clock
    awg.ref_clock_source('External')
    # 1.2GHz clock from Tektronix AWG
    #awg_tek.run()
    #awg.configure_sample_clock(source=1, freq=1.20e9)
    # 1GHz clock from microwave source
    #awg.configure_sample_clock(source=1, freq=1e9)
    # 1.25GHz internal clock
    awg.configure_sample_clock(source=0, freq=1.25e9)
    awg.configure_clock_sync(enabled=False, master=True)
for awg in awgs[1:]:
    awg.configure_sample_clock(source=1, freq=awgs[0].get_clock_frequency())
    awg.configure_clock_sync(enabled=True, master=False)
# 
# channel settings
for awg in awgs:
    awg.ch1.operation_mode('Burst')
    awg.ch1.burst_count(1)
    awg.ch2.operation_mode('Burst')
    awg.ch2.burst_count(1)
    awg.ch1.output_configuration('Amplified')
    awg.ch2.output_configuration('Amplified')
    awg.predistortion(False)
    awg.ch1.output_filter(False)
    awg.ch2.output_filter(False)
    awg.ch1.gain(0.5)
    awg.ch2.gain(0.5)    
    #awg.set_ch1_output_bandwidth(500e6)
    #awg.set_ch2_output_bandwidth(500e6)
    awg.ch1.output_impedance(50)
    awg.ch2.output_impedance(50)
    awg.ch1.output(True)
    awg.ch2.output(True)
    awg.m1.source('Channel 1 Marker 1')
    awg.m2.source('Channel 1 Marker 2')
    awg.m3.source('Channel 2 Marker 1')
    awg.m4.source('Channel 2 Marker 2')
    awg.clock_source('Internal')
#     awg.ch1.configure_trigger_source(1024) # No Trigger flag
#     awg.ch2.configure_trigger_source(1024) # No Trigger flag
    awg.ch1.configure_trigger_source(1|1026|1028|1032|1040) # any hardware trigger input
    awg.ch2.configure_trigger_source(1|1026|1028|1032|1040) # any hardware trigger input
    awg.trigger_threshold_B(0.7)

# triggered by hardware trigger 1 of awg #1 -- this must be set after switching to burst mode
for awg in awgs[:1]:
    awg.trigger_threshold_A(1.)
    awg.m4.source('Hardware Trigger 1')
# awgs[0].ch1.output(True)
# awgs[0].run()


# myHandle = awgs[0].create_arb_waveform(np.linspace(-1,1,1024))
# awgs[0].configure_arb_waveform(1, myHandle, 0.5, 0.0)
# myHandle2 = awgs[0].create_arb_waveform(np.sin(np.linspace(-np.pi,np.pi,1024)))
# awgs[0].configure_arb_waveform(2, myHandle2, 0.5, 0.0)

# awg_wfm = WaveformAWG([(awg_agilent1, 'ch1')], 1e9)
# awg_wfm.add_waveform_segment(WFS_Gaussian("init", 256e-9, 0.8))
# awg_wfm.add_waveform_segment(WFS_Constant("hold", 256e-9, 0.0))
# awg_wfm.add_waveform_segment(WFS_Constant("read", 512e-9, 0.0))
# awg_wfm.get_trigger_output().set_markers_to_none()
# awg_wfm.program_AWG()

awg_wfm2 = WaveformAWGIQ([(awg_agilent1, 'ch1'),(awg_agilent1, 'ch2')], 1.25e9, 26e6, global_factor=0.4)#Clocks were out of sync - so hence 26MHz (it was beating with the DDC sinusoids and the AWG one!)
awg_wfm2.IQdcOffset = (0,0)
# awg_wfm2.add_waveform_segment(WFS_Gaussian("init", 512e-9, 1.0))
# awg_wfm2.add_waveform_segment(WFS_Constant("zero1", 128e-9, 0.0))
# awg_wfm2.add_waveform_segment(WFS_Constant("hold", 1024e-9, 0.5))
# awg_wfm2.add_waveform_segment(WFS_Constant("zero2", 128e-9, 0.0))
# awg_wfm2.add_waveform_segment(WFS_Gaussian("pulse", 512e-9, 1.0))
# awg_wfm2.add_waveform_segment(WFS_Constant("read", 512e-9, 0.0))
awg_wfm2.add_waveform_segment(WFS_Gaussian("init", 512e-9, 1.0))
awg_wfm2.add_waveform_segment(WFS_Constant("zero1", 128e-9, 0.0))
awg_wfm2.add_waveform_segment(WFS_Gaussian("init2", 512e-9, 1.0))
awg_wfm2.add_waveform_segment(WFS_Constant("zero2", 512e-9, 0.0))


# awg_wfm2.get_output_channel(0).Amplitude = 1.0
awg_wfm2.get_trigger_output(0).set_markers_to_segments(["init","init2"])
awg_wfm2.get_trigger_output(1).set_markers_to_segments(["zero1","zero2"])
# awg_wfm2.get_trigger_output(0).set_markers_to_none()
# awg_wfm2.get_trigger_output(1).set_markers_to_none()
awg_wfm2.program_AWG()
# lePlot = awg_wfm2.plot_waveforms().show()

acq_module = ACQ(new_exp.station.load_fpgaACQ())
acq_module.NumSamples = 248
acq_module.NumSegments = 1
# acq_module.SampleRate = 1e9
# acq_module.TriggerEdge = 0
# acq_module.set_trigger_source(ddg_module, 'AB')

my_param1 = VariableInstrument("len1", awg_wfm2, 'IQFrequency')
my_param2 = VariableInstrument("len2", awg_wfm2, 'IQPhase')

tc = TimingConfiguration(1.2e-6, [ddg_module], [awg_wfm2], acq_module)
# lePlot = tc.plot().show()
# leData = new_exp.run(tc, [(my_param1, np.linspace(20e6,35e6,10)),(my_param2, np.linspace(0,3,3))])

# import matplotlib.pyplot as plt
# plt.plot(np.abs(leData[0][0][:]))
# plt.show()


input('press <ENTER> to continue')