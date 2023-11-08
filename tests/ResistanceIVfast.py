import sqdtoolz as stz
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

lab = stz.Laboratory(instr_config_file = r'tests/ResistanceIVfast.yaml', save_dir = 'mySaves/', using_VS_Code=False)
lab.UpdateStateEnabled = False

#FOR TWO WIRE
complianceVoltage = 0.1
complianceCurrent = 1.0e-6
probe_type = 'FourWire'

## FOR FOUR WIRE
# complianceVoltage = 1.0e0
# complianceCurrent = 1.0e-1
# probe_type = 'FourWire'

########################################################################

lab.load_instrument('smu_keithley')
stz.GENsmu('junction', lab, 'smu_keithley')

stz.VariableProperty('V_smu', lab, lab.HAL('junction'), 'Voltage')
stz.VariableProperty('I_smu', lab, lab.HAL('junction'), 'Current')

# lab.VAR('V_smu').Value = 0
lab.HAL("junction").Mode = "SrcI_MeasV"
lab.HAL('junction').ComplianceCurrent = complianceCurrent
lab.HAL('junction').ComplianceVoltage = complianceVoltage
lab.HAL('junction').ManualActivation = False
lab.HAL('junction').RampRateVoltage = 0.5
lab.HAL('junction').RampRateCurrent = 0.5
lab.HAL('junction').ProbeType = probe_type
#
stz.ExperimentConfiguration('V_sweep', lab, 0, ['junction'])

#For Fast Sweep on Keithley SMU
lab.HAL('junction').SweepSampleTime = 0.01 #0.001
lab.HAL('junction').SweepSamplePoints = 20
lab.HAL('junction').SweepStartValue = -10.e-6
lab.HAL('junction').SweepEndValue = 10.e-6

stz.ExperimentConfiguration('I_sweepFast4', lab, 0, [], 'junction')
lab.HAL('junction').Output = False

from sqdtoolz.Experiments.Experimental.ExpResistanceIVsFast import ExpResistanceIVsFast

stz.VariableInternal('dummySweep', lab)

expt = ExpResistanceIVsFast('Test10KrepeatSweep', lab.CONFIG('I_sweepFast4'))
leData = lab.run_single(expt, [(lab.VAR('dummySweep'), np.arange(10))])

