import sqdtoolz as stz
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
# from simple_pid import PID
import time

lab = stz.Laboratory(instr_config_file = 'tests/TemperaturePID.yaml', save_dir = 'mySaves/', using_VS_Code=False)
lab.UpdateStateEnabled = False

lab.load_instrument('PerfectPrimeThermometer')
therm = stz.GENtherm("therm", lab, ['PerfectPrimeThermometer', 'CH1'])

lab.load_instrument('dc_supply')
dc_supply = stz.GENsmu('DC_SUPPLY', lab, 'dc_supply')

dc_supply.Mode = 'SrcV_MeasI'
dc_supply.RampRateVoltage = 10
dc_supply.Voltage = 0
dc_supply.Current = 3
dc_supply.Output = True


stz.VariableProperty('voltOut', lab, lab.HAL('DC_SUPPLY'), 'Voltage')
stz.VariableProperty('tempMeas', lab, lab.HAL('therm'), 'Temperature')


stz.VariableInternal('dummy', lab, 0)

stz.SOFTpid('pidTest', lab,  lab.VAR('tempMeas'), lab.VAR('voltOut'),  0.2, 0.005, 0.1, output_min=0, output_max=10)

lab.HAL('pidTest').SetPoint = 50

stz.ExperimentConfiguration('test', lab, 1, ['DC_SUPPLY', 'pidTest'], None)

expt = stz.Experiment('test', lab.CONFIG('test'))
lab.run_single(expt, [(lab.VAR('dummy'), np.arange(500))], rec_params=[(lab.HAL('therm'), 'Temperature'), (lab.HAL('DC_SUPPLY'), 'Voltage')], delay=1)
# lab.run_single(exptPID, [(lab.VAR('dummy'), np.arange(200))], delay=1)

dc_supply.Voltage = 0

a=0
