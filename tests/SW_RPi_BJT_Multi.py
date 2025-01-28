from sqdtoolz.HAL.GENswitch import GENswitch
from sqdtoolz.Laboratory import Laboratory

lab = Laboratory(instr_config_file = "tests\\SW_RPi_BJT_Multi.yaml", save_dir = "mySaves\\")

lab.load_instrument('sw_rpi')

GENswitch('sw_rpi1', lab, ['sw_rpi', 'sw1'])
GENswitch('sw_rpi2', lab, ['sw_rpi', 'sw2'])

lab.HAL('sw_rpi1').Position = "P0"
lab.HAL('sw_rpi1').Position = "P1"
lab.HAL('sw_rpi1').Position = "P0"
lab.HAL('sw_rpi1').Position = "P2"
lab.HAL('sw_rpi1').Position = "P0"
lab.HAL('sw_rpi1').Position = "P3"
lab.HAL('sw_rpi1').Position = "P0"
lab.HAL('sw_rpi1').Position = "P4"
lab.HAL('sw_rpi1').Position = "P0"

lab.HAL('sw_rpi2').Position = "P0"
lab.HAL('sw_rpi2').Position = "P1"
lab.HAL('sw_rpi2').Position = "P0"
lab.HAL('sw_rpi2').Position = "P2"
lab.HAL('sw_rpi2').Position = "P0"
lab.HAL('sw_rpi2').Position = "P3"
lab.HAL('sw_rpi2').Position = "P0"
lab.HAL('sw_rpi2').Position = "P4"
lab.HAL('sw_rpi2').Position = "P0"
