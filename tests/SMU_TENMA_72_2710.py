import sqdtoolz as stz

new_lab = stz.Laboratory(instr_config_file = "tests\\SMU_TENMA_72_2710.yaml", save_dir = "mySaves\\")

new_lab.load_instrument('dc_supply')

smu_module = stz.GENsmu('DC_SUPPLY', new_lab, 'dc_supply')

smu_module.Voltage=0.01

smu_module.Voltage=0.01

print(smu_module)

input('Press ENTER')
