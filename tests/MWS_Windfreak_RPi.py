import sqdtoolz as stz

lab = stz.Laboratory(instr_config_file = "tests\\MWS_Windfreak_RPi.yaml", save_dir = "mySaves\\")


lab.load_instrument('mws_windfreak_rpi')

stz.GENmwSource('mw_test1a', lab, ['mws_windfreak_rpi', 'WF_1'], 'RFoutA')
stz.GENmwSource('mw_test1b', lab, ['mws_windfreak_rpi', 'WF_1'], 'RFoutB')
stz.GENmwSource('mw_test2a', lab, ['mws_windfreak_rpi', 'WF_2'], 'RFoutA')
stz.GENmwSource('mw_test2b', lab, ['mws_windfreak_rpi', 'WF_2'], 'RFoutB')
stz.GENmwSource('mw_test3a', lab, ['mws_windfreak_rpi', 'WF_3'], 'RFoutA')
stz.GENmwSource('mw_test3b', lab, ['mws_windfreak_rpi', 'WF_3'], 'RFoutB')

for m in ['mw_test1a', 'mw_test1b', 'mw_test2a', 'mw_test2b', 'mw_test3a', 'mw_test3b']:
    lab.HAL(m).Output = False

print(lab.HAL('mw_test1a'))
print(lab.HAL('mw_test1b'))
print(lab.HAL('mw_test2a'))
print(lab.HAL('mw_test2b'))
print(lab.HAL('mw_test3a'))
print(lab.HAL('mw_test3b'))
a=0
