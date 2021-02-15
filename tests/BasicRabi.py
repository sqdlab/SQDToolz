from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformModulations import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyACQ import*
from sqdtoolz.Drivers.dummyAWG import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Parameter import*

from sqdtoolz.ExperimentConfigurations.Experimental.ExpConfigIQpulseInSingleOut import ExpConfigIQpulseInSingleOut
from sqdtoolz.Experiments.Experimental.ExperimentRabi import ExperimentRabi
import numpy as np

new_lab = Laboratory(instr_config_file = "", save_dir = "mySaves\\")

#Can be done in YAML
instr_ddg = DummyDDG('ddg')
new_lab.add_instrument(instr_ddg)
instr_acq = DummyACQ('acq')
new_lab.add_instrument(instr_acq)
instr_awg = DummyAWG('awg_test_instr')
new_lab.add_instrument(instr_awg)

ddg_module = DDG(instr_ddg)
awg_wfm_q = WaveformAWG("Waveform 2", [(instr_awg, 'CH3'),(instr_awg, 'CH4')], 1e9)
acq_module = ACQ(instr_acq)

mod_freq_qubit = WM_SinusoidalIQ("QubitFreqMod", 100e6)

param_rab_freq = new_lab.add_parameter('Rabi Frequency')

expt_config = ExpConfigIQpulseInSingleOut(2.5e-6, ddg_module, 'A', awg_wfm_q, acq_module, 1e9)

exp_rabi = ExperimentRabi("myRabi", expt_config, mod_freq_qubit, np.linspace(0,100e-9,5), param_rab_freq)


leData = new_lab.run_single(exp_rabi)
# input('press <ENTER> to continue')

lePlot = expt_config.plot().show()
input('press <ENTER> to continue')
