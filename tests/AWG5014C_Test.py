from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.ExperimentConfiguration import*

new_lab = Laboratory(instr_config_file = "tests\\AWG5014C_Test.yaml", save_dir = "mySaves\\")

instrAWG = new_lab.station.load_awg5014C()
ch1 = instrAWG.get_output_channel('CH1')
ch1.output