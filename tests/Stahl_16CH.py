from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENvoltSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

lab = Laboratory(instr_config_file = "tests\\Stahl_16CH.yaml", save_dir = "mySaves\\")

lab.load_instrument('stahl_volt')

stahl_source = GENvoltSource('vFlux', lab, ['stahl_volt', 'CH4'])

lab.HAL('vFlux').Voltage = 0.0
input('press <ENTER> to continue')

#Slow Ramp
lab.HAL('vFlux').RampRate = 0.001
lab.HAL('vFlux').Voltage = 0.020
input('press <ENTER> to continue')
#Fast Ramp
lab.HAL('vFlux').RampRate = 0.1
lab.HAL('vFlux').Voltage = 1.0
input('press <ENTER> to continue')
lab.HAL('vFlux').Voltage = 0.0

input('press <ENTER> to continue')




# input('Press ENTER')