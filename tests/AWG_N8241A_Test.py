from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.TimingConfiguration import*
from sqdtoolz.Drivers.Agilent_N8241A import*
import numpy as np

new_exp = Experiment(instr_config_file = "tests\\BenchTest.yaml", save_dir = "", name="test")

awg_agilent1 = Agilent_N8241A('awg_agilent1', ivi_dll=r'C:\Program Files\IVI Foundation\IVI\Bin\AGN6030A.dll', 
                                    address='TCPIP::192.168.0.103::INSTR', reset=True) 


#Can be done in YAML
# instr_ddg = DDG_DG645('ddg_real')
# new_exp.add_instrument(instr_ddg)

#Ideally, the length and polarity are set to default values in the drivers via the YAML file - i.e. just set TrigPulseDelay
ddg_module = DDG(new_exp.station.load_pulser())
ddg_module.get_trigger_output('AB').TrigPulseLength = 50e-9
ddg_module.get_trigger_output('AB').TrigPolarity = 1
ddg_module.get_trigger_output('AB').TrigPulseDelay = 10e-9
ddg_module.get_trigger_output('CD').TrigPulseLength = 100e-9
ddg_module.get_trigger_output('CD').TrigPulseDelay = 50e-9
ddg_module.get_trigger_output('CD').TrigPolarity = 1
ddg_module.get_trigger_output('EF').TrigPulseLength = 400e-9
ddg_module.get_trigger_output('EF').TrigPulseDelay = 250e-9
ddg_module.get_trigger_output('EF').TrigPolarity = 0
# awg.set_trigger_source(ddg_module.get_trigger_source('A'))

new_exp.station.load_pulser().burst_period(1e-6)

tc = TimingConfiguration(1e-6, [ddg_module], None)
ddg_module._instr_ddg.burst_period(1e-6)


#awgs = [awg_agilent0, awg_agilent1, awg_agilent2]
awgs = [awg_agilent1]
#awgs = [awg_agilent2, awg_agilent3, awg_agilent1]

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

awgs[0].create_arb_waveform(np.linspace(-1,1,1024))

awgs[0].ch1.output(True)
# awgs[0].run()
