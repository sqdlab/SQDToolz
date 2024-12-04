import sqdtoolz as stz

#Connect CH1 to the calibration pin...

lab = stz.Laboratory(instr_config_file = "tests/DSO_DS1054Z.yaml", save_dir = "mySaves/")

lab.load_instrument('rigoldso')
stz.ACQdso('DSO', lab, 'rigoldso')

lab.HAL('DSO').channel(0).Enabled = True
lab.HAL('DSO').channel(1).Enabled = False
lab.HAL('DSO').channel(2).Enabled = False
lab.HAL('DSO').channel(3).Enabled = False

lab.HAL('DSO').SampleRate = 10e6
lab.HAL('DSO').NumSamples = 120000

# print(lab.HAL('DSO')._get_current_config())

stz.ExperimentConfiguration('contMeas', lab, 500e-6, [], 'DSO')
new_exp = stz.Experiment('test', lab.CONFIG('contMeas'))
leData = lab.run_single(new_exp, [])

input('press <ENTER> to continue')
