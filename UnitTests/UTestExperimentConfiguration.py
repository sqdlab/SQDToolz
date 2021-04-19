from sqdtoolz.ExperimentConfiguration import*

from sqdtoolz.Drivers.dummyACQ import*
from sqdtoolz.Drivers.dummyDDG import*
from sqdtoolz.Drivers.dummyAWG import*
from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*

import numpy as np
import unittest

ENABLE_MANUAL_COMPONENTS = False

#Test the ACQ module
instr_acq = DummyACQ("dum_acq")
hal_acq = ACQ(instr_acq)
instr_ddg = DummyDDG('ddg')
hal_ddg = DDG(instr_ddg)
instr_awg = DummyAWG('awg_test_instr')
awg_wfm = WaveformAWG("Waveform 1", [(instr_awg, 'CH1'), (instr_awg, 'CH2')], 1e9)
awg_wfm2 = WaveformAWG("Waveform 2", [(instr_awg, 'CH3'), (instr_awg, 'CH4')], 1e9)
instr_fsrc = DummyGENmwSrc('MW-Src')
hal_mw = GENmwSource(instr_fsrc.get_output('CH1'))
#
#Test the set_acq_params function
hal_acq.set_acq_params(10,2,30)
assert hal_acq.NumRepetitions == 10, "ACQ HAL did not properly enter the number of repetitions."
assert hal_acq.NumSegments == 2, "ACQ HAL did not properly enter the number of segments."
assert hal_acq.NumSamples == 30, "ACQ HAL did not properly enter the number of samples."
#
expConfig = ExperimentConfiguration(1.0, [], hal_acq)
#leConfig = expConfig.save_config()

def arr_equality(arr1, arr2):
    if arr1.size != arr2.size:
        return False
    return np.sum(np.abs(arr1 - arr2)) < 1e-15

def round_to_samplerate(awgobj, arr):
    step = 1.0 / awgobj.SampleRate
    return np.around(arr / step) * step

