from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*
from sqdtoolz.Experiment import*
from sqdtoolz.Utilities.FileIO import*

from sqdtoolz.Drivers.dummyGENmwSource import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*

from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformMapper import*


from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*

from sqdtoolz.ExperimentSweeps import*

import numpy as np
import shutil
import os.path

import unittest

class TestColdReload(unittest.TestCase):
    def initialise(self):
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab.load_instrument('virACQ')

        #Test the case where an instrument fails initialisation - i.e. load_instrument fails; reloading should call its constructor...
        fname = "test_save_dir/blowup.txt"
        if os.path.isfile(fname):
            os.remove(fname)
        try:
            self.lab.load_instrument('virACQblowup')
        except FileNotFoundError:
            try:
                hal_acq = ACQ("acq_blowup", self.lab, 'virACQblowup')
            except AssertionError:
                f = open(fname, "w")
                f.write("foo")
                f.close()
                self.lab.load_instrument('virACQblowup')
                hal_acq = ACQ("acq_blowup", self.lab, 'virACQblowup')
                #Check constructor ran for 'virACQblowup'...     
                f = open(fname, "r")
                assert f.read() == "foobar", "The constructor for the QCoDeS instrument failed to rerun after failing once"
                f.close()

        self.lab.load_instrument('virDDG')
        self.lab.load_instrument('virAWG')
        self.lab.load_instrument('virMWS')
        self.lab.load_instrument('virMWS2')

        #Initialise test-modules
        hal_acq = ACQ("dum_acq", self.lab, 'virACQ')
        hal_ddg = DDG("ddg", self.lab, 'virDDG', )
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
        awg_wfm2 = WaveformAWG("Wfm2", self.lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9)
        hal_mw = GENmwSource("MW-Src", self.lab, 'virMWS', 'CH1')
        hal_mw2 = GENmwSource("MW-Src2", self.lab, 'virMWS2', 'CH1')

        hal_acq.set_acq_params(10,2,30)
        assert hal_acq.NumRepetitions == 10, "ACQ HAL did not properly enter the number of repetitions."
        assert hal_acq.NumSegments == 2, "ACQ HAL did not properly enter the number of segments."
        assert hal_acq.NumSamples == 30, "ACQ HAL did not properly enter the number of samples."
        #
        hal_acq.set_trigger_source(None)
        expConfig = ExperimentConfiguration('testConf', self.lab, 1.0, [], 'dum_acq')
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
        expConfig = ExperimentConfiguration('testConf', self.lab, 1.0, ['ddg', 'Wfm1', 'Wfm2', 'MW-Src'], 'dum_acq')
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
        expConfig2 = ExperimentConfiguration('testConf2', self.lab, 1.0, ['ddg', 'Wfm1', 'Wfm2', 'MW-Src'], 'dum_acq')
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

        #Test Saving has no errors...
        self.lab.save_experiment_configs('UnitTests/')
        self.lab.save_laboratory_config('UnitTests/')

    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None
        os.remove('UnitTests/experiment_configurations.txt')
        os.remove('UnitTests/laboratory_configuration.txt')
        shutil.rmtree('test_save_dir')

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.sum(np.abs(arr1 - arr2)) < 1e-15
    
    def test_LabAndExpConfigs(self):
        self.initialise()

        #Test cold-reload
        self.lab.release_all_instruments()
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
        with open("UnitTests/laboratory_configuration.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_labconfig(data)
        #
        with open("UnitTests/experiment_configurations.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_experiment_configurations(data)
        self.lab.CONFIG('testConf').init_instruments()

        #
        #Check the parameters...
        #
        assert self.lab.HAL("dum_acq").NumRepetitions == 10, "NumRepetitions incorrectly reloaded into ACQ."
        assert self.lab.HAL("dum_acq").NumSegments == 2, "NumSegments incorrectly reloaded into ACQ."
        assert self.lab.HAL("dum_acq").NumSamples == 30, "NumSamples incorrectly reloaded into ACQ."
        assert self.lab.HAL("dum_acq").SampleRate == 500e6, "SampleRate incorrectly reloaded in ACQ."
        assert self.lab.HAL("dum_acq").InputTriggerEdge == 1, "InputTriggerEdge incorrectly reloaded in ACQ."
        assert self.lab.HAL("dum_acq").get_trigger_source() == self.lab.HAL("Wfm1").get_output_channel(0).marker(1), "Trigger source incorrectly reloaded in ACQ"
        #
        assert self.lab.HAL("ddg").RepetitionTime == 83e-9, "RepetitionTime incorrectly set in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('A').TrigPulseLength == 10e-9, "TrigPulseLength incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('B').TrigPulseLength == 100e-9, "TrigPulseLength incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('C').TrigPulseLength == 400e-9, "TrigPulseLength incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('A').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('B').TrigPulseDelay == 50e-9, "TrigPulseDelay incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('C').TrigPulseDelay == 250e-9, "TrigPulseDelay incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('A').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('B').TrigPolarity == 1, "TrigPolarity incorrectly reloaded in DDG."
        assert self.lab.HAL("ddg").get_trigger_output('C').TrigPolarity == 0, "TrigPolarity incorrectly reloaded in DDG."
        #
        assert self.lab.HAL("MW-Src").Power == 16, "Power incorrectly reloaded in MW-Source."
        assert self.lab.HAL("MW-Src").Frequency == 5e9, "Frequency incorrectly reloaded in MW-Source."
        assert self.lab.HAL("MW-Src").Phase == 0, "Phase incorrectly reloaded in MW-Source."
        assert self.lab.HAL("MW-Src").Mode == 'PulseModulated', "Mode incorrectly reloaded in MW-Source."
        #
        assert self.lab.HAL("Wfm1").SampleRate == 1e9, "Property incorrectly reloaded in AWG Waveform."
        assert self.lab.HAL("Wfm1")._global_factor == 1.0, "Property incorrectly reloaded in AWG Waveform."
        assert self.lab.HAL("Wfm1").get_output_channel(0).Amplitude == 1, "Property incorrectly reloaded in AWG Waveform."
        assert self.lab.HAL("Wfm1").get_output_channel(1).Offset == 0, "Property incorrectly set in AWG Waveform."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 0.5, "Property incorrectly reloaded in AWG Waveform Segment."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 20e-9, "Property incorrectly reloaded in AWG Waveform Segment."
        assert self.lab.HAL("Wfm1").get_waveform_segment('zero11').Value == 0.1, "Property incorrectly reloaded in AWG Waveform Segment."
        assert self.lab.HAL("Wfm1").get_waveform_segment('zero22').Duration == 77e-9*3, "Property incorrectly reloaded in AWG Waveform Segment."

        self.cleanup()

    def test_VARs(self):
        self.initialise()

        #
        #Test variables
        #
        #Create some variables
        assert self.lab.VAR("myFreq") == None, "Variable is somehow already in the Laboratory."
        assert self.lab.VAR("testAmpl") == None, "Variable is somehow already in the Laboratory."
        assert self.lab.VAR("test RepTime") == None, "Variable is somehow already in the Laboratory."
        assert self.lab.VAR("myDura1") == None, "Variable is somehow already in the Laboratory."
        assert self.lab.VAR("myDura2") == None, "Variable is somehow already in the Laboratory."
        assert self.lab.VAR("testSpace") == None, "Variable is somehow already in the Laboratory."
        #
        VariableInternal('myFreq', self.lab)
        self.lab.VAR('myFreq').Value = 5
        #Property variable
        VariableProperty('test RepTime', self.lab, self.lab.HAL("ddg"), 'RepetitionTime')
        self.lab.VAR('test RepTime').Value = 99
        #
        assert_found = False
        try:
            VariableInternal('test RepTime', self.lab)
        except AssertionError:
            assert_found = True
            # assert arr_act.size == 0, "There are erroneous trigger edges found in the current configuration."
        assert assert_found, "Reinstantiation of a variable was possible with a different variable type..."
        #
        #Deeper property variable...
        VariableProperty('testAmpl', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init0'), 'Amplitude')
        self.lab.VAR('testAmpl').Value = 86
        #Spaced variable
        VariableInternal('myDura1', self.lab)
        VariableProperty('myDura2', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init2'), 'Duration')
        VariableSpaced('testSpace', self.lab, 'myDura1', 'myDura2', 3.1415926)
        self.lab.VAR('testSpace').Value = 2016
        #
        #
        #Check that they are setting parameters correctly
        assert self.lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable."
        assert self.lab.VAR("test RepTime").Value == 99, "Property incorrectly set in variable."
        assert self.lab.HAL("ddg").RepetitionTime == 99, "Property incorrectly set in variable."
        assert self.lab.VAR("testAmpl").Value == 86, "Property incorrectly set in variable."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 86, "Property incorrectly set in variable."
        assert self.lab.VAR("testSpace").Value == 2016, "Property incorrectly set in spaced-variable."
        assert self.lab.VAR("myDura1").Value == 2016, "Property incorrectly set in spaced-variable."
        assert self.lab.VAR("myDura2").Value == 2016+3.1415926, "Property incorrectly set in spaced-variable."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Property incorrectly set in spaced-variable."
        #Quickly check reinitialisation behaviour...
        VariableInternal('myFreq', self.lab)
        assert self.lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable on reinstantiation."
        VariableInternal('myFreq', self.lab, 7)
        assert self.lab.VAR("myFreq").Value == 7, "Property incorrectly set in variable on reinstantiation."
        VariableInternal('myFreq', self.lab, 5)
        assert self.lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable on reinstantiation."
        VariableInternal('myFreq', self.lab)
        assert self.lab.VAR("myFreq").Value == 5, "Property incorrectly set in variable on reinstantiation."
        #
        #Save the variables to a file
        self.lab.save_laboratory_config('UnitTests/', 'laboratory_configuration2.txt')
        self.lab.save_variables('UnitTests\\')
        #
        #Change and check said variables once more...
        self.lab.VAR('myFreq').Value = 49
        self.lab.VAR('testAmpl').Value = 63
        self.lab.VAR('test RepTime').Value = 72
        self.lab.VAR('testSpace').Value = -45
        assert self.lab.VAR("myFreq").Value == 49, "Property incorrectly set in variable."
        assert self.lab.VAR("test RepTime").Value == 72, "Property incorrectly set in variable."
        assert self.lab.HAL("ddg").RepetitionTime == 72, "Property incorrectly set in variable."
        assert self.lab.VAR("testAmpl").Value == 63, "Property incorrectly set in variable."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 63, "Property incorrectly set in variable."
        #
        assert self.lab.VAR("testSpace").Value == -45, "Property incorrectly set in spaced-variable."
        assert self.lab.VAR("myDura1").Value == -45, "Property incorrectly set in spaced-variable."
        assert self.lab.VAR("myDura2").Value == -45+3.1415926, "Property incorrectly set in spaced-variable."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init2').Duration == -45+3.1415926, "Property incorrectly set in spaced-variable."
        #
        old_obj_freq = self.lab.VAR("myFreq")
        old_obj_ampl = self.lab.VAR("testAmpl")
        old_obj_repT = self.lab.VAR("test RepTime")
        old_obj_dur1 = self.lab.VAR("myDura1")
        old_obj_dur2 = self.lab.VAR("myDura2")
        old_obj_varS = self.lab.VAR("testSpace")
        #
        #
        #Check with a warm reload configuration and variables
        with open("UnitTests/laboratory_configuration2.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_labconfig(data)
        self.lab.update_variables_from_last_expt('UnitTests/laboratory_parameters.txt')
        #
        #Check that the variables have been correctly reloaded...
        assert self.lab.VAR("myFreq").Value == 5, "Variable incorrectly reloaded."
        assert self.lab.VAR("test RepTime").Value == 99, "Variable incorrectly reloaded."
        assert self.lab.HAL("ddg").RepetitionTime == 99, "Variable incorrectly reloaded."
        assert self.lab.VAR("testAmpl").Value == 86, "Variable incorrectly reloaded."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 86, "Variable incorrectly reloaded."
        #
        assert self.lab.VAR("myDura1").Value == 2016, "Variable incorrectly reloaded"
        assert self.lab.VAR("myDura2").Value == 2016+3.1415926, "Variable incorrectly reloaded"
        assert self.lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Variable incorrectly reloaded"
        #
        #
        #Verify new variable objects haven't been created...
        assert old_obj_freq == self.lab.VAR("myFreq"), "New variable object has been created when updating from file."
        assert old_obj_ampl == self.lab.VAR("testAmpl"), "New variable object has been created when updating from file."
        assert old_obj_repT == self.lab.VAR("test RepTime"), "New variable object has been created when updating from file."
        assert old_obj_dur1 == self.lab.VAR("myDura1"), "New variable object has been created when updating from file."
        assert old_obj_dur2 == self.lab.VAR("myDura2"), "New variable object has been created when updating from file."
        assert old_obj_varS == self.lab.VAR("testSpace"), "New variable object has been created when updating from file."
        #
        #
        #
        #Test with DDG's different scheme...
        VariableProperty('myDura2', self.lab, self.lab.HAL("ddg").get_trigger_output('A'), 'TrigPulseLength')
        self.lab.VAR('myDura2').Value = 48.5
        assert self.lab.HAL("ddg").get_trigger_output('A').TrigPulseLength == 48.5, "DDG parameter was incorrectly set by VariableProperty."

        os.remove('UnitTests/laboratory_configuration2.txt')
        os.remove('UnitTests/laboratory_parameters.txt')
        self.cleanup()

    def test_WFMTs(self):
        self.initialise()
        #
        #Test WaveformTransformations
        #
        #Create some variables
        assert self.lab.WFMT("IQmod") == None, "WaveformTransformation is somehow already in the Laboratory."
        WFMT_ModulationIQ("IQmod", self.lab, 49e6)
        #
        assert self.lab.WFMT("IQmod").IQFrequency == 49e6, "WaveformTransformation property incorrectly set"
        self.lab.WFMT("IQmod").IQFrequency = 84e7
        assert self.lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
        #
        assert self.lab.WFMT("IQmod").IQAmplitude == 1.0, "WaveformTransformation property incorrectly set"
        self.lab.WFMT("IQmod").IQAmplitude = 9.4
        assert self.lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
        #
        assert self.lab.WFMT("IQmod").IQAmplitudeFactor == 1.0, "WaveformTransformation property incorrectly set"
        self.lab.WFMT("IQmod").IQAmplitudeFactor = 78.1
        assert self.lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
        #
        assert self.lab.WFMT("IQmod").IQPhaseOffset == 0.0, "WaveformTransformation property incorrectly set"
        self.lab.WFMT("IQmod").IQPhaseOffset = 54.3
        assert self.lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
        #
        assert self.lab.WFMT("IQmod").IQdcOffset == (0,0), "WaveformTransformation property incorrectly set"
        self.lab.WFMT("IQmod").IQdcOffset = (9,1)
        assert self.lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
        #
        assert self.lab.WFMT("IQmod").IQUpperSideband, "WaveformTransformation property incorrectly set"
        self.lab.WFMT("IQmod").IQUpperSideband = False
        assert self.lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"
        #
        self.lab.save_laboratory_config('UnitTests/', 'laboratory_configuration3.txt')
        #
        #Check again on a cold reload
        #
        self.lab.release_all_instruments()
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
        with open("UnitTests/laboratory_configuration3.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_labconfig(data)
        #
        assert self.lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"

        os.remove('UnitTests/laboratory_configuration3.txt')
        self.cleanup()

    def test_SPECs(self):
        self.initialise()
        #
        #Check ExperimentSpecifications
        #
        expConfig = ExperimentConfiguration('testConf4', self.lab, 1.0, ['MW-Src', 'MW-Src2'], None)
        #
        ExperimentSpecification('cavityFile', self.lab, 'Cavity').commit_entries()
        ExperimentSpecification('cavity', self.lab)
        self.lab.SPEC('cavity').add('Frequency', 0, self.lab.HAL('MW-Src'), 'Frequency')
        #
        self.lab.HAL('MW-Src').Frequency = 4
        expConfig = ExperimentConfiguration('testConf4', self.lab, 1.0, ['MW-Src', 'MW-Src2'], None, ['cavity'])
        assert self.lab.HAL('MW-Src').Frequency == 4, "HAL property incorrectly set."
        expConfig.init_instruments()
        assert self.lab.HAL('MW-Src').Frequency == 0, "HAL property incorrectly loaded from ExperimentSpecification."
        self.lab.SPEC('cavity')['Frequency'].Value = 5.8
        assert self.lab.HAL('MW-Src').Frequency == 0, "HAL property incorrectly set."
        expConfig.init_instruments()
        assert self.lab.HAL('MW-Src').Frequency == 5.8, "HAL property incorrectly set from the ExperimentSpecification."
        self.lab.HAL('MW-Src').Frequency = 5
        assert self.lab.HAL('MW-Src').Frequency == 5, "HAL property incorrectly set."
        expConfig.init_instruments()
        assert self.lab.HAL('MW-Src').Frequency == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
        #
        #Following construct is used to track how many times a given parameter is set...
        prev_func = GENmwSource.Frequency.fset
        def freq_func(self, val):
            if not hasattr(self, 'num_set_freq'):
                self.num_set_freq = 0
            self.num_set_freq += 1
            prev_func(self, val)
        GENmwSource.Frequency = property(GENmwSource.Frequency.fget, freq_func)
        #
        expConfig = ExperimentConfiguration('testConf4', self.lab, 1.0, ['MW-Src', 'MW-Src2'], None, ['cavity'])
        VariableProperty('SrcFreq', self.lab, self.lab.HAL("MW-Src"), 'Frequency')
        VariableProperty('DncFreq', self.lab, self.lab.HAL("MW-Src2"), 'Frequency')
        VariableSpaced('cavFreq', self.lab, 'SrcFreq', 'DncFreq', 3.5)
        self.lab.VAR('cavFreq').Value = 15
        assert self.lab.VAR('SrcFreq').Value == 15, "HAL property incorrectly set."
        assert self.lab.VAR('DncFreq').Value == 18.5, "HAL property incorrectly set."
        self.lab.SPEC('cavity').set_destination('Frequency', self.lab.VAR('cavFreq'))
        assert self.lab.VAR('SrcFreq').Value == 15, "HAL property incorrectly set."
        assert self.lab.VAR('DncFreq').Value == 18.5, "HAL property incorrectly set."
        assert self.lab.HAL('MW-Src').num_set_freq == 1, "HAL got set more times than expected."
        assert self.lab.HAL('MW-Src2').num_set_freq == 1, "HAL got set more times than expected."
        expConfig.init_instruments()
        assert self.lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
        assert self.lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."
        assert self.lab.HAL('MW-Src').num_set_freq == 2, "HAL got set more times than expected."
        assert self.lab.HAL('MW-Src2').num_set_freq == 2, "HAL got set more times than expected."
        self.lab.VAR('DncFreq').Value = 21
        assert self.lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly set."
        assert self.lab.VAR('DncFreq').Value == 21, "HAL property incorrectly set."
        assert self.lab.HAL('MW-Src').num_set_freq == 2, "HAL got set more times than expected."
        assert self.lab.HAL('MW-Src2').num_set_freq == 3, "HAL got set more times than expected."
        expConfig.init_instruments()
        assert self.lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
        assert self.lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."
        assert self.lab.HAL('MW-Src').num_set_freq == 3, "HAL got set more times than expected."
        assert self.lab.HAL('MW-Src2').num_set_freq == 4, "HAL got set more times than expected."
        self.lab.VAR('SrcFreq').Value = 24
        self.lab.VAR('DncFreq').Value = 21
        assert self.lab.VAR('SrcFreq').Value == 24, "HAL property incorrectly set."
        assert self.lab.VAR('DncFreq').Value == 21, "HAL property incorrectly set."
        assert self.lab.HAL('MW-Src').num_set_freq == 4, "HAL got set more times than expected."
        assert self.lab.HAL('MW-Src2').num_set_freq == 5, "HAL got set more times than expected."
        #
        self.lab.save_laboratory_config('UnitTests/', 'laboratory_configuration4.txt')
        self.lab.save_variables('UnitTests\\')
        self.lab.save_experiment_configs('UnitTests/', 'experiment_configurations2.txt')
        #
        #Check with cold-reload...
        self.lab.release_all_instruments()
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
        with open("UnitTests/laboratory_configuration4.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_labconfig(data)
        self.lab.update_variables_from_last_expt('UnitTests/laboratory_parameters.txt')
        with open("UnitTests/experiment_configurations2.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_experiment_configurations(data)
        #
        assert self.lab.VAR('SrcFreq').Value == 24, "HAL property incorrectly set."
        assert self.lab.VAR('DncFreq').Value == 21, "HAL property incorrectly set."
        assert self.lab.SPEC('cavity')['Frequency'].Value == 5.8, "Incorrect property loaded into ExperimentSpecification via cold-reload."
        self.lab.CONFIG('testConf4').init_instruments()
        assert self.lab.VAR('SrcFreq').Value == 5.8, "HAL property incorrectly loaded from ExperimentSpecification."
        assert self.lab.VAR('DncFreq').Value == 9.3, "HAL property incorrectly loaded from ExperimentSpecification."

        os.remove('UnitTests/experiment_configurations2.txt')
        os.remove('UnitTests/laboratory_configuration4.txt')
        os.remove('UnitTests/laboratory_parameters.txt')
        self.cleanup()

    def test_PROCs(self):
        self.initialise()
        #TODO: Include more PROC types as they ahve evolved now...
        #
        #Check cold-reload on ExperimentConfigurations again with Processors...
        #
        expConfig = ExperimentConfiguration('testConf4', self.lab, 1.0, ['MW-Src', 'MW-Src2'], 'dum_acq', ['cavity'])
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.add_stage(CPU_DDC([0.14]))
        new_proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
        new_proc.add_stage_end(CPU_Mean('repetition'))
        self.lab.HAL("dum_acq").set_data_processor(new_proc)
        new_proc = ProcessorCPU('cpu_test2', self.lab)
        new_proc.add_stage(CPU_DDC([0.14]))
        new_proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
        new_proc.add_stage_end(CPU_Mean('repetition'))
        new_proc = ProcessorCPU('cpu_test3', self.lab)
        new_proc.add_stage(CPU_DDC([0.14]))
        new_proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
        new_proc.add_stage_end(CPU_Mean('repetition'))
        self.lab.HAL("dum_acq").set_extra_post_processors([self.lab.PROC('cpu_test2'), self.lab.PROC('cpu_test3')])
        self.lab.CONFIG('testConf4').save_config()
        #
        self.lab.save_laboratory_config('UnitTests/', 'laboratory_configuration4.txt')
        self.lab.save_variables('UnitTests\\')
        self.lab.save_experiment_configs('UnitTests/', 'experiment_configurations2.txt')
        #
        #Check with cold-reload...
        self.lab.release_all_instruments()
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
        with open("UnitTests/laboratory_configuration4.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_labconfig(data)
        self.lab.update_variables_from_last_expt('UnitTests/laboratory_parameters.txt')
        with open("UnitTests/experiment_configurations2.txt") as json_file:
            data = json.load(json_file)
            self.lab.cold_reload_experiment_configurations(data)
        self.lab.PROC('cpu_test').add_stage_end(CPU_Mean('sample'))
        self.lab.CONFIG('testConf4').init_instruments()

        os.remove('UnitTests/experiment_configurations2.txt')
        os.remove('UnitTests/laboratory_configuration4.txt')
        os.remove('UnitTests/laboratory_parameters.txt')
        self.cleanup()


class TestSweeps(unittest.TestCase):
    def initialise(self):
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab.load_instrument('virACQ')
        self.lab.load_instrument('virDDG')
        self.lab.load_instrument('virAWG')
        self.lab.load_instrument('virMWS')
        self.lab.load_instrument('virMWS2')
        self.lab.load_instrument('virSMU')

        #Initialise test-modules
        hal_acq = ACQ("dum_acq", self.lab, 'virACQ')
        hal_ddg = DDG("ddg", self.lab, 'virDDG', )
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
        hal_mw = GENmwSource("MW-Src", self.lab, 'virMWS', 'CH1')
        hal_mw2 = GENmwSource("MW-Src2", self.lab, 'virMWS2', 'CH1')
        hal_smu = GENsmu('SMU', self.lab, 'virSMU')

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

        expConfig = ExperimentConfiguration('testConf', self.lab, 1.0, ['ddg', 'Wfm1', 'MW-Src'], 'dum_acq')

        VariableInternal('myFreq', self.lab)
        VariableProperty('testAmpl', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init0'), 'Amplitude')
        self.lab.VAR('testAmpl').Value = 86
        VariableProperty('test RepTime', self.lab, self.lab.HAL("ddg"), 'RepetitionTime')
        self.lab.VAR('test RepTime').Value = 99
        VariableInternal('myDura1', self.lab)
        self.lab.VAR('myDura1').Value = 2016
        VariableProperty('myDura2', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init2'), 'Duration')
        VariableSpaced('testSpace', self.lab, 'myDura1', 'myDura2', 3.1415926)
        self.lab.VAR('testSpace').Value = 2016

        WFMT_ModulationIQ("IQmod", self.lab, 49e6)
        self.lab.WFMT("IQmod").IQFrequency = 84e7
        self.lab.WFMT("IQmod").IQAmplitude = 9.4
        self.lab.WFMT("IQmod").IQAmplitudeFactor = 78.1
        self.lab.WFMT("IQmod").IQPhaseOffset = 54.3
        self.lab.WFMT("IQmod").IQdcOffset = (9,1)
        self.lab.WFMT("IQmod").IQUpperSideband = False

    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.sum(np.abs(arr1 - arr2)) < 1e-15

    def test_VarSweep(self):
        self.initialise()

        #
        #Check variable sweeps
        #
        #Check linspace
        cur_arr = np.linspace(1,15,14)
        m = 0
        for cur_val in self.lab.VAR("myFreq").linspace(1,15,14):
            assert cur_val == cur_arr[m], "Variable linspace does not return correct value"
            assert self.lab.VAR("myFreq").Value == cur_arr[m], "Variable linspace does not set correct value"
            m += 1
        #Check arange
        cur_arr = np.arange(1,15,0.45)
        m = 0
        for cur_val in self.lab.VAR("myFreq").arange(1,15,0.45):
            assert cur_val == cur_arr[m], "Variable linspace does not return correct value"
            assert self.lab.VAR("myFreq").Value == cur_arr[m], "Variable linspace does not set correct value"
            m += 1
        #Check array
        cur_arr = np.arange(1,151,0.5)
        m = 0
        for cur_val in self.lab.VAR("myFreq").array(cur_arr):
            assert cur_val == cur_arr[m], "Variable linspace does not return correct value"
            assert self.lab.VAR("myFreq").Value == cur_arr[m], "Variable linspace does not set correct value"
            m += 1
        
        shutil.rmtree('test_save_dir')
        self.cleanup()

    def test_Exp(self):
        self.initialise()
        
        #Check out recorded parameter storage
        #
        #Check basic parameter storage with VARs
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1))], delay=1, rec_params=[self.lab.VAR('myFreq'), self.lab.VAR('testAmpl')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,2]))
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[5,0],[5,1],[5,2]]))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1))
        #
        #Check basic parameter storage with a WFMT
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1))], delay=1, rec_params=[(self.lab.WFMT("IQmod"), 'IQFrequency'), self.lab.VAR('testAmpl')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,2]))
        val = self.lab.WFMT("IQmod").IQFrequency
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[val,0],[val,1],[val,2]]))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1))
        #
        #Check basic parameter storage with a HAL and 2D sweep
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1)), (self.lab.VAR('test RepTime'), np.linspace(9,12,4))], rec_params=[(self.lab.WFMT("IQmod"), 'IQFrequency'), (self.lab.HAL("MW-Src"), 'Power')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,4,2]))
        val = self.lab.WFMT("IQmod").IQFrequency
        val2 = self.lab.HAL("MW-Src").Power
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[[val,val2]]*4]*3))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[1]), np.linspace(9,12,4))
        #
        #Check case when there are no sweeping points
        time.sleep(1)   #Otherwise it writes to the same file as the previous test...
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, rec_params=[(self.lab.WFMT("IQmod"), 'IQFrequency'), (self.lab.HAL("MW-Src"), 'Power'), (self.lab.HAL("Wfm1").get_waveform_segment('init0'), 'Duration')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3]))
        val = self.lab.WFMT("IQmod").IQFrequency
        val2 = self.lab.HAL("MW-Src").Power
        val3 = self.lab.HAL("Wfm1").get_waveform_segment('init0').Duration
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([val,val2,val3]))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals), np.array([]))

        #Check Experiment sweep_vars don't accept empty arrays...
        time.sleep(1)   #Otherwise it writes to the same file as the previous test...
        self.lab.VAR('myDura2').Value = 1e-9
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,10,1))], delay=1)
        res.release()
        #
        assert_found = False
        try:
            exp = Experiment("test", self.lab.CONFIG('testConf'))
            res = self.lab.run_single(exp, (self.lab.VAR("testAmpl"), np.arange(0,2,1)), delay=1)
        except AssertionError:
            assert_found = True
        assert assert_found, "Experiment class did not catch an error when incorrectly passing a sweeping-variables without a list bracket..."
        #
        assert_found = False
        try:
            exp = Experiment("test", self.lab.CONFIG('testConf'))
            res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), [1,2,3])], delay=1)
        except AssertionError:
            assert_found = True
        assert assert_found, "Experiment class did not catch an error when passing a sweeping-variable with a non-numpy array..."
        #
        assert_found = False
        try:
            exp = Experiment("test", self.lab.CONFIG('testConf'))
            res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,-1,1))], delay=1)
        except AssertionError:
            assert_found = True
        assert assert_found, "Experiment class did not catch an error when passing a sweeping-variable with an empty list..."

        shutil.rmtree('test_save_dir')
        self.cleanup()


    def test_ExpReverseSweep(self):
        self.initialise()
        
        #Check basic parameter storage with 1D reverse sweep...
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1))], delay=0.1, reverse_index=0, rec_params=[self.lab.VAR('myFreq'), self.lab.VAR('testAmpl')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,4])), "Reverse sweeping experiment in 1D did not produce the right number of dependent parameters."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[5,0]*2,[5,1]*2,[5,2]*2])), "Reverse sweeping experiment in 1D did not store the correct data."
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1)), "Reverse sweeping experiment in 1D did not produce the right parameter values."
        #
        #Check basic parameter storage with 1D reverse sweep...
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 2
        self.lab.UpdateStateEnabled = False
        self.lab.HAL('SMU').Voltage = 0
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1))], delay=0.1, reverse_index=0, rec_params=[self.lab.VAR('myFreq'), self.lab.VAR('testAmpl'), (self.lab.HAL('SMU'), 'Voltage')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        arr = exp.last_rec_params.get_numpy_array()
        assert self.arr_equality(np.array(arr.shape), np.array([3,6])), "Reverse sweeping experiment in 1D did not produce the right number of dependent parameters."
        assert self.arr_equality(np.array(arr[:,0:2]), np.array([[2,0],[2,1],[2,2]])), "Reverse sweeping experiment in 1D did not store the correct data."
        assert self.arr_equality(np.array(arr[:,3:5]), np.array([[2,0],[2,1],[2,2]])), "Reverse sweeping experiment in 1D did not store the correct data."
        assert self.arr_equality(np.diff(np.concatenate([arr[:,2], arr[:,5][::-1]])), np.ones(5)), "Reverse sweeping experiment in 1D did not store the data in correct order."
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1)), "Reverse sweeping experiment in 1D did not produce the right parameter values."
        #
        #Check basic parameter storage with 2D reverse sweep...
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 2
        self.lab.UpdateStateEnabled = False
        self.lab.HAL('SMU').Voltage = 0
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1)), (self.lab.VAR("myFreq"), np.arange(1,5,1))], delay=0.1, reverse_index=0, rec_params=[self.lab.VAR('myFreq'), self.lab.VAR('testAmpl'), (self.lab.HAL('SMU'), 'Voltage')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        arr = exp.last_rec_params.get_numpy_array()
        assert self.arr_equality(np.array(arr.shape), np.array([3,4,6])), "Reverse sweeping experiment in 1D did not produce the right number of dependent parameters."
        assert self.arr_equality(np.array(arr[:,:,0:2]), np.array([[[1,0],[2,0],[3,0],[4,0]], [[1,1],[2,1],[3,1],[4,1]], [[1,2],[2,2],[3,2],[4,2]]])), "Reverse sweeping experiment in 1D did not store the correct data."
        assert self.arr_equality(np.array(arr[:,:,3:5]), np.array([[[1,0],[2,0],[3,0],[4,0]], [[1,1],[2,1],[3,1],[4,1]], [[1,2],[2,2],[3,2],[4,2]]])), "Reverse sweeping experiment in 1D did not store the correct data."
        assert self.arr_equality(np.diff(np.concatenate([np.ndarray.flatten(arr[:,:,2]), np.ndarray.flatten(arr[:,:,5][::-1])])), np.ones(23)), "Reverse sweeping experiment in 1D did not store the data in correct order."
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1)), "Reverse sweeping experiment in 1D did not produce the right parameter values."
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[1]), np.arange(1,5,1)), "Reverse sweeping experiment in 1D did not produce the right parameter values."
        #
        #Check basic parameter storage with 2D reverse sweep...
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 2
        self.lab.UpdateStateEnabled = False
        self.lab.HAL('SMU').Voltage = 0
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1)), (self.lab.VAR("myFreq"), np.arange(1,5,1))], delay=0.1, reverse_index=1, rec_params=[self.lab.VAR('myFreq'), self.lab.VAR('testAmpl'), (self.lab.HAL('SMU'), 'Voltage')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        arr = exp.last_rec_params.get_numpy_array()
        assert self.arr_equality(np.array(arr.shape), np.array([3,4,6])), "Reverse sweeping experiment in 1D did not produce the right number of dependent parameters."
        assert self.arr_equality(np.array(arr[:,:,0:2]), np.array([[[1,0],[2,0],[3,0],[4,0]], [[1,1],[2,1],[3,1],[4,1]], [[1,2],[2,2],[3,2],[4,2]]])), "Reverse sweeping experiment in 1D did not store the correct data."
        assert self.arr_equality(np.array(arr[:,:,3:5]), np.array([[[1,0],[2,0],[3,0],[4,0]], [[1,1],[2,1],[3,1],[4,1]], [[1,2],[2,2],[3,2],[4,2]]])), "Reverse sweeping experiment in 1D did not store the correct data."
        assert self.arr_equality(np.diff(np.ndarray.flatten(np.concatenate([(arr[x,:,2], arr[x,:,5][::-1]) for x in range(3)]))), np.ones(23)), "Reverse sweeping experiment in 1D did not store the data in correct order."
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1)), "Reverse sweeping experiment in 1D did not produce the right parameter values."
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[1]), np.arange(1,5,1)), "Reverse sweeping experiment in 1D did not produce the right parameter values."


        shutil.rmtree('test_save_dir')
        self.cleanup()


    def test_ExpSweepAndFullColdReload(self):
        self.initialise()

        #
        #Check with experiment sweeps
        #
        self.lab.HAL('dum_acq').set_trigger_source(None)
        self.lab.HAL('dum_acq').set_data_processor(None)
        self.lab.HAL('ddg').get_trigger_output('A').TrigPulseLength = 10e-8
        ExperimentConfiguration('testConf', self.lab, 1.0, ['ddg'], 'dum_acq')
        #
        reslts = []
        self.lab.group_open("test_group")
        for cur_freq in self.lab.VAR("myFreq").array([1,2,3]):
            for cur_amp in self.lab.VAR("testAmpl").array([4,7,8]):
                exp = Experiment("test", self.lab.CONFIG('testConf'))
                reslts += [ self.lab.run_single(exp, delay=1) ]
        self.lab.group_close()
        #Check the written data...
        for res in reslts[:-1]:
            res.release()
        res = reslts[-1]
        amalg_res = FileIODirectory.fromReader(res)
        assert self.arr_equality(amalg_res.param_vals[0], np.array([1,2,3])), "The extracted FileIODirectory object has incorrect right sweeping values."
        assert self.arr_equality(amalg_res.param_vals[1], np.array([4,7,8])), "The extracted FileIODirectory object has incorrect right sweeping values."
        assert amalg_res.param_names[0:2] == ["myFreq", "testAmpl"], "The extracted FileIODirectory object has incorrect right sweeping parameter names."
        #Test time-stamps are spaced appropriately...
        ts = amalg_res.get_time_stamps()
        ts_exps = []
        for m in np.arange(3):
            for n in np.arange(3):
                ts_exps += [ ts[m][n][0][0][0] ]
        assert np.sum(np.diff(ts_exps)/1e6) >= 8, "The time-stamps do not differ by at least 1s per experimental trace."
        res.release()

        #
        #Check again on a complete cold reload
        #
        self.lab.release_all_instruments()
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
        self.lab.cold_reload_last_configuration()
        #
        #Check that the variables have been correctly reloaded...
        assert self.lab.VAR("myFreq").Value == 3, "Variable incorrectly reloaded."
        assert self.lab.VAR("test RepTime").Value == 99, "Variable incorrectly reloaded."
        assert self.lab.HAL("ddg").RepetitionTime == 99, "Variable incorrectly reloaded."
        assert self.lab.VAR("testAmpl").Value == 8, "Variable incorrectly reloaded."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 8, "Variable incorrectly reloaded."
        #
        assert self.lab.VAR("myDura1").Value == 2016, "Variable incorrectly reloaded"
        assert self.lab.VAR("myDura2").Value == 2016+3.1415926, "Variable incorrectly reloaded"
        assert self.lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Variable incorrectly reloaded"
        #
        assert self.lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"
        #
        #
        #Check that cold-reloading works even if there are invalid directories...
        Path('test_save_dir/3099-09-09/123456-test').mkdir(parents=True, exist_ok=True)
        self.lab.release_all_instruments()
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')
        self.lab.cold_reload_last_configuration()
        #
        #Check that the variables have been correctly reloaded...
        assert self.lab.VAR("myFreq").Value == 3, "Variable incorrectly reloaded."
        assert self.lab.VAR("test RepTime").Value == 99, "Variable incorrectly reloaded."
        assert self.lab.HAL("ddg").RepetitionTime == 99, "Variable incorrectly reloaded."
        assert self.lab.VAR("testAmpl").Value == 8, "Variable incorrectly reloaded."
        assert self.lab.HAL("Wfm1").get_waveform_segment('init0').Amplitude == 8, "Variable incorrectly reloaded."
        #
        assert self.lab.VAR("myDura1").Value == 2016, "Variable incorrectly reloaded"
        assert self.lab.VAR("myDura2").Value == 2016+3.1415926, "Variable incorrectly reloaded"
        assert self.lab.HAL("Wfm1").get_waveform_segment('init2').Duration == 2016+3.1415926, "Variable incorrectly reloaded"
        #
        assert self.lab.WFMT("IQmod").IQFrequency == 84e7, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQAmplitude == 9.4, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQAmplitudeFactor == 78.1, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQPhaseOffset == 54.3, "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQdcOffset == (9,1), "WaveformTransformation property incorrectly set"
        assert self.lab.WFMT("IQmod").IQUpperSideband == False, "WaveformTransformation property incorrectly set"

        shutil.rmtree('test_save_dir')
        self.cleanup()

