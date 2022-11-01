from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENtherm import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*
from sqdtoolz.Variable import*

new_lab = Laboratory(instr_config_file = "tests\\THERM_TC0309.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('PerfectPrimeThermometer')
therm = GENtherm("therm", new_lab, ['PerfectPrimeThermometer', 'CH1'])
ExperimentConfiguration('testConf', new_lab, -1, [])

VariableInternal('dummy', new_lab)

expt = Experiment('test', new_lab.CONFIG('testConf'))
leData = new_lab.run_single(expt, [(new_lab.VAR('dummy'), np.arange(20))], delay=1, rec_params=[(new_lab.HAL('therm'), 'Temperature')])

arr = expt.last_rec_params.get_numpy_array()
plt.plot(arr)
plt.show()

input('press <ENTER> to continue')
