from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENsmu import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\SMU_B2901A.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('smu')

smu_module = GENsmu('vSMU', new_lab, ['smu'])

#Connect a 10kOhm resistor across the force outputs...
#
print('Set Voltage, Measure Current')
smu_module.Mode = 'SrcV_MeasI'
smu_module.Output = True
smu_module.ComplianceCurrent = 5e-7
v_vals = np.linspace(0,10e-3,10)
vm_vals = []
c_vals = []
for v in v_vals:
    smu_module.Voltage = v
    vm_vals += [smu_module.SenseVoltage]
    c_vals += [smu_module.SenseCurrent]
    print(f'{v}, {c_vals[-1]}')
fig, axs = plt.subplots(nrows=2)
axs[0].plot(v_vals, c_vals)
axs[1].plot(v_vals, vm_vals)
fig.show()
input('Press ENTER')
#
print('Set Voltage, Measure Current')
smu_module.Mode = 'SrcV_MeasI'
smu_module.Output = True
smu_module.ComplianceCurrent = 10e-7
v_vals = np.linspace(0,10e-3,10)
vm_vals = []
c_vals = []
for v in v_vals:
    smu_module.Voltage = v
    vm_vals += [smu_module.SenseVoltage]
    c_vals += [smu_module.SenseCurrent]
    print(f'{v}, {c_vals[-1]}')
fig, axs = plt.subplots(nrows=2)
axs[0].plot(v_vals, c_vals)
axs[1].plot(v_vals, vm_vals)
fig.show()
input('Press ENTER')
#
print('Set Current, Measure Voltage')
smu_module.Mode = 'SrcI_MeasV'
smu_module.Output = True
smu_module.ComplianceVoltage = 0.005
c_vals = np.linspace(0,1e-6,10)
cm_vals = []
v_vals = []
for c in c_vals:
    smu_module.Current = c
    cm_vals += [smu_module.SenseCurrent]
    v_vals += [smu_module.SenseVoltage]
    print(f'{c}, {v_vals[-1]}')
fig, axs = plt.subplots(nrows=2)
axs[0].plot(c_vals, v_vals)
axs[1].plot(c_vals, cm_vals)
fig.show()
input('Press ENTER')
