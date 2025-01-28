from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*

from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformMapper import*

import numpy as np

import shutil

def arr_equality(arr1, arr2):
    if arr1.size != arr2.size:
        return False
    return np.sum(np.abs(arr1 - arr2)) < 1e-15

def round_to_samplerate(awgobj, arr):
    step = 1.0 / awgobj.SampleRate
    return np.around(arr / step) * step

lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

lab.load_instrument('virACQ')
lab.load_instrument('virDDG')
lab.load_instrument('virAWG')
lab.load_instrument('virMWS')

#Initialise test-modules
hal_acq = ACQ("dum_acq", lab, 'virACQ')
hal_ddg = DDG("ddg", lab, 'virDDG', )
awg_wfm = WaveformAWG("Wfm1", lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
awg_wfm2 = WaveformAWG("Wfm2", lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9)
hal_mw = GENmwSource("MW-Src", lab, 'virMWS', 'CH1')


hal_ddg = lab.HAL('ddg')
hal_acq = lab.HAL('dum_acq')
awg_wfm = lab.HAL('Wfm1')
awg_wfm2 = lab.HAL('Wfm2')
hal_mw = lab.HAL('MW-Src')

hal_ddg.set_trigger_output_params('A', 50e-9)
hal_ddg.get_trigger_output('B').TrigPulseLength = 100e-9
hal_ddg.get_trigger_output('B').TrigPulseDelay = 50e-9
hal_ddg.get_trigger_output('B').TrigPolarity = 1
hal_ddg.get_trigger_output('C').TrigPulseLength = 400e-9
hal_ddg.get_trigger_output('C').TrigPulseDelay = 250e-9
hal_ddg.get_trigger_output('C').TrigPolarity = 0

read_segs = []
read_segs2 = []
awg_wfm.clear_segments()
awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
for m in range(4):
    awg_wfm.add_waveform_segment(WFS_Gaussian(f"init{m}", None, 20e-9, 0.5-0.1*m))
    awg_wfm.add_waveform_segment(WFS_Constant(f"zero1{m}", None, 30e-9, 0.1*m))
    awg_wfm.add_waveform_segment(WFS_Gaussian(f"init2{m}", None, 45e-9, 0.5-0.1*m))
    awg_wfm.add_waveform_segment(WFS_Constant(f"zero2{m}", None, 77e-9*(m+1), 0.0))
    read_segs += [f"init{m}"]
    read_segs2 += [f"zero2{m}"]
awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
awg_wfm.AutoCompression = 'None'#'Basic'

read_segs = []
awg_wfm2.clear_segments()
for m in range(2):
    awg_wfm2.add_waveform_segment(WFS_Gaussian(f"init{m}", None, 20e-9, 0.5-0.1*m))
    awg_wfm2.add_waveform_segment(WFS_Constant(f"zero{m}", None, 27e-9*(m+1), 0.0))
    read_segs += [f"zero{m}"]
awg_wfm2.get_output_channel(0).marker(0).set_markers_to_segments(read_segs)
awg_wfm2.AutoCompression = 'None'#'Basic'

#Try adding the MW module to the loop and see what happens
#
#Test it is business as usual if the MW module is just added in Continuous mode
hal_mw.Mode = 'Continuous'
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration('testConf', lab, 2e-6, ['ddg', 'Wfm1', 'Wfm2', 'MW-Src'], 'dum_acq')
arr_act, arr_act_segs, cur_trig_srcs = expConfig.get_trigger_edges(hal_acq)
temp = np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)])
arr_exp = round_to_samplerate(awg_wfm, np.sort(np.concatenate( [(650+0)*1e-9 + temp, (650+20+27)*1e-9 + temp])) )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
#
#Test that the MW source is still omitted from calculations if in Continuous mode...
expConfig.plot().show()
input('Press ENTER after verifying MW source does not show up')

lab.release_all_instruments()
lab = None
