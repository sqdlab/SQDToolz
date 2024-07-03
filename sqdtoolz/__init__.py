from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiment import Experiment
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.ExperimentSpecification import*
from sqdtoolz.Variable import*

from sqdtoolz.HAL.DDG import DDG
try:
    from sqdtoolz.HAL.MultiACQ import MultiACQ
except ModuleNotFoundError:
    pass
from sqdtoolz.HAL.ACQ import ACQ
from sqdtoolz.HAL.AWG import WaveformAWG #TODO: Refactor this - RB is angry
from sqdtoolz.HAL.GENmwSource import GENmwSource
from sqdtoolz.HAL.GENvoltSource import GENvoltSource
from sqdtoolz.HAL.GENatten import GENatten
from sqdtoolz.HAL.GENswitch import GENswitch
from sqdtoolz.HAL.GENswitchTrig import GENswitchTrig
from sqdtoolz.HAL.GENtherm import GENtherm
from sqdtoolz.HAL.SOFTpid import SOFTpid
from sqdtoolz.HAL.ACQvna import ACQvna
from sqdtoolz.HAL.GENsmu import GENsmu
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformMapper import*
from sqdtoolz.HAL.WaveformTransformations import*

from sqdtoolz.HAL.Processors.ProcessorCPU import*
try:
    from sqdtoolz.HAL.Processors.ProcessorGPU import*
except (ModuleNotFoundError, ImportError):
    pass
from sqdtoolz.HAL.Processors.ProcessorFPGA import*


# print('hi')