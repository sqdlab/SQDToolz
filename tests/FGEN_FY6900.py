import sqdtoolz as stz

lab = stz.Laboratory(instr_config_file = "tests/FGEN_FY6900.yaml", save_dir = "mySaves/")

lab.load_instrument('fgen')
stz.GENfuncGen('fgen1', lab, 'fgen', 'CH1')

lab.HAL('fgen1').Waveform = "SQUARE"
lab.HAL('fgen1').Frequency = 69e3
lab.HAL('fgen1').Amplitude = 2
lab.HAL('fgen1').Offset = -0.05
lab.HAL('fgen1').Output = True


input('press <ENTER> to continue')


lab.HAL('fgen1').Waveform = "SINE"
lab.HAL('fgen1').Frequency = 100e3
lab.HAL('fgen1').Amplitude = 2
lab.HAL('fgen1').Offset = 0.0
lab.HAL('fgen1').Output = False

input('press <ENTER> to continue')