from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

#Test cold-reload
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir')
with open("UnitTests/laboratory_configuration.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_instruments(data)
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

print("Laboratory Unit Tests completed successfully.")
