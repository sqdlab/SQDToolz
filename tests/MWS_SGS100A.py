import sqdtoolz as stz

lab = stz.Laboratory(instr_config_file = "tests\\MWS_SGS100A.yaml", save_dir = "mySaves\\")


lab.load_instrument('src_sgs1')

stz.GENmwSource('mw_test', lab, 'src_sgs1', 'RFOUT')

print(lab.HAL('mw_test'))
print(lab.HAL('mw_test'))
print(lab.HAL('mw_test'))
print(lab.HAL('mw_test'))
a=0
