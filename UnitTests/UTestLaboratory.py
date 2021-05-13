from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.ExperimentSpecification import*
from sqdtoolz.Laboratory import*
from sqdtoolz.Experiment import*
import numpy as np
from sqdtoolz.Utilities.FileIO import*
from pathlib import Path

def arr_equality(arr1, arr2):
    if arr1.size != arr2.size:
        return False
    return np.sum(np.abs(arr1 - arr2)) < 1e-15

#Test cold-reload
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
with open("UnitTests/laboratory_configuration.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_labconfig(data)
#
with open("UnitTests/experiment_configurations.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_experiment_configurations(data)
new_lab.CONFIG('testConf').init_instruments()
#
#Check the parameters...
#
assert new_lab.HAL("dum_acq").NumRepetitions == 10, "NumRepetitions incorrectly reloaded into ACQ."
assert new_lab.HAL("dum_acq").NumSegments == 2, "NumSegments incorrectly reloaded into ACQ."
assert new_lab.HAL("dum_acq").NumSamples == 30, "NumSamples incorrectly reloaded into ACQ."
assert new_lab.HAL("dum_acq").SampleRate == 500e6, "SampleRate incorrectly reloaded in ACQ."
assert new_lab.HAL("dum_acq").InputTriggerEdge == 1, "InputTriggerEdge incorrectly reloaded in ACQ."
assert new_lab.HAL("dum_acq").get_trigger_source() == new_lab.HAL("Wfm1").get_output_channel(0).marker(1), "Trigger source incorrectly reloaded in ACQ"
#
assert new_lab.HAL("ddg").RepetitionTime == 83e-9, "RepetitionTime incorrectly set in DDG."
assert new_lab.HAL("ddg").get_trigger_output('A').TrigPulseLength == 10e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('B').TrigPulseLength == 100e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('C').TrigPulseLength == 400e-9, "TrigPulseLength incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('A').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('B').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('C').TrigPulseDelay == 250e-9, "TrigPulseDelay incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('A').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('B').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
assert new_lab.HAL("ddg").get_trigger_output('C').TrigPolarity == 0, "TrigPolarity incorrectly reloaded in DDG."
#
assert new_lab.HAL("MW-Src").Power == 16, "Power incorrectly reloaded in MW-Source."
assert new_lab.HAL("MW-Src").Frequency == 5e9, "Frequency incorrectly reloaded in MW-Source."
assert new_lab.HAL("MW-Src").Phase == 0, "Phase incorrectly reloaded in MW-Source."
assert new_lab.HAL("MW-Src").Mode == 'PulseModulated', "Mode incorrectly reloaded in MW-Source."
#
assert new_lab.HAL("Wfm1").SampleRate == 1e9, "Property incorrectly reloaded in AWG Waveform."
assert new_lab.HAL("Wfm1")._global_factor == 1.0, "Property incorrectly reloaded in AWG Waveform."
assert new_lab.HAL("Wfm1").get_output_channel(0).Amplitude == 1, "Property incorrectly reloaded in AWG Waveform."
assert new_lab.HAL("Wfm1").get_output_channel(1).Offset == 0, "Property incorrectly set in AWG Waveform."
assert new_lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 0.5, "Property incorrectly reloaded in AWG Waveform Segment."
assert new_lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 20e-9, "Property incorrectly reloaded in AWG Waveform Segment."
assert new_lab.HAL("Wfm1").get_waveform_segment('zero11').Value == 0.1, "Property incorrectly reloaded in AWG Waveform Segment."
assert new_lab.HAL("Wfm1").get_waveform_segment('zero22').Duration == 77e-9*3, "Property incorrectly reloaded in AWG Waveform Segment."

#
#Test variables
#
#Create some variables
assert new_lab.VAR("myFreq") == None, "Variable is somehow already in the Laboratory."
assert new_lab.VAR("testAmpl") == None, "Variable is somehow already in the Laboratory."
assert new_lab.VAR("test RepTime") == None, "Variable is somehow already in the Laboratory."
assert new_lab.VAR("myDura1") == None, "Variable is somehow already in the Laboratory."
assert new_lab.VAR("myDura2") == None, "Variable is somehow already in the Laboratory."
assert new_lab.VAR("testSpace") == None, "Variable is somehow already in the Laboratory."
#
VariableInternal('myFreq', new_lab)
new_lab.VAR('myFreq').Value = 5
#Property variable
VariableProperty('test RepTime', new_lab, new_lab.HAL("ddg"), 'RepetitionTime')
new_lab.VAR('test RepTime').Value = 99
#
assert_found = False
try:
    VariableInternal('test RepTime', new_lab)
except AssertionError:
    assert_found = True
    # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
assert assert_found, "Reinstantiation of a variable was possible with a different variable type..."
#
#Deeper property variable...
VariableProperty('testAmpl', new_lab, new_lab.HAL("Wfm1").get_waveform_segment('init0'), 'Amplitude')
new_lab.VAR('testAmpl').Value = 86
#Spaced variable
VariableInternal('myDura1', new_lab)
VariableProperty('myDura2', new_lab, new_lab.HAL("Wfm1").get_waveform_segment('init2'), 'Duration')
VariableSpaced('testSpace', new_lab, 'myDura1', 'myDura2', 3.1415926)
new_lab.VAR('testSpace').Value = 2016
#
#
#Check that they are setting parameters correctly
assert new_lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable."
assert new_lab.VAR("test RepTime").Value == 99, "Property incorrectly set in variable."
assert new_lab.HAL("ddg").RepetitionTime == 99, "Property incorrectly set in variable."
assert new_lab.VAR("testAmpl").Value == 86, "Property incorrectly set in variable."
assert new_lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 86, "Property incorrectly set in variable."
assert new_lab.VAR("testSpace").Value == 2016, "Property incorrectly set in spaced-variable."
assert new_lab.VAR("myDura1").Value == 2016, "Property incorrectly set in spaced-variable."
assert new_lab.VAR("myDura2").Value == 2016+3.1415926, "Property incorrectly set in spaced-variable."
assert new_lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Property incorrectly set in spaced-variable."
#Quickly check reinitialisation behaviour...
VariableInternal('myFreq', new_lab)
assert new_lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable on reinstantiation."
VariableInternal('myFreq', new_lab, 7)
assert new_lab.VAR("myFreq").Value == 7, "Property incorrectly set in variable on reinstantiation."
VariableInternal('myFreq', new_lab, 5)
assert new_lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable on reinstantiation."
VariableInternal('myFreq', new_lab)
assert new_lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable on reinstantiation."
#
#Save the variables to a file
new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration2.txt')
new_lab.save_variables('UnitTests\\')
#
#Change and check said variables once more...
new_lab.VAR('myFreq').Value = 49
new_lab.VAR('testAmpl').Value = 63
new_lab.VAR('test RepTime').Value = 72
new_lab.VAR('testSpace').Value = -45
assert new_lab.VAR("myFreq").Value == 49, "Property incorrectly set in variable."
assert new_lab.VAR("test RepTime").Value == 72, "Property incorrectly set in variable."
assert new_lab.HAL("ddg").RepetitionTime == 72, "Property incorrectly set in variable."
assert new_lab.VAR("testAmpl").Value == 63, "Property incorrectly set in variable."
assert new_lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 63, "Property incorrectly set in variable."
#
assert new_lab.VAR("testSpace").Value == -45, "Property incorrectly set in spaced-variable."
assert new_lab.VAR("myDura1").Value == -45, "Property incorrectly set in spaced-variable."
assert new_lab.VAR("myDura2").Value == -45+3.1415926, "Property incorrectly set in spaced-variable."
assert new_lab.HAL("Wfm1").get_waveform_segment('init2').Duration == -45+3.1415926, "Property incorrectly set in spaced-variable."
#
old_obj_freq = new_lab.VAR("myFreq")
old_obj_ampl = new_lab.VAR("testAmpl")
old_obj_repT = new_lab.VAR("test RepTime")
old_obj_dur1 = new_lab.VAR("myDura1")
old_obj_dur2 = new_lab.VAR("myDura2")
old_obj_varS = new_lab.VAR("testSpace")
#
#
#Check with a warm reload configuration and variables
with open("UnitTests/laboratory_configuration2.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_labconfig(data)
new_lab.update_variables_from_last_expt('UnitTests\\laboratory_parameters.txt')
#
#Check that the variables have been correctly reloaded...
assert new_lab.VAR("myFreq").Value == 5, "Variable incorrectly reloaded."
assert new_lab.VAR("test RepTime").Value == 99, "Variable incorrectly reloaded."
assert new_lab.HAL("ddg").RepetitionTime == 99, "Variable incorrectly reloaded."
assert new_lab.VAR("testAmpl").Value == 86, "Variable incorrectly reloaded."
assert new_lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 86, "Variable incorrectly reloaded."
#
assert new_lab.VAR("myDura1").Value == 2016, "Variable incorrectly reloaded"
assert new_lab.VAR("myDura2").Value == 2016+3.1415926, "Variable incorrectly reloaded"
assert new_lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Variable incorrectly reloaded"
#
#
#Verify new variable objects haven't been created...
assert old_obj_freq == new_lab.VAR("myFreq"), "New variable object has been created when updating from file."
assert old_obj_ampl == new_lab.VAR("testAmpl"), "New variable object has been created when updating from file."
assert old_obj_repT == new_lab.VAR("test RepTime"), "New variable object has been created when updating from file."
assert old_obj_dur1 == new_lab.VAR("myDura1"), "New variable object has been created when updating from file."
assert old_obj_dur2 == new_lab.VAR("myDura2"), "New variable object has been created when updating from file."
assert old_obj_varS == new_lab.VAR("testSpace"), "New variable object has been created when updating from file."


#
#Test WaveformTransformations
#
#Create some variables
assert new_lab.WFMT("IQmod") == None, "WaveformTransformation is somehow already in the Laboratory."
WFMT_ModulationIQ("IQmod", new_lab, 49e6)
#
assert new_lab.WFMT("IQmod").IQFrequency == 49e6, "WaveformTransformation property incorrectly set"
new_lab.WFMT("IQmod").IQFrequency = 84e7
assert new_lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
#
assert new_lab.WFMT("IQmod").IQAmplitude == 1.0, "WaveformTransformation property incorrectly set"
new_lab.WFMT("IQmod").IQAmplitude = 9.4
assert new_lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
#
assert new_lab.WFMT("IQmod").IQAmplitudeFactor == 1.0, "WaveformTransformation property incorrectly set"
new_lab.WFMT("IQmod").IQAmplitudeFactor = 78.1
assert new_lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
#
assert new_lab.WFMT("IQmod").IQPhaseOffset == 0.0, "WaveformTransformation property incorrectly set"
new_lab.WFMT("IQmod").IQPhaseOffset = 54.3
assert new_lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
#
assert new_lab.WFMT("IQmod").IQdcOffset == (0,0), "WaveformTransformation property incorrectly set"
new_lab.WFMT("IQmod").IQdcOffset = (9,1)
assert new_lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
#
assert new_lab.WFMT("IQmod").IQUpperSideband, "WaveformTransformation property incorrectly set"
new_lab.WFMT("IQmod").IQUpperSideband = False
assert new_lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"
#
new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration3.txt')

#
#Check again on a cold reload
#
new_lab._station.close_all_registered_instruments()
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
with open("UnitTests/laboratory_configuration3.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_labconfig(data)
new_lab.update_variables_from_last_expt('UnitTests\\laboratory_parameters.txt')
#
#Check that the variables have been correctly reloaded...
assert new_lab.VAR("myFreq").Value == 5, "Variable incorrectly reloaded."
assert new_lab.VAR("test RepTime").Value == 99, "Variable incorrectly reloaded."
assert new_lab.HAL("ddg").RepetitionTime == 99, "Variable incorrectly reloaded."
assert new_lab.VAR("testAmpl").Value == 86, "Variable incorrectly reloaded."
assert new_lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 86, "Variable incorrectly reloaded."
#
assert new_lab.VAR("myDura1").Value == 2016, "Variable incorrectly reloaded"
assert new_lab.VAR("myDura2").Value == 2016+3.1415926, "Variable incorrectly reloaded"
assert new_lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Variable incorrectly reloaded"
#
assert new_lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"

#
#Check ExperimentSpecifications
#
new_lab.load_instrument('virMWS2')
hal_mw2 = GENmwSource("MW-Src2", new_lab, 'virMWS2', 'CH1')
expConfig = ExperimentConfiguration('testConf4', new_lab, 1.0, [new_lab.HAL('MW-Src'), new_lab.HAL('MW-Src2')], None)
#
ExperimentSpecification('cavity', new_lab)
new_lab.SPEC('cavity').add('Frequency', 0, new_lab.HAL('MW-Src'), 'Frequency')
#
new_lab.HAL('MW-Src').Frequency = 4
expConfig = ExperimentConfiguration('testConf4', new_lab, 1.0, [new_lab.HAL('MW-Src'), new_lab.HAL('MW-Src2')], None, ['cavity'])
assert new_lab.HAL('MW-Src').Frequency == 4, "HAL property incorrectly set."
expConfig.init_instruments()
assert new_lab.HAL('MW-Src').Frequency == 0, "HAL property incorrectly loaded from ExperimentSpecification."
new_lab.SPEC('cavity')['Frequency'] = 5.8
assert new_lab.HAL('MW-Src').Frequency == 0, "HAL property incorrectly set."
expConfig.init_instruments()
assert new_lab.HAL('MW-Src').Frequency == 5.8, "HAL property incorrectly set from the ExperimentSpecification."
new_lab.HAL('MW-Src').Frequency = 5
assert new_lab.HAL('MW-Src').Frequency == 5, "HAL property incorrectly set."
expConfig.init_instruments()
assert new_lab.HAL('MW-Src').Frequency == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
#
expConfig = ExperimentConfiguration('testConf4', new_lab, 1.0, [new_lab.HAL('MW-Src'), new_lab.HAL('MW-Src2')], None, ['cavity'])
VariableProperty('SrcFreq', new_lab, new_lab.HAL("MW-Src"), 'Frequency')
VariableProperty('DncFreq', new_lab, new_lab.HAL("MW-Src2"), 'Frequency')
VariableSpaced('cavFreq', new_lab, 'SrcFreq', 'DncFreq', 3.5)
new_lab.VAR('cavFreq').Value = 15
assert new_lab.VAR('SrcFreq').Value == 15, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 18.5, "HAL property incorrectly set."
new_lab.SPEC('cavity').set_destination('Frequency', new_lab.VAR('cavFreq'))
assert new_lab.VAR('SrcFreq').Value == 15, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 18.5, "HAL property incorrectly set."
expConfig.init_instruments()
assert new_lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
assert new_lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."
new_lab.VAR('DncFreq').Value = 21
assert new_lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 21, "HAL property incorrectly set."
expConfig.init_instruments()
assert new_lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
assert new_lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."
new_lab.VAR('SrcFreq').Value = 24
new_lab.VAR('DncFreq').Value = 21
assert new_lab.VAR('SrcFreq').Value == 24, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 21, "HAL property incorrectly set."
#
new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration4.txt')
new_lab.save_variables('UnitTests\\')
new_lab.save_experiment_configs('UnitTests/', 'experiment_configurations2.txt')
#
#Check with cold-reload...
new_lab._station.close_all_registered_instruments()
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
with open("UnitTests/laboratory_configuration4.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_labconfig(data)
new_lab.update_variables_from_last_expt('UnitTests\\laboratory_parameters.txt')
with open("UnitTests/experiment_configurations2.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_experiment_configurations(data)
#
assert new_lab.VAR('SrcFreq').Value == 24, "HAL property incorrectly set."
assert new_lab.VAR('DncFreq').Value == 21, "HAL property incorrectly set."
assert new_lab.SPEC('cavity')['Frequency'] == 5.8, "Incorrect property loaded into ExperimentSpecification via cold-reload."
new_lab.CONFIG('testConf4').init_instruments()
assert new_lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
assert new_lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."

#
#Check cold-reload on ExperimentConfigurations again with Processors...
#
from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
expConfig = ExperimentConfiguration('testConf4', new_lab, 1.0, [new_lab.HAL('MW-Src'), new_lab.HAL('MW-Src2')], new_lab.HAL('dum_acq'), ['cavity'])
new_proc = ProcessorCPU('cpu_test', new_lab)
new_proc.add_stage(CPU_DDC([0.14]))
new_proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
new_proc.add_stage_end(CPU_Mean('repetition'))
new_lab.HAL("dum_acq").set_data_processor(new_proc)
new_lab.CONFIG('testConf4').save_config()
#
new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration4.txt')
new_lab.save_variables('UnitTests\\')
new_lab.save_experiment_configs('UnitTests/', 'experiment_configurations2.txt')
#
#Check with cold-reload...
new_lab._station.close_all_registered_instruments()
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
with open("UnitTests/laboratory_configuration4.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_labconfig(data)
new_lab.update_variables_from_last_expt('UnitTests\\laboratory_parameters.txt')
with open("UnitTests/experiment_configurations2.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_experiment_configurations(data)
new_lab.PROC('cpu_test').add_stage_end(CPU_Mean('sample'))
new_lab.CONFIG('testConf4').init_instruments()

#
#Check variable sweeps
#
#Check linspace
cur_arr = np.linspace(1,15,14)
m = 0
for cur_val in new_lab.VAR("myFreq").linspace(1,15,14):
    assert cur_val == cur_arr[m], "Variable linspace does not return correct value"
    assert new_lab.VAR("myFreq").Value == cur_arr[m], "Variable linspace does not set correct value"
    m += 1
#Check arange
cur_arr = np.arange(1,15,0.45)
m = 0
for cur_val in new_lab.VAR("myFreq").arange(1,15,0.45):
    assert cur_val == cur_arr[m], "Variable linspace does not return correct value"
    assert new_lab.VAR("myFreq").Value == cur_arr[m], "Variable linspace does not set correct value"
    m += 1
#Check array
cur_arr = np.arange(1,151,0.5)
m = 0
for cur_val in new_lab.VAR("myFreq").array(cur_arr):
    assert cur_val == cur_arr[m], "Variable linspace does not return correct value"
    assert new_lab.VAR("myFreq").Value == cur_arr[m], "Variable linspace does not set correct value"
    m += 1

#
#Check with experiment sweeps
#
new_lab.HAL('dum_acq').set_trigger_source(None)
new_lab.HAL('dum_acq').set_data_processor(None)
ExperimentConfiguration('testConf', new_lab, 1.0, [new_lab.HAL('ddg')], new_lab.HAL('dum_acq'))
#
new_lab.group_open("test_group")
for cur_freq in new_lab.VAR("myFreq").array([1,2,3]):
    for cur_amp in new_lab.VAR("testAmpl").array([4,7,8]):
        exp = Experiment("test", new_lab.CONFIG('testConf'))
        res = new_lab.run_single(exp, delay=1)
new_lab.group_close()
#Check the written data...
amalg_res = FileIODirectory.fromReader(res)
assert arr_equality(amalg_res.param_vals[0], np.array([1,2,3])), "The extracted FileIODirectory object has incorrect right sweeping values."
assert arr_equality(amalg_res.param_vals[1], np.array([4,7,8])), "The extracted FileIODirectory object has incorrect right sweeping values."
assert amalg_res.param_names[0:2] == ["myFreq", "testAmpl"], "The extracted FileIODirectory object has incorrect right sweeping parameter names."

#
#Check again on a complete cold reload
#
new_lab._station.close_all_registered_instruments()
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
new_lab.cold_reload_last_configuration()
#
#Check that the variables have been correctly reloaded...
assert new_lab.VAR("myFreq").Value == 3, "Variable incorrectly reloaded."
assert new_lab.VAR("test RepTime").Value == 99, "Variable incorrectly reloaded."
assert new_lab.HAL("ddg").RepetitionTime == 99, "Variable incorrectly reloaded."
assert new_lab.VAR("testAmpl").Value == 8, "Variable incorrectly reloaded."
assert new_lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 8, "Variable incorrectly reloaded."
#
assert new_lab.VAR("myDura1").Value == 2016, "Variable incorrectly reloaded"
assert new_lab.VAR("myDura2").Value == 2016+3.1415926, "Variable incorrectly reloaded"
assert new_lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Variable incorrectly reloaded"
#
assert new_lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"
#
#
#Check that cold-reloading works even if there are invalid directories...
Path('test_save_dir/3099-09-09/123456-test').mkdir(parents=True, exist_ok=True)
new_lab._station.close_all_registered_instruments()
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
new_lab.cold_reload_last_configuration()
#
#Check that the variables have been correctly reloaded...
assert new_lab.VAR("myFreq").Value == 3, "Variable incorrectly reloaded."
assert new_lab.VAR("test RepTime").Value == 99, "Variable incorrectly reloaded."
assert new_lab.HAL("ddg").RepetitionTime == 99, "Variable incorrectly reloaded."
assert new_lab.VAR("testAmpl").Value == 8, "Variable incorrectly reloaded."
assert new_lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 8, "Variable incorrectly reloaded."
#
assert new_lab.VAR("myDura1").Value == 2016, "Variable incorrectly reloaded"
assert new_lab.VAR("myDura2").Value == 2016+3.1415926, "Variable incorrectly reloaded"
assert new_lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Variable incorrectly reloaded"
#
assert new_lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
assert new_lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"


print("Laboratory Unit Tests completed successfully.")
