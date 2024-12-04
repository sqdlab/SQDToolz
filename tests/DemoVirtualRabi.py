import sqdtoolz as stz
from sqdtoolz.Experiments.Experimental.ExpRabi import ExpRabi
import numpy as np

#ASSUMING THAT IT IS RUN IN VSCODE WITH SQDToolz AS THE MAIN FOLDER!
lab = stz.Laboratory('tests/DemoVirtual.yaml', 'mySaves/')

lab.load_instrument('virDDG')
lab.load_instrument('virACQ')
lab.load_instrument('virAWG')
lab.load_instrument('virMWS')
lab.load_instrument('virMWS2')

#Initialise test-modules
hal_acq = stz.ACQ("dum_acq", lab, 'virACQ')
hal_ddg = stz.DDG("ddg", lab, 'virDDG', )
awg_wfm = stz.WaveformAWG("Wfm1", lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, 50e-6)
awg_wfm2 = stz.WaveformAWG("Wfm2", lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9, 50e-6)
hal_mw = stz.GENmwSource("MW-Src", lab, 'virMWS', 'CH1')
hal_mw2 = stz.GENmwSource("MW-Src2", lab, 'virMWS2', 'CH1')

lab.HAL('dum_acq').SampleRate = 1e9
lab.HAL('dum_acq').NumSamples = 100
lab.HAL('dum_acq').NumRepetitions = 100

myProc = stz.ProcessorCPU('cpu_proc', lab)
myProc.add_stage(stz.CPU_Max('sample'))
myProc.add_stage(stz.CPU_Mean('segment'))
myProc.add_stage(stz.CPU_Mean('repetition'))
lab.HAL('dum_acq').set_data_processor(myProc)

mod_freq_qubit = stz.WFMT_ModulationIQ("QubitFreqMod", lab, 100e6)

stz.ExperimentSpecification('res0', lab, 'Cavity')
stz.ExperimentSpecification('qubit0', lab, 'Qubit')

stz.ExperimentConfiguration('testConfig', lab, 2.5e-6, ['ddg', 'Wfm1', 'MW-Src'], 'dum_acq', ['res0', 'qubit0'])
waveform_mapping = stz.WaveformMapper()
waveform_mapping.add_waveform('qubit', 'Wfm1')
waveform_mapping.add_digital('readout', awg_wfm.get_output_channel(0).marker(1))
lab.CONFIG('testConfig').map_waveforms(waveform_mapping)

lab.open_browser()

exp_rabi = ExpRabi("myRabi", lab.CONFIG('testConfig'), mod_freq_qubit, np.linspace(0,100e-9,30), lab.SPEC('qubit0'))
leData = lab.run_single(exp_rabi, delay=0.5)

