from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENsmu import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\SMU_Keithley236.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('smu')

smu_module = GENsmu('vSMU', new_lab, ['smu'])

new_lab.HAL('vSMU').Current = 0.001
print(new_lab.HAL('vSMU').Voltage)
new_lab.HAL('vSMU').Current = 0.001
print(new_lab.HAL('vSMU').Voltage)
new_lab.HAL('vSMU').Mode = 'SrcI_MeasV'
new_lab.HAL('vSMU').Output = True

print(new_lab.HAL('vSMU'))

# input('Press ENTER')
