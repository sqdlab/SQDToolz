import sqdtoolz as stz
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
# from simple_pid import PID
import time
from sqdtoolz.Experiments.Experimental.ExpPID import ExpPID

lab = stz.Laboratory(instr_config_file = 'tests/TemperaturePID.yaml', save_dir = 'mySaves/', using_VS_Code=False)
lab.UpdateStateEnabled = False

lab.load_instrument('PerfectPrimeThermometer')
therm = stz.GENtherm("therm", lab, ['PerfectPrimeThermometer', 'CH1'])

lab.load_instrument('dc_supply')
dc_supply = stz.GENsmu('DC_SUPPLY', lab, 'dc_supply')

dc_supply.RampRateVoltage = 10
dc_supply.Voltage = 0
dc_supply.Current = 3
dc_supply.Output = True

stz.ExperimentConfiguration('test', lab, 1, [], None)

stz.VariableInternal('tempSetPt', lab, 200)
stz.VariableProperty('voltOut', lab, lab.HAL('DC_SUPPLY'), 'Voltage')
stz.VariableProperty('tempMeas', lab, lab.HAL('therm'), 'Temperature')


stz.VariableInternal('dummy', lab, 0)

expt = stz.Experiment('test', lab.CONFIG('test'))
exptPID = ExpPID(expt, lab.VAR('tempSetPt'), lab.VAR('tempMeas'), lab.VAR('voltOut'), 0.2, 0.005, 0.1, output_min=0, output_max=10)
lab.run_single(exptPID, [(lab.VAR('dummy'), np.arange(500))], rec_params=[(lab.HAL('therm'), 'Temperature'), (lab.HAL('DC_SUPPLY'), 'Voltage')], delay=1)
# lab.run_single(exptPID, [(lab.VAR('dummy'), np.arange(200))], delay=1)

dc_supply.Voltage = 0

a=0
