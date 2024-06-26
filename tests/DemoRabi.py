from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyACQex import*
from sqdtoolz.Drivers.dummyAWG import*
from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Variable import*
from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_Max import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*

from sqdtoolz.ExperimentConfigurations.Experimental.ExpConfigIQpulseInSingleOut import ExpConfigIQpulseInSingleOut
from sqdtoolz.Experiments.Experimental.ExperimentRabi import ExperimentRabi
import numpy as np

new_lab = Laboratory(instr_config_file = "", save_dir = "mySaves\\")

#Can be done in YAML
instr_ddg = DummyDDG('ddg')
new_lab.add_instrument(instr_ddg)
instr_acq = DummyACQex('acq')
new_lab.add_instrument(instr_acq)
instr_awg = DummyAWG('awg_test_instr')
new_lab.add_instrument(instr_awg)
instr_fsrc = DummyGENmwSrc('freq_src_instr')
new_lab.add_instrument(instr_fsrc)

ddg_module = DDG(instr_ddg)
awg_wfm_q = WaveformAWG("Waveform 2", [(instr_awg, 'CH3'),(instr_awg, 'CH4')], 1e9)
acq_module = ACQ(instr_acq)
freq_src_module = GENmwSource(instr_fsrc.get_output('CH1'))

mod_freq_qubit = WFMT_ModulationIQ("QubitFreqMod", 100e6)

param_rab_freq = new_lab.add_variable('Rabi Frequency')

#Setup the trigger and instrument relations
ddg_module.set_trigger_output_params('A', 0.0, 50e-9)
acq_module.set_trigger_source(awg_wfm_q.get_output_channel(0).marker(0))
awg_wfm_q.set_trigger_source_all(ddg_module.get_trigger_output('A'))
acq_module.SampleRate = 1e9
acq_module.NumSamples = 100
acq_module.NumRepetitions = 100
#Attach a CPU post-processor
myProc = ProcessorCPU()
myProc.add_stage(CPU_Max('sample'))
myProc.add_stage(CPU_Mean('repetition'))
acq_module.set_data_processor(myProc)

#Cement the parameters into the experiment configuration
exp_config = ExpConfigIQpulseInSingleOut(2.5e-6, [ddg_module], [awg_wfm_q], acq_module, [freq_src_module], awg_wfm_q)   #TODO: Check if the configuration is compatible - e.g. a special function in the translation script?

exp_rabi = ExperimentRabi("myRabi", exp_config, mod_freq_qubit, np.linspace(0,100e-9,30), param_rab_freq)
leData = new_lab.run_single(exp_rabi)
# input('press <ENTER> to continue')

# lePlot = exp_config.plot().show()
# input('press <ENTER> to continue')
