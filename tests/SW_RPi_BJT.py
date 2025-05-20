from sqdtoolz.HAL.GENswitch import GENswitch
from sqdtoolz.Laboratory import Laboratory

lab = Laboratory(instr_config_file = "tests\\SW_RPi_BJT.yaml", save_dir = "mySaves\\")

lab.load_instrument('sw_rpi')

GENswitch('sw_rpi', lab, 'sw_rpi')

lab.HAL('sw_rpi').Position = "P0"
lab.HAL('sw_rpi').Position = "P1"
lab.HAL('sw_rpi').Position = "P0"
lab.HAL('sw_rpi').Position = "P2"
lab.HAL('sw_rpi').Position = "P0"
lab.HAL('sw_rpi').Position = "P3"
lab.HAL('sw_rpi').Position = "P0"

