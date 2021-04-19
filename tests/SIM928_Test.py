from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENvoltSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\SIM928.yaml", save_dir = "mySaves\\")

instr_sim928 = new_lab._station.load_sim_rack928()

volt_module = GENvoltSource(instr_sim928.get_output(3))

#Slow Ramp
volt_module.RampRate = 0.001
volt_module.Voltage = 0.020
input('press <ENTER> to continue')
#Fast Ramp
volt_module.RampRate = 0.1
volt_module.Voltage = 1.0
input('press <ENTER> to continue')
volt_module.Voltage = 0.0

input('press <ENTER> to continue')
