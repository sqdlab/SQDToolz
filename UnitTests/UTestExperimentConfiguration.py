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
import unittest

ENABLE_MANUAL_COMPONENTS = False

#######################################################################################################
#######################################TESTING TRIGGER RELATIONS#######################################
#######################################################################################################

new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir')

new_lab.activate_instrument('virACQ')
new_lab.activate_instrument('virDDG')
new_lab.activate_instrument('virAWG')
new_lab.activate_instrument('virMWS')

#Initialise test-modules
hal_acq = ACQ("dum_acq", new_lab, 'virACQ')
hal_ddg = DDG("ddg", new_lab, 'virDDG', )
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
awg_wfm2 = WaveformAWG("Wfm2", new_lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9)
hal_mw = GENmwSource("MW-Src", new_lab, 'virMWS', 'CH1')

#Test reinstantiation does not create something new
hal_ddg.hidden = 'hello'
assert hal_ddg.hidden == 'hello', "Could not plant hidden attribute"
hal_ddg = DDG("ddg", new_lab, 'virDDG')
assert hal_ddg.hidden == 'hello', "Reinstantiation is creating a new object..."
#
hal_acq.hidden = 'hello'
assert hal_acq.hidden == 'hello', "Could not plant hidden attribute"
hal_acq = ACQ("dum_acq", new_lab, 'virACQ')
assert hal_acq.hidden == 'hello', "Reinstantiation is creating a new object..."
#
awg_wfm.hidden = 'hello'
assert awg_wfm.hidden == 'hello', "Could not plant hidden attribute"
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
assert awg_wfm.hidden == 'hello', "Reinstantiation is creating a new object..."
assert_found = False
try:
    WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH4'), ('virAWG', 'CH2')], 1e9)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Reinstantiation was possible with a different channel configuration..."
assert_found = False
try:
    WaveformAWG("Wfm1", new_lab, [('viruAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Reinstantiation was possible with a different channel configuration..."
assert_found = False
try:
    WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH4')], 1e9)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Reinstantiation was possible with a different channel configuration..."
#
hal_mw.hidden = 'hello'
assert hal_mw.hidden == 'hello', "Could not plant hidden attribute"
hal_mw = GENmwSource("MW-Src", new_lab, 'virMWS', 'CH1')
assert hal_mw.hidden == 'hello', "Reinstantiation is creating a new object..."
assert_found = False
try:
    GENmwSource("MW-Src", new_lab, 'virMWS', 'CH2')
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Reinstantiation was possible with a different channel configuration..."


#Test the set_acq_params function
hal_acq.set_acq_params(10,2,30)
assert hal_acq.NumRepetitions == 10, "ACQ HAL did not properly enter the number of repetitions."
assert hal_acq.NumSegments == 2, "ACQ HAL did not properly enter the number of segments."
assert hal_acq.NumSamples == 30, "ACQ HAL did not properly enter the number of samples."
#
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [], hal_acq)

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
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert arr_act_segs.size == 0, "There are erroneous trigger segments found in the current configuration."
#
#Test the case where there is a single trigger relation
#
#Test trivial DDG - should raise assert as it is not TriggerInputCompatible...
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('A'))
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = np.array([50e-9])
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + hal_ddg.get_trigger_output('A').TrigPulseLength]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
#
#Test ACQ again with the same positive input polarity
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('B'))
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_acq)
arr_exp = np.array([50e-9])
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + hal_ddg.get_trigger_output('B').TrigPulseLength]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function."
#
#Test ACQ with negative input polarity
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('C'))
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg], hal_acq)
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
    expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg], hal_acq)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "ExperimentConfiguration failed to trigger an assertion error when omitting a trigger source in the supplied HAL objects."
