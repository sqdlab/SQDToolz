import sqdtoolz
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.RemoteHAL import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

import Pyro4
# remote_obj = Pyro4.Proxy('PYRO:obj_6e5a70763dd84b2bb13d6b2c1ad81564@localhost:59297')

new_lab = Laboratory(instr_config_file = "tests\\Remote_SMU_Keithley236.yaml", save_dir = "mySaves\\")

remote_smu = RemoteHAL('SMU', new_lab, 'PYRO:obj_1daaa3bacbaf40cd8dc4bcd842f03328@192.168.1.205:51729')

print(new_lab.HAL('SMU').Output)
new_lab.HAL('SMU').Output = False

new_lab.HAL('SMU').Voltage = 0.01

# print(new_lab.HAL('SMU').Current)

sqdtoolz.VariableProperty('voltage', new_lab, new_lab.HAL('SMU'), 'Voltage')

new_lab.VAR('voltage').Value = 0

exp_config = ExperimentConfiguration('remote_smu_test', new_lab, 0, ['SMU'])

exp = Experiment('remote_smu_test', new_lab.CONFIG('remote_smu_test'))

leData = new_lab.run_single(exp, [(new_lab.VAR('voltage'), np.linspace(0,0.1,11))], delay=1)

input('Press ENTER')