class TestExpFeatures(unittest.TestCase):
    def initialise(self):
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab.load_instrument('virACQ')
        self.lab.load_instrument('virDDG')
        self.lab.load_instrument('virAWG')
        self.lab.load_instrument('virMWS')
        self.lab.load_instrument('virMWS2')

        #Initialise test-modules
        hal_acq = ACQ("dum_acq", self.lab, 'virACQ')
        hal_ddg = DDG("ddg", self.lab, 'virDDG', )
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
        hal_mw = GENmwSource("MW-Src", self.lab, 'virMWS', 'CH1')
        hal_mw2 = GENmwSource("MW-Src2", self.lab, 'virMWS2', 'CH1')

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

        expConfig = ExperimentConfiguration('testConf', self.lab, 1.0, ['ddg', 'Wfm1', 'MW-Src'], 'dum_acq')
        expConfig = ExperimentConfiguration('testConf2', self.lab, 1.0, ['ddg', 'MW-Src'], 'dum_acq')

        VariableInternal('myFreq', self.lab)
        VariableProperty('testAmpl', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init0'), 'Amplitude')
        self.lab.VAR('testAmpl').Value = 86
        VariableProperty('test RepTime', self.lab, self.lab.HAL("ddg"), 'RepetitionTime')
        self.lab.VAR('test RepTime').Value = 99
        VariableInternal('myDura1', self.lab)
        self.lab.VAR('myDura1').Value = 2016
        VariableProperty('myDura2', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init2'), 'Duration')
        VariableSpaced('testSpace', self.lab, 'myDura1', 'myDura2', 3.1415926)
        self.lab.VAR('testSpace').Value = 2016

        WFMT_ModulationIQ("IQmod", self.lab, 49e6)
        self.lab.WFMT("IQmod").IQFrequency = 84e7
        self.lab.WFMT("IQmod").IQAmplitude = 9.4
        self.lab.WFMT("IQmod").IQAmplitudeFactor = 78.1
        self.lab.WFMT("IQmod").IQPhaseOffset = 54.3
        self.lab.WFMT("IQmod").IQdcOffset = (9,1)
        self.lab.WFMT("IQmod").IQUpperSideband = False

    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.sum(np.abs(arr1 - arr2)) < 1e-12

    def test_RecParams(self):
        self.initialise()
        
        #Check out recorded parameter storage
        #
        #Check basic parameter storage with VARs
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1))], delay=1, rec_params=[self.lab.VAR('myFreq'), self.lab.VAR('testAmpl')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,2]))
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[5,0],[5,1],[5,2]]))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1))
        res.release()
        #
        #Check basic parameter storage with a WFMT
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1))], delay=1, rec_params=[(self.lab.WFMT("IQmod"), 'IQFrequency'), self.lab.VAR('testAmpl')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,2]))
        val = self.lab.WFMT("IQmod").IQFrequency
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[val,0],[val,1],[val,2]]))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1))
        res.release()
        #
        #Check basic parameter storage with a HAL and 2D sweep
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1)), (self.lab.VAR('test RepTime'), np.linspace(9,12,4))], rec_params=[(self.lab.WFMT("IQmod"), 'IQFrequency'), (self.lab.HAL("MW-Src"), 'Power')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,4,2]))
        val = self.lab.WFMT("IQmod").IQFrequency
        val2 = self.lab.HAL("MW-Src").Power
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[[val,val2]]*4]*3))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[1]), np.linspace(9,12,4))
        res.release()
        #
        #Check case when there are no sweeping points
        time.sleep(1)   #Otherwise it writes to the same file as the previous test...
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, rec_params=[(self.lab.WFMT("IQmod"), 'IQFrequency'), (self.lab.HAL("MW-Src"), 'Power'), (self.lab.HAL("Wfm1").get_waveform_segment('init0'), 'Duration')])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3]))
        val = self.lab.WFMT("IQmod").IQFrequency
        val2 = self.lab.HAL("MW-Src").Power
        val3 = self.lab.HAL("Wfm1").get_waveform_segment('init0').Duration
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([val,val2,val3]))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals), np.array([]))
        res.release()
        exp = None

        shutil.rmtree('test_save_dir')
        self.cleanup()

    class miniExp(Experiment):
        def __init__(self, name, expt_config, testObj):
            super().__init__(name, expt_config)
            self.testObj = testObj
            self._freq = 0
            self._ampl = 20

        def _mid_process(self):
            cur_sweep_inds = self._retrieve_current_sweep_values()
            assert cur_sweep_inds['myFreq'] == self._freq, "Error in retriving current sweeping values in mid-process"
            assert cur_sweep_inds['testAmpl'] == self._ampl, "Error in retriving current sweeping values in mid-process"
            self._ampl += 1
            if self._has_completed_iteration('myFreq'):
                self._freq += 1
                self._ampl = 20
                vals = self._query_current_array_iteration('data', 'myFreq')
                assert self.testObj.arr_equality(np.array(vals.shape), np.array([10, 1, 1, 10, 2])), "FileIO query error during mid-process."

    class miniExp2(Experiment):
        def __init__(self, name, expt_config, testObj):
            super().__init__(name, expt_config)
            self.testObj = testObj

        def _init_aux_datafiles(self):
            self._init_data_file('auxilia')
            self._cntr = 0

        def _mid_process(self):
            if self._has_completed_iteration('myFreq'):
                vals = self._query_current_array_iteration('rec_params', 'myFreq')
                assert self.testObj.arr_equality(vals, np.vstack([np.arange(20,30,1), [self._cntr]*10]).T), "FileIO query error during mid-process"
                self._cntr += 1
                averages = np.mean(vals,axis=0)
                data_pkt = {
                    'parameters' : [],
                    'data' : { 'AverageA' : averages[0]+averages[1], 'AverageF' : averages[1]}
                }
                self._push_data_mid_iteration('auxilia', 'myFreq', data_pkt)

    class miniExp3(Experiment):
        def __init__(self, name, expt_config, testObj):
            super().__init__(name, expt_config)
            self.testObj = testObj

        def _init_aux_datafiles(self):
            self._init_data_file('auxilia')
            self._cntr = 0

        def _mid_process(self):
            if self._has_completed_iteration('myFreq'):
                vals = self._query_current_array_iteration('rec_params', 'myFreq')
                assert self.testObj.arr_equality(vals, np.vstack([np.arange(20,30,1), [self._cntr % 10]*10]).T), "FileIO query error during mid-process"
                self._cntr += 1
                averages = np.mean(vals,axis=0)
                data_pkt = {
                    'parameters' : [],
                    'data' : { 'AverageA' : (averages[0]+averages[1])*self.testObj.lab.VAR("myDura1").Value }
                }
                self._push_data_mid_iteration('auxilia', 'myFreq', data_pkt)

    class miniExp4(Experiment):
        def __init__(self, name, expt_config, testObj):
            super().__init__(name, expt_config)
            self.testObj = testObj

        def _init_aux_datafiles(self):
            self._init_data_file('auxilia')
            self._cntr = 0

        def _mid_process(self):
            data = self._query_current_iteration_data()
            data_pkt = {
                    'parameters' : ['r','g','s'],
                    'data' : { 'param1' : data['data']['ch1']*10, 'param2' : data['data']['ch2']*20 }
                }
            self._push_data_mid_iteration('auxilia', None, data_pkt)

    class miniExp5(Experiment):
        def __init__(self, name, expt_config, testObj):
            super().__init__(name, expt_config)
            self.testObj = testObj

        def _init_aux_datafiles(self):
            self._init_data_file('auxilia')
            self._cntr = 0

        def _mid_process(self):
            data = self._query_current_iteration_data()
            data_pkt = {
                    'parameters' : [],
                    'data' : { 'param1' : np.mean(data['data']['ch1']), 'param2' : np.mean(data['data']['ch2']) }
                }
            self._push_data_mid_iteration('auxilia', None, data_pkt)

    def test_MidProcess(self):
        self.initialise()

        exp = self.miniExp("test", self.lab.CONFIG('testConf2'), self)
        res = self.lab.run_single(exp, [(self.lab.VAR("myFreq"), np.arange(0,10,1)), (self.lab.VAR("testAmpl"), np.arange(20,30,1))])

        time.sleep(1)

        exp = self.miniExp2("test", self.lab.CONFIG('testConf2'), self)
        res = self.lab.run_single(exp, [(self.lab.VAR("myFreq"), np.arange(0,10,1)), (self.lab.VAR("testAmpl"), np.arange(20,30,1))], rec_params=[(self.lab.VAR("testAmpl"), 'Value'), (self.lab.VAR("myFreq"), 'Value')])
        res = exp.retrieve_last_aux_dataset('auxilia')
        assert len(res.param_names) == 1, "Error in recording data during mid-process."
        assert res.param_names[0] == "myFreq", "Error in recording data during mid-process."
        assert len(res.dep_params) == 2, "Error in recording data during mid-process."
        assert res.dep_params[0] == 'AverageA', "Error in recording data during mid-process."
        assert res.dep_params[1] == 'AverageF', "Error in recording data during mid-process."
        arr = res.get_numpy_array()
        assert self.arr_equality(arr[:,0], np.mean(np.arange(20,30,1))+np.arange(0,10,1)), "Error in recording data during mid-process."
        assert self.arr_equality(arr[:,1], np.arange(10)), "Error in recording data during mid-process."

        time.sleep(1)
        
        exp = self.miniExp3("test", self.lab.CONFIG('testConf2'), self)
        res = self.lab.run_single(exp, [(self.lab.VAR("myDura1"), np.arange(0,1,0.2)), (self.lab.VAR("myFreq"), np.arange(0,10,1)), (self.lab.VAR("testAmpl"), np.arange(20,30,1))], rec_params=[(self.lab.VAR("testAmpl"), 'Value'), (self.lab.VAR("myFreq"), 'Value')])
        res = exp.retrieve_last_aux_dataset('auxilia')
        assert len(res.param_names) == 2, "Error in recording data during mid-process."
        assert res.param_names[0] == "myDura1", "Error in recording data during mid-process."
        assert res.param_names[1] == "myFreq", "Error in recording data during mid-process."
        assert len(res.dep_params) == 1, "Error in recording data during mid-process."
        assert res.dep_params[0] == 'AverageA', "Error in recording data during mid-process."
        arr = res.get_numpy_array()
        assert self.arr_equality(arr[:,:,0], np.array([(np.mean(np.arange(20,30,1))+np.arange(0,10,1))*x for x in np.arange(0,1,0.2)])), "Error in recording data during mid-process."
        res.release()
        exp = None

        time.sleep(1)
        
        exp = self.miniExp4("test", self.lab.CONFIG('testConf2'), self)
        resOrig = self.lab.run_single(exp, [(self.lab.VAR("myDura1"), np.arange(0,1,0.2)), (self.lab.VAR("myFreq"), np.arange(0,10,1)), (self.lab.VAR("testAmpl"), np.arange(20,30,1))], rec_params=[(self.lab.VAR("testAmpl"), 'Value'), (self.lab.VAR("myFreq"), 'Value')])
        res = exp.retrieve_last_aux_dataset('auxilia')
        assert len(res.param_names) == 6, "Error in recording data during mid-process."
        assert res.param_names[0] == "myDura1", "Error in recording data during mid-process."
        assert res.param_names[1] == "myFreq", "Error in recording data during mid-process."
        assert res.param_names[2] == "testAmpl", "Error in recording data during mid-process."
        assert len(res.dep_params) == 2, "Error in recording data during mid-process."
        assert res.dep_params[0] == 'param1', "Error in recording data during mid-process."
        assert res.dep_params[1] == 'param2', "Error in recording data during mid-process."
        arr = res.get_numpy_array()
        arrOrig = resOrig.get_numpy_array()
        arrOrig[:,:,:,:,:,:,0] *= 10
        arrOrig[:,:,:,:,:,:,1] *= 20
        assert self.arr_equality(arr, arrOrig), "Error in recording data during mid-process."
        res.release()
        resOrig.release()
        exp = None
        
        exp = self.miniExp5("test", self.lab.CONFIG('testConf2'), self)
        resOrig = self.lab.run_single(exp, [(self.lab.VAR("myDura1"), np.arange(0,1,0.2)), (self.lab.VAR("myFreq"), np.arange(0,10,1)), (self.lab.VAR("testAmpl"), np.arange(20,30,1))], rec_params=[(self.lab.VAR("testAmpl"), 'Value'), (self.lab.VAR("myFreq"), 'Value')])
        res = exp.retrieve_last_aux_dataset('auxilia')
        assert len(res.param_names) == 3, "Error in recording data during mid-process."
        assert res.param_names[0] == "myDura1", "Error in recording data during mid-process."
        assert res.param_names[1] == "myFreq", "Error in recording data during mid-process."
        assert res.param_names[2] == "testAmpl", "Error in recording data during mid-process."
        assert len(res.dep_params) == 2, "Error in recording data during mid-process."
        assert res.dep_params[0] == 'param1', "Error in recording data during mid-process."
        assert res.dep_params[1] == 'param2', "Error in recording data during mid-process."
        arr = res.get_numpy_array()
        arrOrig = resOrig.get_numpy_array()
        arrOrig = np.mean(arrOrig,axis=-2)[:,:,:,0,0]
        assert self.arr_equality(arr, arrOrig), "Error in recording data during mid-process."
        res.release()
        resOrig.release()
        exp = None

        shutil.rmtree('test_save_dir')
        self.cleanup()