#
#Simple test feeding the AWG with simple pulse from DDG
hal_acq.set_trigger_source(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('A'))
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm, awg_wfm2], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
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
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_mw)
arr_exp = round_to_samplerate(awg_wfm, np.array([1e-9*(10+20+30+45), 1e-9*(10+(20+30+45)*2+77), 1e-9*(10+(20+30+45)*3+77*3), 1e-9*(10+(20+30+45)*4+77*6)]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + np.array([1,2,3,4])*77e-9]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
#
#Test with active-low gated-trigger mode
new_lab._get_instrument('virMWS').get_output('CH1').TriggerInputEdge = 0
hal_mw.Mode = 'PulseModulated'
hal_mw.set_trigger_source(awg_wfm.get_output_channel(1).marker(0))
hal_acq.set_trigger_source(awg_wfm2.get_output_channel(0).marker(0))
awg_wfm2.set_trigger_source_all(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('C'))
hal_acq.InputTriggerEdge = 0
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
arr_act, arr_act_segs = expConfig.get_trigger_edges(hal_mw)
arr_exp = round_to_samplerate(awg_wfm, np.array([0.0, 1e-9*(10+20+30+45+77), 1e-9*(10+(20+30+45)*2+77*3), 1e-9*(10+(20+30+45)*3+77*6)]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
arr_exp = round_to_samplerate(awg_wfm, np.vstack([arr_exp, arr_exp + np.array([10+20+30+45,20+30+45,20+30+45,20+30+45])*1e-9]).T )
assert arr_equality(arr_act_segs[:,0], arr_exp[:,0]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
assert arr_equality(arr_act_segs[:,1], arr_exp[:,1]), "Incorrect trigger segment intervals returned by the get_trigger_edges function on including 2 AWGs and MW-Source."
hal_acq.InputTriggerEdge = 1
new_lab._get_instrument('virMWS').get_output('CH1').TriggerInputEdge = 1

#
#Test waveform-update and mapping
#
#Try simple example
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
waveform_mapping = WaveformMapper()
waveform_mapping.add_waveform('qubit', 'Wfm1')
waveform_mapping.add_digital('readout', awg_wfm.get_output_channel(0).marker(1))
waveform_mapping.add_digital('sequence', awg_wfm.get_output_channel(1).marker(0))
expConfig.map_waveforms(waveform_mapping)
wfm = WaveformGeneric(['qubit'], ['readout', 'sequence'])
wfm.set_waveform('qubit', [
    WFS_Gaussian("init", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1", None, 30e-9, 0.1),
    WFS_Gaussian("init2", None, 45e-9, 0.5-0.1),
    WFS_Constant("zero2", None, 77e-9, 0.0)
])
wfm.set_digital_segments('readout', 'qubit', ['zero2'])
wfm.set_digital_trigger('sequence', 50e-9)
expConfig.update_waveforms(wfm)
arr_act, arr_act_segs = expConfig.get_trigger_edges(awg_wfm2.get_output_channel(0).marker(0))
arr_exp = round_to_samplerate(awg_wfm, np.array([20e-9+30e-9+45e-9]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges when using waveform mapping."
#
#Try multiple waveforms...
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
waveform_mapping = WaveformMapper()
waveform_mapping.add_waveform('qubit1', 'Wfm1')
waveform_mapping.add_waveform('qubit2', 'Wfm2')
waveform_mapping.add_digital('readout', awg_wfm.get_output_channel(0).marker(1))
waveform_mapping.add_digital('sequence', awg_wfm.get_output_channel(1).marker(0))
expConfig.map_waveforms(waveform_mapping)
wfm = WaveformGeneric(['qubit1', 'qubit2'], ['readout', 'sequence'])
wfm.set_waveform('qubit1', [
    WFS_Gaussian("init", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1", None, 30e-9, 0.1),
    WFS_Gaussian("init2", None, 45e-9, 0.5-0.1),
    WFS_Constant("zero2", None, 77e-9, 0.0)
])
wfm.set_waveform('qubit2', [
    WFS_Gaussian("initX", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1X", None, 30e-9, 0.1),
    WFS_Gaussian("init2X", None, 45e-9, 0.5-0.1),
    WFS_Constant("zero2X", None, 77e-9, 0.0)
])
wfm.set_digital_segments('readout', 'qubit1', ['zero1'])
wfm.set_digital_segments('sequence', 'qubit2', ['init2X'])
expConfig.update_waveforms(wfm)
arr_act, arr_act_segs = expConfig.get_trigger_edges(awg_wfm2.get_output_channel(0).marker(0))
arr_exp = round_to_samplerate(awg_wfm, np.array([20e-9]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges when using waveform mapping on multiple waveforms."
#
#Try multiple waveforms but reference waveform is on another waveform...
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
waveform_mapping = WaveformMapper()
waveform_mapping.add_waveform('qubit1', 'Wfm1')
waveform_mapping.add_waveform('qubit2', 'Wfm2')
waveform_mapping.add_digital('readout', awg_wfm.get_output_channel(0).marker(1))
waveform_mapping.add_digital('sequence', awg_wfm.get_output_channel(1).marker(0))
expConfig.map_waveforms(waveform_mapping)
wfm = WaveformGeneric(['qubit1', 'qubit2'], ['readout', 'sequence'])
wfm.set_waveform('qubit1', [
    WFS_Gaussian("init", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1", None, 30e-9, 0.1),
    WFS_Gaussian("init2", None, 45e-9, 0.5-0.1),
    WFS_Constant("zero2", None, 77e-9, 0.0)
])
wfm.set_waveform('qubit2', [
    WFS_Gaussian("initX", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1X", None, 45e-9, 0.1),
    WFS_Gaussian("init2X", None, 30e-9, 0.5-0.1),
    WFS_Constant("zero2X", None, 77e-9, 0.0)
])
wfm.set_digital_segments('readout', 'qubit2', ['init2X'])
wfm.set_digital_segments('sequence', 'qubit1', ['zero1'])
expConfig.update_waveforms(wfm)
arr_act, arr_act_segs = expConfig.get_trigger_edges(awg_wfm2.get_output_channel(0).marker(0))
arr_exp = round_to_samplerate(awg_wfm, np.array([65e-9]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges when using waveform mapping on multiple waveforms."
#Check the assert triggers if the waveforms are of different size...
wfm.set_waveform('qubit2', [
    WFS_Gaussian("initX", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1X", None, 45e-9, 0.1),
    WFS_Gaussian("init2X", None, 31e-9, 0.5-0.1),
    WFS_Constant("zero2X", None, 77e-9, 0.0)
])
assert_found = False
try:
    expConfig.update_waveforms(wfm)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Function update_waveforms failed to trigger an assertion error when feeding waveforms of different size while demanding reference marker segments amongst each other."
#
#Try with elastic segments and multiple waveforms...
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=200e-9)
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
waveform_mapping = WaveformMapper()
waveform_mapping.add_waveform('qubit1', 'Wfm1')
waveform_mapping.add_waveform('qubit2', 'Wfm2')
waveform_mapping.add_digital('readout', awg_wfm.get_output_channel(0).marker(1))
waveform_mapping.add_digital('sequence', awg_wfm.get_output_channel(1).marker(0))
expConfig.map_waveforms(waveform_mapping)
wfm = WaveformGeneric(['qubit1', 'qubit2'], ['readout', 'sequence'])
wfm.set_waveform('qubit1', [
    WFS_Gaussian("init", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1", None, -1, 0.1),
    WFS_Gaussian("init2", None, 45e-9, 0.5-0.1),
    WFS_Constant("zero2", None, 77e-9, 0.0)
])
wfm.set_waveform('qubit2', [
    WFS_Gaussian("initX", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1X", None, 30e-9, 0.1),
    WFS_Gaussian("init2X", None, 45e-9, 0.5-0.1),
    WFS_Constant("zero2X", None, 77e-9, 0.0)
])
wfm.set_digital_segments('readout', 'qubit1', ['init2'])
wfm.set_digital_segments('sequence', 'qubit1', ['zero2'])
expConfig.update_waveforms(wfm)
arr_act, arr_act_segs = expConfig.get_trigger_edges(awg_wfm2.get_output_channel(0).marker(0))
arr_exp = round_to_samplerate(awg_wfm, np.array([20e-9+58e-9]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges when using an elastic waveform and waveform mapping on multiple waveforms."
#
#Try with elastic segments and multiple waveforms but reference waveform is on another waveform...
awg_wfm = WaveformAWG("Wfm1", new_lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=200e-9)
awg_wfm2 = WaveformAWG("Wfm2", new_lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9, total_time=200e-9)
expConfig = ExperimentConfiguration('testConf', new_lab, 2e-6, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
waveform_mapping = WaveformMapper()
waveform_mapping.add_waveform('qubit1', 'Wfm1')
waveform_mapping.add_waveform('qubit2', 'Wfm2')
waveform_mapping.add_digital('readout', awg_wfm.get_output_channel(0).marker(1))
waveform_mapping.add_digital('sequence', awg_wfm.get_output_channel(1).marker(0))
expConfig.map_waveforms(waveform_mapping)
wfm = WaveformGeneric(['qubit1', 'qubit2'], ['readout', 'sequence'])
wfm.set_waveform('qubit1', [
    WFS_Gaussian("init", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1", None, -1, 0.1),
    WFS_Gaussian("init2", None, 45e-9, 0.5-0.1),
    WFS_Constant("zero2", None, 77e-9, 0.0)
])
wfm.set_waveform('qubit2', [
    WFS_Gaussian("initX", None, 20e-9, 0.5-0.1),
    WFS_Constant("zero1X", None, 45e-9, 0.1),
    WFS_Gaussian("init2X", None, -1, 0.5-0.1),
    WFS_Constant("zero2X", None, 77e-9, 0.0)
])
wfm.set_digital_segments('readout', 'qubit2', ['init2X'])
wfm.set_digital_segments('sequence', 'qubit1', ['zero1'])
expConfig.update_waveforms(wfm)
arr_act, arr_act_segs = expConfig.get_trigger_edges(awg_wfm2.get_output_channel(0).marker(0))
arr_exp = round_to_samplerate(awg_wfm, np.array([65e-9]) + 650e-9 )
assert arr_equality(arr_act, arr_exp), "Incorrect trigger edges when using an elastic waveform and waveform mapping on multiple waveforms."
#Check the assert triggers if the waveforms are of different size...
awg_wfm2 = WaveformAWG("Wfm2", new_lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9, total_time=201e-9)
assert_found = False
try:
    expConfig.update_waveforms(wfm)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Function update_waveforms failed to trigger an assertion error when feeding waveforms of different size while demanding reference marker segments amongst each other."


#########################################################################################################
#######################################TESTING SAVE/LOAD FUNCTIONS#######################################
#########################################################################################################

#Reinitialise test-modules
# hal_acq = ACQ(instr_acq)
# hal_ddg = DDG(instr_ddg)
# awg_wfm = WaveformAWG("Waveform 1", [(instr_awg, 'CH1'), (instr_awg, 'CH2')], 1e9)
# awg_wfm2 = WaveformAWG("Waveform 2", [(instr_awg, 'CH3'), (instr_awg, 'CH4')], 1e9)
# hal_mw = GENmwSource(instr_fsrc.get_output('CH1'))

hal_acq.set_acq_params(10,2,30)
assert hal_acq.NumRepetitions == 10, "ACQ HAL did not properly enter the number of repetitions."
assert hal_acq.NumSegments == 2, "ACQ HAL did not properly enter the number of segments."
assert hal_acq.NumSamples == 30, "ACQ HAL did not properly enter the number of samples."
#
hal_acq.set_trigger_source(None)
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [], hal_acq)
leConfig = expConfig.save_config()

#Reinitialise the waveform
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
hal_acq.set_trigger_source(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('A'))
#
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
hal_acq.SampleRate = 500e6
hal_acq.InputTriggerEdge = 1
#
hal_ddg.RepetitionTime = 83e-9
hal_ddg.set_trigger_output_params('A', 50e-9)
hal_ddg.get_trigger_output('B').TrigPulseLength = 100e-9
hal_ddg.get_trigger_output('B').TrigPulseDelay = 50e-9
hal_ddg.get_trigger_output('B').TrigPolarity = 1
hal_ddg.get_trigger_output('C').TrigPulseLength = 400e-9
hal_ddg.get_trigger_output('C').TrigPulseDelay = 250e-9
hal_ddg.get_trigger_output('C').TrigPolarity = 0
#
hal_mw.Power = 16
hal_mw.Frequency = 5e9
hal_mw.Phase = 0
hal_mw.Mode = 'PulseModulated'
#
#Save and load
leConfig = expConfig.save_config()
expConfig.update_config(leConfig)
#
#If no errors propped up, then try changing parameters and reloading previous parameters...
#
#Testing ACQ
hal_acq.NumRepetitions = 42
hal_acq.NumSegments = 54
hal_acq.NumSamples = 67
hal_acq.SampleRate = 9001
hal_acq.InputTriggerEdge = 0
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('A'))
assert hal_acq.NumRepetitions == 42, "Property incorrectly set in ACQ."
assert hal_acq.NumSegments == 54, "Property incorrectly set in ACQ."
assert hal_acq.NumSamples == 67, "Property incorrectly set in ACQ."
assert hal_acq.SampleRate == 9001, "Property incorrectly set in ACQ."
assert hal_acq.InputTriggerEdge == 0, "Property incorrectly set in ACQ."
assert hal_acq.get_trigger_source() == hal_ddg.get_trigger_output('A'), "Trigger source incorrectly set in ACQ"
expConfig.update_config(leConfig)
assert hal_acq.NumRepetitions == 10, "NumRepetitions incorrectly reloaded into ACQ."
assert hal_acq.NumSegments == 2, "NumSegments incorrectly reloaded into ACQ."
assert hal_acq.NumSamples == 30, "NumSamples incorrectly reloaded into ACQ."
assert hal_acq.SampleRate == 500e6, "SampleRate incorrectly reloaded in ACQ."
assert hal_acq.InputTriggerEdge == 1, "InputTriggerEdge incorrectly reloaded in ACQ."
assert hal_acq.get_trigger_source() == awg_wfm.get_output_channel(0).marker(1), "Trigger source incorrectly reloaded in ACQ"
#
#Testing DDG
hal_ddg.RepetitionTime = 53e-9
hal_ddg.get_trigger_output('A').TrigPulseLength = 420e-9
hal_ddg.get_trigger_output('B').TrigPulseLength = 6e-9
hal_ddg.get_trigger_output('C').TrigPulseLength = 86e-9
hal_ddg.get_trigger_output('A').TrigPulseDelay = 471e-9
hal_ddg.get_trigger_output('B').TrigPulseDelay = 93e-9
hal_ddg.get_trigger_output('C').TrigPulseDelay = 49e-9
hal_ddg.get_trigger_output('A').TrigPolarity = 0
hal_ddg.get_trigger_output('B').TrigPolarity = 0
hal_ddg.get_trigger_output('C').TrigPolarity = 1
assert hal_ddg.RepetitionTime == 53e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseLength == 420e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseLength == 6e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseLength == 86e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseDelay == 471e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseDelay == 93e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseDelay == 49e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPolarity == 0, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('B').TrigPolarity == 0, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('C').TrigPolarity == 1, "Property incorrectly set in DDG."
expConfig.update_config(leConfig)
assert hal_ddg.RepetitionTime == 83e-9, "RepetitionTime incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseLength == 10e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseLength == 100e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseLength == 400e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseDelay == 250e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('A').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('B').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('C').TrigPolarity == 0, "TrigPolarity incorrectly reloaded in DDG."
#
#Testing MWS
hal_mw.Power = 9001
hal_mw.Frequency = 91939
hal_mw.Phase = 73
hal_mw.Mode = 'Continuous'
assert hal_mw.Power == 9001, "Property incorrectly set in MW-Source."
assert hal_mw.Frequency == 91939, "Property incorrectly set in MW-Source."
assert hal_mw.Phase == 73, "Property incorrectly set in MW-Source."
assert hal_mw.Mode == 'Continuous', "Property incorrectly set in MW-Source."
expConfig.update_config(leConfig)
assert hal_mw.Power == 16, "Power incorrectly reloaded in MW-Source."
assert hal_mw.Frequency == 5e9, "Frequency incorrectly reloaded in MW-Source."
assert hal_mw.Phase == 0, "Phase incorrectly reloaded in MW-Source."
assert hal_mw.Mode == 'PulseModulated', "Mode incorrectly reloaded in MW-Source."
#
#Testing AWG
awg_wfm._sample_rate = 49e7
awg_wfm._global_factor = 300
awg_wfm.get_output_channel(0).Amplitude = 5
awg_wfm.get_output_channel(1).Offset = 7
awg_wfm.get_waveform_segment('init0').Amplitude = 9001
awg_wfm.get_waveform_segment('init2').Duration = 40e-9
awg_wfm.get_waveform_segment('zero11').Value = 78
awg_wfm.get_waveform_segment('zero22').Duration = 96
assert awg_wfm.SampleRate == 49e7, "Property incorrectly set in AWG Waveform."
assert awg_wfm._global_factor == 300, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_output_channel(0).Amplitude == 5, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_output_channel(1).Offset == 7, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_waveform_segment('init0').Amplitude == 9001, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('init2').Duration == 40e-9, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero11').Value == 78, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero22').Duration == 96, "Property incorrectly set in AWG Waveform Segment."
expConfig.update_config(leConfig)
assert awg_wfm.SampleRate == 1e9, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm._global_factor == 1.0, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(0).Amplitude == 1, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(1).Offset == 0, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_waveform_segment('init0').Amplitude == 0.5, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('init2').Duration == 20e-9, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero11').Value == 0.1, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero22').Duration == 77e-9*3, "Property incorrectly reloaded in AWG Waveform Segment."
#Run same tests but this time clear the all segments...
awg_wfm.clear_segments()
expConfig.update_config(leConfig)
assert awg_wfm.SampleRate == 1e9, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm._global_factor == 1.0, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(0).Amplitude == 1, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(1).Offset == 0, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_waveform_segment('init0').Amplitude == 0.5, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('init2').Duration == 20e-9, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero11').Value == 0.1, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero22').Duration == 77e-9*3, "Property incorrectly reloaded in AWG Waveform Segment."


##
#Do the same again but with initialisation behavior
##
#
#Reinitialise test-modules
# hal_acq = ACQ(instr_acq)
# hal_ddg = DDG(instr_ddg)
# awg_wfm = WaveformAWG("Waveform 1", [(instr_awg, 'CH1'), (instr_awg, 'CH2')], 1e9)
# awg_wfm2 = WaveformAWG("Waveform 2", [(instr_awg, 'CH3'), (instr_awg, 'CH4')], 1e9)
# hal_mw = GENmwSource(instr_fsrc.get_output('CH1'))
#
hal_acq.set_acq_params(10,2,30)
assert hal_acq.NumRepetitions == 10, "ACQ HAL did not properly enter the number of repetitions."
assert hal_acq.NumSegments == 2, "ACQ HAL did not properly enter the number of segments."
assert hal_acq.NumSamples == 30, "ACQ HAL did not properly enter the number of samples."
#
hal_acq.set_trigger_source(None)
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [], hal_acq)
leConfig = expConfig.save_config()

#Reinitialise the waveform
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
hal_acq.set_trigger_source(awg_wfm.get_output_channel(0).marker(1))
awg_wfm.set_trigger_source_all(hal_ddg.get_trigger_output('A'))
#
expConfig = ExperimentConfiguration('testConf', new_lab, 1.0, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
hal_acq.SampleRate = 500e6
hal_acq.InputTriggerEdge = 1
#
hal_ddg.RepetitionTime = 83e-9
hal_ddg.set_trigger_output_params('A', 50e-9)
hal_ddg.get_trigger_output('B').TrigPulseLength = 100e-9
hal_ddg.get_trigger_output('B').TrigPulseDelay = 50e-9
hal_ddg.get_trigger_output('B').TrigPolarity = 1
hal_ddg.get_trigger_output('C').TrigPulseLength = 400e-9
hal_ddg.get_trigger_output('C').TrigPulseDelay = 250e-9
hal_ddg.get_trigger_output('C').TrigPolarity = 0
#
hal_mw.Power = 16
hal_mw.Frequency = 5e9
hal_mw.Phase = 0
hal_mw.Mode = 'PulseModulated'
#
#If no errors propped up, then try changing parameters and reloading previous parameters...
#
#Testing ACQ
hal_acq.NumRepetitions = 42
hal_acq.NumSegments = 54
hal_acq.NumSamples = 67
hal_acq.SampleRate = 9001
hal_acq.InputTriggerEdge = 0
hal_acq.set_trigger_source(hal_ddg.get_trigger_output('A'))
assert hal_acq.NumRepetitions == 42, "Property incorrectly set in ACQ."
assert hal_acq.NumSegments == 54, "Property incorrectly set in ACQ."
assert hal_acq.NumSamples == 67, "Property incorrectly set in ACQ."
assert hal_acq.SampleRate == 9001, "Property incorrectly set in ACQ."
assert hal_acq.InputTriggerEdge == 0, "Property incorrectly set in ACQ."
assert hal_acq.get_trigger_source() == hal_ddg.get_trigger_output('A'), "Trigger source incorrectly set in ACQ"
expConfig.init_instruments()
assert hal_acq.NumRepetitions == 10, "NumRepetitions incorrectly reloaded into ACQ."
assert hal_acq.NumSegments == 2, "NumSegments incorrectly reloaded into ACQ."
assert hal_acq.NumSamples == 30, "NumSamples incorrectly reloaded into ACQ."
assert hal_acq.SampleRate == 500e6, "SampleRate incorrectly reloaded in ACQ."
assert hal_acq.InputTriggerEdge == 1, "InputTriggerEdge incorrectly reloaded in ACQ."
assert hal_acq.get_trigger_source() == awg_wfm.get_output_channel(0).marker(1), "Trigger source incorrectly reloaded in ACQ"
#
#Testing DDG
hal_ddg.RepetitionTime = 53e-9
hal_ddg.get_trigger_output('A').TrigPulseLength = 420e-9
hal_ddg.get_trigger_output('B').TrigPulseLength = 6e-9
hal_ddg.get_trigger_output('C').TrigPulseLength = 86e-9
hal_ddg.get_trigger_output('A').TrigPulseDelay = 471e-9
hal_ddg.get_trigger_output('B').TrigPulseDelay = 93e-9
hal_ddg.get_trigger_output('C').TrigPulseDelay = 49e-9
hal_ddg.get_trigger_output('A').TrigPolarity = 0
hal_ddg.get_trigger_output('B').TrigPolarity = 0
hal_ddg.get_trigger_output('C').TrigPolarity = 1
assert hal_ddg.RepetitionTime == 53e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseLength == 420e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseLength == 6e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseLength == 86e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseDelay == 471e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseDelay == 93e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseDelay == 49e-9, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPolarity == 0, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('B').TrigPolarity == 0, "Property incorrectly set in DDG."
assert hal_ddg.get_trigger_output('C').TrigPolarity == 1, "Property incorrectly set in DDG."
expConfig.init_instruments()
assert hal_ddg.RepetitionTime == 83e-9, "RepetitionTime incorrectly set in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseLength == 10e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseLength == 100e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseLength == 400e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('A').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('B').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('C').TrigPulseDelay == 250e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('A').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('B').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
assert hal_ddg.get_trigger_output('C').TrigPolarity == 0, "TrigPolarity incorrectly reloaded in DDG."
#
#Testing MWS
hal_mw.Power = 9001
hal_mw.Frequency = 91939
hal_mw.Phase = 73
hal_mw.Mode = 'Continuous'
assert hal_mw.Power == 9001, "Property incorrectly set in MW-Source."
assert hal_mw.Frequency == 91939, "Property incorrectly set in MW-Source."
assert hal_mw.Phase == 73, "Property incorrectly set in MW-Source."
assert hal_mw.Mode == 'Continuous', "Property incorrectly set in MW-Source."
expConfig.init_instruments()
assert hal_mw.Power == 16, "Power incorrectly reloaded in MW-Source."
assert hal_mw.Frequency == 5e9, "Frequency incorrectly reloaded in MW-Source."
assert hal_mw.Phase == 0, "Phase incorrectly reloaded in MW-Source."
assert hal_mw.Mode == 'PulseModulated', "Mode incorrectly reloaded in MW-Source."
#
#Testing AWG
awg_wfm._sample_rate = 49e7
awg_wfm._global_factor = 300
awg_wfm.get_output_channel(0).Amplitude = 5
awg_wfm.get_output_channel(1).Offset = 7
awg_wfm.get_waveform_segment('init0').Amplitude = 9001
awg_wfm.get_waveform_segment('init2').Duration = 40e-9
awg_wfm.get_waveform_segment('zero11').Value = 78
awg_wfm.get_waveform_segment('zero22').Duration = 96
expConfig2 = ExperimentConfiguration('testConf2', new_lab, 1.0, [hal_ddg, awg_wfm, awg_wfm2, hal_mw], hal_acq)
assert awg_wfm.SampleRate == 49e7, "Property incorrectly set in AWG Waveform."
assert awg_wfm._global_factor == 300, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_output_channel(0).Amplitude == 5, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_output_channel(1).Offset == 7, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_waveform_segment('init0').Amplitude == 9001, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('init2').Duration == 40e-9, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero11').Value == 78, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero22').Duration == 96, "Property incorrectly set in AWG Waveform Segment."
expConfig.init_instruments()
assert awg_wfm.SampleRate == 1e9, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm._global_factor == 1.0, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(0).Amplitude == 1, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(1).Offset == 0, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_waveform_segment('init0').Amplitude == 0.5, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('init2').Duration == 20e-9, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero11').Value == 0.1, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero22').Duration == 77e-9*3, "Property incorrectly reloaded in AWG Waveform Segment."
#Run same tests but this time clear the all segments...
awg_wfm.clear_segments()
expConfig.init_instruments()
assert awg_wfm.SampleRate == 1e9, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm._global_factor == 1.0, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(0).Amplitude == 1, "Property incorrectly reloaded in AWG Waveform."
assert awg_wfm.get_output_channel(1).Offset == 0, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_waveform_segment('init0').Amplitude == 0.5, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('init2').Duration == 20e-9, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero11').Value == 0.1, "Property incorrectly reloaded in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero22').Duration == 77e-9*3, "Property incorrectly reloaded in AWG Waveform Segment."
expConfig2.init_instruments()
assert awg_wfm.SampleRate == 49e7, "Property incorrectly set in AWG Waveform."
assert awg_wfm._global_factor == 300, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_output_channel(0).Amplitude == 5, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_output_channel(1).Offset == 7, "Property incorrectly set in AWG Waveform."
assert awg_wfm.get_waveform_segment('init0').Amplitude == 9001, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('init2').Duration == 40e-9, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero11').Value == 78, "Property incorrectly set in AWG Waveform Segment."
assert awg_wfm.get_waveform_segment('zero22').Duration == 96, "Property incorrectly set in AWG Waveform Segment."

new_lab.save_experiment_configs('UnitTests/')

new_lab.save_laboratory_config('UnitTests/')
new_lab.save_experiment_configs('UnitTests/')

print("Experiment Configuration Unit Tests completed successfully.")
