from sqdtoolz.HAL.GENswitch import GENswitch
from sqdtoolz.Laboratory import Laboratory

lab = Laboratory(instr_config_file = "tests\\SW_RpiIQBox.yaml", save_dir = "mySaves\\")

lab.load_instrument('sw_rpi')

GENswitch('sw_rpi', lab, 'sw_rpi')

lab.HAL('sw_rpi').Position = "Pmeas"
lab.HAL('sw_rpi').Position = "Pmix"
lab.HAL('sw_rpi').Position = "Pmeas"
lab.HAL('sw_rpi').Position = "Pmix"
lab.HAL('sw_rpi').Position = "Pmeas"

