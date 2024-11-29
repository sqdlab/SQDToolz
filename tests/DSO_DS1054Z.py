import sqdtoolz as stz

#Connect CH1 to the calibration pin...

lab = stz.Laboratory(instr_config_file = "tests/DSO_DS1054Z.yaml", save_dir = "mySaves/")

lab.load_instrument('rigoldso')
stz.ACQdso('DSO', lab, 'rigoldso')

lab.HAL('DSO').SampleRate = 10e6
lab.HAL('DSO').NumSamples = 120000

# print(lab.HAL('DSO')._get_current_config())

stz.ExperimentConfiguration('contMeas', lab, 500e-6, [], 'DSO')
new_exp = stz.Experiment('test', lab.CONFIG('contMeas'))
leData = lab.run_single(new_exp, [])

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