#Test get_trigger_edges function
#
hal_ddg.set_trigger_output_params('A', 50e-9)
hal_ddg.get_trigger_output('B').TrigPulseLength = 100e-9
hal_ddg.get_trigger_output('B').TrigPulseDelay = 50e-9
hal_ddg.get_trigger_output('B').TrigPolarity = 1
hal_ddg.get_trigger_output('C').TrigPulseLength = 400e-9
hal_ddg.get_trigger_output('C').TrigPulseDelay = 250e-9
hal_ddg.get_trigger_output('C').TrigPolarity = 0
#
#Test the case where there are no trigger relations
expConfig = ExperimentConfiguration(1.0, [hal_ddg], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert arr_act_segs.size == 0, "There are erroneous trigger segments found in the current configuration."
#
#Test the case where there is a single trigger relation
#
#Test trivial DDG - should raise assert as it is not TriggerInputCompatible...
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('A'))
expConfig = ExperimentConfiguration(1.0, [hal_ddg], hal_acq)
assert_found = False
try:
    arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_ddg)    
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Function get_trigger_edges failed to trigger an assertion error when feeding a non-TriggerInputCompatible object."
#
#Test ACQ with positive input polarity
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('A'))
expConfig = ExperimentConfiguration(1.0, [hal_ddg], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = np.array([50e-9])
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + hal_ddg.get_trigger_output('A').TrigPulseLength]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
#
#Test ACQ again with the same positive input polarity
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('B'))
expConfig = ExperimentConfiguration(1.0, [hal_ddg], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = np.array([50e-9])
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + hal_ddg.get_trigger_output('B').TrigPulseLength]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
#
#Test ACQ with negative input polarity
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('C'))
expConfig = ExperimentConfiguration(1.0, [hal_ddg], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = np.array([650e-9])
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function."
arr_exp = round_to_samplerate(awg_wfm, np.array([[0.0, hal_ddg.get_trigger_output('C').TrigPulseDelay]]) )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."

#Test get_trigger_edges when triggering ACQ from AWG triggered via DDG...
#
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
#
#Test assert flagged when including a trigger source outside that supplied into ExperimentConfiguration
hal_acq.set_trigger_source(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('A'))
try:
    expConfig = ExperimentConfiguration(1.0, [hal_ddg], hal_acq)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "ExperimentConfiguration failed to trigger an assertion error when omitting a trigger source in the supplied HAL objects."
#
#Simple test feeding the AWG with simple pulse from DDG
hal_acq.set_trigger_source(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('A'))
expConfig = ExperimentConfiguration(1.0, [hal_ddg, awg_wfm], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = round_to_samplerate(awg_wfm, np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)]) + 50e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including an AWG."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp+20e-9]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including an AWG."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including an AWG."
#
#Try with a negative polarity DDG output
hal_acq.set_trigger_source(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
expConfig = ExperimentConfiguration(1.0, [hal_ddg, awg_wfm], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = round_to_samplerate(awg_wfm, np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including an AWG."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp+20e-9]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including an AWG."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including an AWG."
#
#Try with a negative polarity DDG output and negative input polarity on ACQ
hal_acq.set_trigger_source(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration(1.0, [hal_ddg, awg_wfm], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = round_to_samplerate(awg_wfm, np.array([(10+20)*1e-9, 1e-9*(10+20+30+45+77+20), 1e-9*(10+(20+30+45)*2+77*3+20), 1e-9*(10+(20+30+45)*3+77*6+20)]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including an AWG."
arr_exp = round_to_samplerate(awg_wfm, np.concatenate([ np.array([[650e-9, 650e-9+10e-9]]), np.vstack( [ arr_exp, arr_exp + np.array([1,2,3,4])*77e-9+(30+45)*1e-9 ] ).T ]) )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including an AWG."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including an AWG."
hal_acq.InputTriggerEdge = 1
#
#Try cascading DDG -> AWG1 -> AWG2 -> ACQ
read_segs = []
awg_wfm2.clear_segments()
for m in range(2):
    awg_wfm2.add_waveform_segment(WFS_Gaussian(f"init{m}", None, 20e-9, 0.5-0.1*m))
    awg_wfm2.add_waveform_segment(WFS_Constant(f"zero{m}", None, 27e-9*(m+1), 0.0))
    read_segs += [f"zero{m}"]
awg_wfm2.get_output_channel(0).marker(0).set_markers_to_segments(read_segs)
awg_wfm2.AutoCompression = 'None'#'Basic'
#
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
expConfig = ExperimentConfiguration(1.0, [hal_ddg, awg_wfm, awg_wfm2], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
temp = np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)])
arr_exp = round_to_samplerate(awg_wfm, np.sort(np.concatenate( [(650+20)*1e-9 + temp, (650+20+27+20)*1e-9 + temp])) )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([ arr_exp, arr_exp + np.tile(np.array([27e-9,27e-9*2]), 4) ]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs."
#
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration(2e-6, [hal_ddg, awg_wfm, awg_wfm2], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
temp = np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)])
arr_exp = round_to_samplerate(awg_wfm, np.sort(np.concatenate( [(650+0)*1e-9 + temp, (650+20+27)*1e-9 + temp])) )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([ arr_exp, arr_exp + np.tile(np.array([20e-9,20e-9]), 4) ]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs."
hal_acq.InputTriggerEdge = 1

#Try adding the MW module to the loop and see what happens
#
#Test it is business as usual if the MW module is just added in Continuous mode
hal_mw.Mode = 'Continuous'
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration(2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
temp = np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)])
arr_exp = round_to_samplerate(awg_wfm, np.sort(np.concatenate( [(650+0)*1e-9 + temp, (650+20+27)*1e-9 + temp])) )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
#
#Test that the MW source is still omitted from calculations if in Continuous mode...
if ENABLE_MANUAL_COMPONENTS:
    expConfig.plot().show()
    input('Press ENTER after verifying MW source does not show up')
#
#Test that the MW source still doesn't arrive on the scene if in PulseModulated mode as no trigger source has been specified...
hal_mw.Mode = 'PulseModulated'
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration(2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
temp = np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)])
arr_exp = round_to_samplerate(awg_wfm, np.sort(np.concatenate( [(650+0)*1e-9 + temp, (650+20+27)*1e-9 + temp])) )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
if ENABLE_MANUAL_COMPONENTS:
    expConfig.plot().show()
    input('Press ENTER after verifying MW source does not show up')
#
#Test that the MW source still arrives on the scene if in PulseModulated mode as a trigger source has been specified...
hal_mw.Mode = 'PulseModulated'
hal_mw.set_trigger_source(awg_wfm.get_output_channel(1).marker(0))
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration(2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
temp = np.array([10e-9, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)])
arr_exp = round_to_samplerate(awg_wfm, np.sort(np.concatenate( [(650+0)*1e-9 + temp, (650+20+27)*1e-9 + temp])) )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
if ENABLE_MANUAL_COMPONENTS:
    expConfig.plot().show()
    input('Press ENTER after verifying MW source shows up')
#
#Test the gated-trigger mode
hal_mw.Mode = 'PulseModulated'
hal_mw.set_trigger_source(awg_wfm.get_output_channel(1).marker(0))
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration(2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_mw)
arr_exp = round_to_samplerate(awg_wfm, np.array([1e-9*(10+20+30+45), 1e-9*(10+(20+30+45)*2+77), 1e-9*(10+(20+30+45)*3+77*3), 1e-9*(10+(20+30+45)*4+77*6)]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + np.array([1,2,3,4])*77e-9]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
#
#Test with active-low gated-trigger mode
instr_fsrc.get_output('CH1').TriggerInputEdge = 0
hal_mw.Mode = 'PulseModulated'
hal_mw.set_trigger_source(awg_wfm.get_output_channel(1).marker(0))
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration(2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_mw)
arr_exp = round_to_samplerate(awg_wfm, np.array([0.0, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + np.array([10+20+30+45,20+30+45,20+30+45,20+30+45])*1e-9]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
instr_fsrc.get_output('CH1').TriggerInputEdge = 1


print("Experiment Configuration Unit Tests completed successfully.")