class TestExpSweeps(unittest.TestCase):
    def initialise(self):
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab.load_instrument('virACQ')
        self.lab.load_instrument('virDDG')
        self.lab.load_instrument('virAWG')
        self.lab.load_instrument('virMWS')
        self.lab.load_instrument('virMWS2')

        #Initialise test-modules
        hal_acq = ACQ("dum_acq", self.lab, 'virACQ')
        hal_ddg = DDG("ddg", self.lab, 'virDDG', )
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
        hal_mw = GENmwSource("MW-Src", self.lab, 'virMWS', 'CH1')
        hal_mw2 = GENmwSource("MW-Src2", self.lab, 'virMWS2', 'CH1')

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

        expConfig = ExperimentConfiguration('testConf', self.lab, 1.0, ['ddg', 'Wfm1', 'MW-Src'], 'dum_acq')
        expConfig = ExperimentConfiguration('testConf2', self.lab, 1.0, ['ddg', 'MW-Src'], 'dum_acq')

        VariableInternal('myFreq', self.lab)
        VariableProperty('testAmpl', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init0'), 'Amplitude')
        self.lab.VAR('testAmpl').Value = 86
        VariableProperty('test RepTime', self.lab, self.lab.HAL("ddg"), 'RepetitionTime')
        self.lab.VAR('test RepTime').Value = 99
        VariableInternal('myDura1', self.lab)
        self.lab.VAR('myDura1').Value = 2016
        VariableProperty('myDura2', self.lab, self.lab.HAL("Wfm1").get_waveform_segment('init2'), 'Duration')
        VariableSpaced('testSpace', self.lab, 'myDura1', 'myDura2', 3.1415926)
        self.lab.VAR('testSpace').Value = 2016

        WFMT_ModulationIQ("IQmod", self.lab, 49e6)
        self.lab.WFMT("IQmod").IQFrequency = 84e7
        self.lab.WFMT("IQmod").IQAmplitude = 9.4
        self.lab.WFMT("IQmod").IQAmplitudeFactor = 78.1
        self.lab.WFMT("IQmod").IQPhaseOffset = 54.3
        self.lab.WFMT("IQmod").IQdcOffset = (9,1)
        self.lab.WFMT("IQmod").IQUpperSideband = False

    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.sum(np.abs(arr1 - arr2)) < 1e-12

    def test_Snake(self):
        def _test(cur_shape, cur_ind):
            cur_inds = ExSwpSnake(cur_ind).get_sweep_indices(1+2*np.arange(np.prod(cur_shape)), cur_shape)
            inds_forward = np.arange(np.prod(cur_shape[cur_ind:]))
            num_inner = np.prod(cur_shape[cur_ind+1:])
            inds_reverse = np.concatenate([np.arange(x*num_inner, (x+1)*num_inner) for x in range(cur_shape[cur_ind]-1,-1,-1)])
            num_outer = int(np.prod(cur_shape[:cur_ind]))
            num_outer_offset = int(cur_shape[cur_ind]*num_inner)
            fin_arr = []
            for m in range(num_outer):
                if m % 2 == 1:
                    fin_arr.append(inds_reverse+m*num_outer_offset)
                else:
                    fin_arr.append(inds_forward+m*num_outer_offset)
            fin_arr = np.concatenate(fin_arr)
            assert self.arr_equality(cur_inds, 1+2*fin_arr), "ExSwpSnake did not permute the indices correctly."

        _test((5,10,5),1)
        _test((5,10,5),0)
        _test((5,10,5),2)
        _test((5,7,10,5),1)
    
    def test_SnakeExp(self):
        self.initialise()
        
        #Check out recorded parameter storage
        #
        #Check permutations do not change result...
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        self.lab.VAR('myFreq').Value = 5
        res = self.lab.run_single(exp, [(self.lab.VAR("testAmpl"), np.arange(0,3,1)), (self.lab.VAR('test RepTime'), np.linspace(9,12,4))], rec_params=[(self.lab.WFMT("IQmod"), 'IQFrequency'), (self.lab.HAL("MW-Src"), 'Power')],
                                  sweep_orders=[ExSwpSnake(1)])
        assert hasattr(exp, 'last_rec_params'), "Running an experiment with rec_params did not create an attribute \'last_rec_params\'."
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array().shape), np.array([3,4,2]))
        val = self.lab.WFMT("IQmod").IQFrequency
        val2 = self.lab.HAL("MW-Src").Power
        assert self.arr_equality(np.array(exp.last_rec_params.get_numpy_array()), np.array([[[val,val2]]*4]*3))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[0]), np.arange(0,3,1))
        assert self.arr_equality(np.array(exp.last_rec_params.param_vals[1]), np.linspace(9,12,4))
        res.release()
        #
        exp = None

        shutil.rmtree('test_save_dir')
        self.cleanup()

if __name__ == '__main__':
    temp = TestSweeps()
    temp.test_ExpReverseSweep()
    unittest.main()