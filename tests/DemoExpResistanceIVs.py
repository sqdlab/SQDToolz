import sqdtoolz as stz
from sqdtoolz.Experiments.Experimental.ExpResistanceIVs import ExpResistanceIVs
import numpy as np

lab = stz.Laboratory(instr_config_file = "tests\\DemoExpResistanceIVs.yaml", save_dir = "mySaves\\")


#####################################
complianceCurrent_JJ = 10e-6
probe_type = 'TwoWire'

lab.load_instrument('smu_keithley')
stz.GENsmu('junction', lab, 'smu_keithley')

stz.VariableProperty('V_jj', lab, lab.HAL('junction'), 'Voltage')
stz.VariableProperty('I_jj', lab, lab.HAL('junction'), 'Current')

lab.HAL('junction').Mode = 'SrcV_MeasI'
lab.HAL('junction').Output = True
lab.HAL('junction').ComplianceCurrent = complianceCurrent_JJ
lab.HAL('junction').ManualActivation = False
lab.HAL('junction').RampRateVoltage = 0.1
lab.HAL('junction').RampRateCurrent = 0.1
lab.HAL('junction').ProbeType = probe_type

stz.ExperimentConfiguration('V_sweep', lab, 0, ['junction'])
#####################################


stz.VariableInternal('dummy', lab)


# exp = ExpResistanceIVs('test', lab.CONFIG('V_sweep'), lab.VAR('V_jj'), np.linspace(0.0, 0.01, 20), lab.VAR('V_jj'), lab.VAR('I_jj'))
# lab.run_single(exp, [(lab.VAR('dummy'), np.arange(5))])
# res = exp.retrieve_last_aux_dataset('ResistanceFits')


lab.load_instrument('PerfectPrimeThermometer')
therm = stz.GENtherm("therm", lab, ['PerfectPrimeThermometer', 'CH1'])
#
exp = ExpResistanceIVs('test', lab.CONFIG('V_sweep'), lab.VAR('V_jj'), np.linspace(0.0, 0.01, 20), lab.VAR('V_jj'), lab.VAR('I_jj'), average_other_params=True)
lab.run_single(exp, [(lab.VAR('dummy'), np.arange(5))], rec_params=[(lab.HAL('therm'), 'Temperature')])
res = exp.retrieve_last_aux_dataset('ResistanceFits')


a=0

# input('Press ENTER')
