from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENsmu import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*
import matplotlib.pyplot as plt

lab = Laboratory(instr_config_file = "tests\\SMU_Keithley236.yaml", save_dir = "mySaves\\")

lab.load_instrument('smu')

smu_module = GENsmu('junction', lab, ['smu'])

complianceVoltage_JJ = 2e-3
probe_type = 'FourWire'

lab.HAL('junction').Mode = 'SrcI_MeasV'
lab.HAL('junction').Output = True
lab.HAL('junction').ComplianceVoltage = complianceVoltage_JJ
lab.HAL('junction').ManualActivation = False
lab.HAL('junction').RampRateVoltage = 0.1
lab.HAL('junction').RampRateCurrent = 0.1
lab.HAL('junction').ProbeType = probe_type

#For Fast Sweep on Keithley SMU
lab.HAL('junction').SweepSampleTime = 0.01 #0.001
lab.HAL('junction').SweepSamplePoints = 20
lab.HAL('junction').SweepStartValue = -5e-8
lab.HAL('junction').SweepEndValue = 5e-8#50e-6

ExperimentConfiguration('I_sweepFast', lab, 0, [], 'junction')

V_sweep = Experiment("test", lab.CONFIG('I_sweepFast'))
leData = lab.run_single(V_sweep)

currents, voltages = leData.get_numpy_array().T

m,b = np.polyfit(voltages, currents,1)
#%matplotlib inline
plt.plot(voltages, currents, 'r.')
fit_currents = [m*i+b for i in voltages]
plt.plot(voltages, fit_currents, 'g-')

plt.show()

input('Press ENTER')
