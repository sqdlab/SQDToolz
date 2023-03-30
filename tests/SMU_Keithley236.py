from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENsmu import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*
import matplotlib.pyplot as plt

new_lab = Laboratory(instr_config_file = "tests\\SMU_Keithley236.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('smu')

smu_module = GENsmu('vSMU', new_lab, ['smu'])

new_lab.HAL('vSMU').Mode = 'SrcV_MeasI'
new_lab.HAL('vSMU').Output = True
new_lab.HAL('vSMU').ComplianceCurrent = 5e-3
# new_lab.HAL('vSMU').ComplianceVoltage = 10
new_lab.HAL('vSMU').ManualActivation = False
new_lab.HAL('vSMU').RampRateVoltage = 0.1
new_lab.HAL('vSMU').RampRateCurrent = 0.1
new_lab.HAL('vSMU').ProbeType = 'TwoWire'
new_lab.HAL('vSMU').ComplianceVoltage = 10

# currents, voltages = new_lab.HAL('vSMU')._instr_smu.resistance(0, 0.02, 0.001, 0)

print(new_lab.HAL('vSMU'))

currents, voltages = new_lab.HAL('vSMU')._instr_smu.resistance(0, 0.02, 0.001, 0)

m,b = np.polyfit(voltages, currents,1)
fit_currents = [m*i+b for i in voltages]
resistance = 1/abs(m)
data = str(resistance)+' Ohm'
print('Estimated resistance {:.3f}kOhm'.format(resistance/1e3))
print('Estimated resistance {:.3f}'.format(resistance))

new_lab.HAL('vSMU').Mode = 'SrcI_MeasV'
new_lab.HAL('vSMU').ProbeType = 'TwoWire'

currents, voltages = new_lab.HAL('vSMU')._instr_smu.resistance(0, 0.001, 0.00001, 0)

m,b = np.polyfit(voltages, currents,1)
fit_currents = [m*i+b for i in voltages]
resistance = 1/abs(m)
data = str(resistance)+' Ohm'
print('Estimated resistance {:.3f}kOhm'.format(resistance/1e3))
print('Estimated resistance {:.3f}'.format(resistance))


# input('Press ENTER')
