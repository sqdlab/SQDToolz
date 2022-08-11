from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

lab = Laboratory(instr_config_file = "tests\\WindFreak_RPi.yaml", save_dir = "mySaves\\")

lab.load_instrument('MWS_Windfreak')
lab.load_instrument('MWS_Windfreak2')

freq_module_LO1 = GENmwSource("LO1", lab, 'MWS_Windfreak', 'RFoutB')
freq_module_LO2 = GENmwSource("LO2", lab, 'MWS_Windfreak', 'RFoutA')
freq_module_drive = GENmwSource("DRIVE", lab, 'MWS_Windfreak2', 'RFoutA')

# NEED HARMONICS TO SKIP OVER 2.8-3 GHZ


# CONSTANTS
DRIVE_POWER = 10
DRIVE_FREQUENCY = 450e6 # 450 looks decent
LO1_POWER = 10
LO1_FREQUENCY = 2.9e9 + DRIVE_FREQUENCY # Want to place lower sideband at 2.9GHz, centre of first stage passband
DRIVE_PLACEMENT_FREQ = 2.9e9
LO2_POWER = 10
DESIRED_DRIVE = 5.026e9
LO2_FREQUENCY = DESIRED_DRIVE + DRIVE_PLACEMENT_FREQ # Using Lower Sideband
print("LO2 set to: ", LO2_FREQUENCY)


# Turn off all outputs
lab.HAL("LO1").Output = False
lab.HAL("LO2").Output = False
lab.HAL("DRIVE").Output = False

# Setup "Drive"
lab.HAL("DRIVE").Power = DRIVE_POWER
lab.HAL("DRIVE").Frequency = DRIVE_FREQUENCY

# Setup LO1
lab.HAL("LO1").Frequency = LO1_FREQUENCY
lab.HAL("LO1").Power = LO1_POWER

# Setup LO2
lab.HAL("LO2").Frequency = LO2_FREQUENCY
lab.HAL("LO2").Power = LO2_POWER

# Turn on outputs
lab.HAL("LO1").Output = True
lab.HAL("LO2").Output = True
lab.HAL("DRIVE").Output = True

"""
lab.HAL("LO1").Output = False
lab.HAL("LO2").Output = False
lab.HAL("DRIVE").Output = False
"""
"""
freq_module.Power = 0
freq_module.Output = True
freq_module.Frequency = 4e9
freq_module.Mode = 'Continuous'

freq_module2.Power = 0
freq_module2.Output = True
freq_module2.Frequency = 4e9
freq_module2.Mode = 'Continuous'
"""
input('press <ENTER> to continue')

lab.HAL("LO1").Output = False
lab.HAL("LO2").Output = False
lab.HAL("DRIVE").Output = False
