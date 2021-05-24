from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENatten import*
from sqdtoolz.Laboratory import*

new_lab = Laboratory(instr_config_file = "tests\\ATTEN_Vaunix.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('VaunixAtten')
atten_module = GENatten('rf_atten', new_lab, ['VaunixAtten', 'CH1'])

atten_module.Attenuation = 10
print(f'Attenuation: {atten_module.Attenuation}')
input('press <ENTER> to continue')
