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

import numpy as np
import shutil

import unittest

class TestSegments(unittest.TestCase):
    ERR_TOL = 5e-13

    def initialise(self):
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab.load_instrument('virAWG')
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
    
    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL
    
    def test_SegmentsAndIQ(self):
        self.initialise()
        awg_wfm = self.lab.HAL("Wfm1")

        #
        #Test IQ-Modulation
        #
        #Create unmodulated waveforms first
        read_segs = []
        read_segs2 = []
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        #Gather initial arrays
        wfm_unmod = np.vstack(awg_wfm.get_raw_waveforms())
        #
        #Okay now modulate...
        WFMT_ModulationIQ('IQmod', self.lab, 47e7)
        WFMT_ModulationIQ('IQmod2', self.lab, 13e7)
        #
        #Changing phases Test
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled."
        #
        #Trying two modulation areas
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45) + 60))
        temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45) + 60))
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled."
        #
        #Trying two different modulation areas
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod2').apply(), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega2*1e-9*(np.arange(45) + 60))
        temp[1, init2_stencil] *= np.sin(omega2*1e-9*(np.arange(45) + 60))
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when using 2 different modulations."
        #
        #Trying to manipulate the phase now...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod').apply(phase=0), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45)))
        temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45)))
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when resetting phase to zero."
        #
        #Trying to manipulate the phase to a non-zero value...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod').apply(phase=np.pi/2), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45))+np.pi/2)
        temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45))+np.pi/2)
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when changing phase to non-zero value."
        #
        #Trying to manipulate the phase to a negative non-zero value...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod').apply(phase=-0.4125), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45))-0.4125)
        temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45))-0.4125)
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when changing phase to a negative value."
        #
        #Trying to manipulate the phase offset...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod').apply(phase_offset=-0.91939), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45)+60)-0.91939)
        temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45)+60)-0.91939)
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when changing phase offset."
        #
        #Trying to manipulate the phase offset and checking relation down the track...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod').apply(phase_offset=-0.91939), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", self.lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        init3_stencil = np.s_[182:227]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45)+60)-0.91939)
        temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45)+60)-0.91939)
        temp[0, init3_stencil] *= np.cos(omega*1e-9*(np.arange(45)+182)-0.91939)
        temp[1, init3_stencil] *= np.sin(omega*1e-9*(np.arange(45)+182)-0.91939)
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when changing phase offset in a previous waveform segment."
        #
        #Trying to manipulate the phase and checking relation down the track...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod').apply(phase=0.1), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", self.lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        init3_stencil = np.s_[182:227]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        temp[0, init2_stencil] *= np.cos(omega*1e-9*(np.arange(45))+0.1)
        temp[1, init2_stencil] *= np.sin(omega*1e-9*(np.arange(45))+0.1)
        temp[0, init3_stencil] *= np.cos(omega*1e-9*(np.arange(45)+182-60)+0.1)
        temp[1, init3_stencil] *= np.sin(omega*1e-9*(np.arange(45)+182-60)+0.1)
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when changing phase in a previous waveform segment."
        #
        #Trying to manipulate the phase and checking relation down the track with 2 separate frequencies!...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(phase=0.1), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod2').apply(), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", self.lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        init3_stencil = np.s_[182:227]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20))+0.1)
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20))+0.1)
        temp[0, init2_stencil] *= np.cos(omega2*1e-9*(np.arange(45)+60))
        temp[1, init2_stencil] *= np.sin(omega2*1e-9*(np.arange(45)+60))
        temp[0, init3_stencil] *= np.cos(omega*1e-9*(np.arange(45)+182-10)+0.1)
        temp[1, init3_stencil] *= np.sin(omega*1e-9*(np.arange(45)+182-10)+0.1)
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when changing phase in a previous waveform segment with 2 frequencies in play."
        #
        #Check that VARs can set WFMTs...
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(phase=0.141), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", self.lab.WFMT('IQmod2').apply(), 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", self.lab.WFMT('IQmod').apply(), 45e-9, 0.5-0.1))
        VariableProperty('wfmt_test', self.lab, awg_wfm.get_waveform_segment('init').get_WFMT(), 'phase')
        assert self.lab.VAR('wfmt_test').Value == 0.141, "WFMTs are not being properly resolved for an IQ waveform."
        self.lab.VAR('wfmt_test').Value = 0.145
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        init2_stencil = np.s_[60:105]
        init3_stencil = np.s_[182:227]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        omega2 = 2*np.pi*self.lab.WFMT('IQmod2').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20))+0.145)
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20))+0.145)
        temp[0, init2_stencil] *= np.cos(omega2*1e-9*(np.arange(45)+60))
        temp[1, init2_stencil] *= np.sin(omega2*1e-9*(np.arange(45)+60))
        temp[0, init3_stencil] *= np.cos(omega*1e-9*(np.arange(45)+182-10)+0.145)
        temp[1, init3_stencil] *= np.sin(omega*1e-9*(np.arange(45)+182-10)+0.145)
        assert self.arr_equality(temp, wfm_mod), "The IQ waveform was incorrectly compiled when changing phase via a VAR construct."

        shutil.rmtree('test_save_dir')
        self.cleanup()

    def test_ZeroLength(self):
        self.initialise()
        awg_wfm = self.lab.HAL("Wfm1")
        read_segs = []
        read_segs2 = []
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        #Gather initial arrays
        wfm_unmod = np.vstack(awg_wfm.get_raw_waveforms())
        #
        #Modulations
        WFMT_ModulationIQ('IQmod', self.lab, 47e7)
        WFMT_ModulationIQ('IQmod2', self.lab, 13e7)

        #Default test with an elastic segment
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "Default waveform compilation failed."
        #
        #Test with a normal zero segment
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("ZEROLENGTH", None, 0e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "Default waveform compilation failed."
        #
        #Test with a WFS_Group
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, 30e-9, 0.1),
                                        WFS_Gaussian("ZEROLENGTH", None, 0e-9, 0.5-0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ]))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "WFS_Group failed in waveform compilation."
        #
        #Test with a WFS_Group on zero repeats
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, 30e-9, 0.1),
                                        WFS_Gaussian("ZEROLENGTH", None, 0e-9, 0.5-0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ]))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroupZERO", [
                                        WFS_Constant("zero1", None, 30e-9, 0.1),
                                        WFS_Gaussian("ZEROLENGTH", None, 0e-9, 0.5-0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], num_repeats=0))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "WFS_Group failed in waveform compilation."
        #
        #Test marker decomposition...
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], time_len=75e-9))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("ZEROLENGTH", None, 0e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        awg_wfm.get_output_channel(0).marker(0).set_markers_to_segments([ 'init', 'ZEROLENGTH', ['TestGroup','init2'], 'init3' ])
        raw_mkrs = awg_wfm.get_output_channel(0).marker(0).get_raw_marker_waveform()
        exp_mkrs = np.array( [0]*10 + [1]*20  +  [0]*30 + [1]*45  +  [0]*77 + [1]*45 )
        assert self.arr_equality(raw_mkrs, exp_mkrs), "WFS_Group failed in marker compilation."
        #
        #Test marker decomposition with zero inside the group!...
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1),
                                        WFS_Gaussian("ZEROLENGTH", None, 0e-9, 0.5-0.1)
                                        ], time_len=75e-9))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("ZEROLENGTH", None, 0e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        awg_wfm.get_output_channel(0).marker(0).set_markers_to_segments([ 'init', 'ZEROLENGTH', ['TestGroup','init2'], ['TestGroup','ZEROLENGTH'], 'init3' ])
        raw_mkrs = awg_wfm.get_output_channel(0).marker(0).get_raw_marker_waveform()
        exp_mkrs = np.array( [0]*10 + [1]*20  +  [0]*30 + [1]*45  +  [0]*77 + [1]*45 )
        assert self.arr_equality(raw_mkrs, exp_mkrs), "WFS_Group failed in marker compilation."

        shutil.rmtree('test_save_dir')
        self.cleanup()

    def test_Group(self):
        self.initialise()
        awg_wfm = self.lab.HAL("Wfm1")
        read_segs = []
        read_segs2 = []
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        #Gather initial arrays
        wfm_unmod = np.vstack(awg_wfm.get_raw_waveforms())
        #
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1R", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2R", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 2e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        #Gather initial arrays
        wfm_unmodRep2 = np.vstack(awg_wfm.get_raw_waveforms())
        #
        #Modulations
        WFMT_ModulationIQ('IQmod', self.lab, 47e7)
        WFMT_ModulationIQ('IQmod2', self.lab, 13e7)

        #
        #Test WFM_Group
        #
        #Default test with an elastic segment
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "Default waveform compilation failed."
        #
        #Test a basic WFS_Group construct
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, 30e-9, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ]))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "WFS_Group failed in waveform compilation."
        #
        #Test a basic WFS_Group construct with repeats
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, 30e-9, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], num_repeats=2))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 2e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmodRep2*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "WFS_Group failed in waveform compilation when using repeats."
        #
        #Test a basic WFS_Group construct with elastic time-frame
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], time_len=75e-9))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmod*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        assert self.arr_equality(temp, wfm_mod), "WFS_Group failed in waveform compilation."
        #
        #Test marker decomposition...
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], time_len=75e-9))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        awg_wfm.get_output_channel(0).marker(0).set_markers_to_segments([ 'init', ['TestGroup','init2'], 'init3' ])
        raw_mkrs = awg_wfm.get_output_channel(0).marker(0).get_raw_marker_waveform()
        exp_mkrs = np.array( [0]*10 + [1]*20  +  [0]*30 + [1]*45  +  [0]*77 + [1]*45 )
        assert self.arr_equality(raw_mkrs, exp_mkrs), "WFS_Group failed in marker compilation."
        #
        #Test marker decomposition when using repeats...
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], time_len=75e-9, num_repeats=2))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 2e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        awg_wfm.get_output_channel(0).marker(0).set_markers_to_segments([ 'init', ['TestGroup','init2'], 'init3' ])
        raw_mkrs = awg_wfm.get_output_channel(0).marker(0).get_raw_marker_waveform()
        exp_mkrs = np.array( [0]*10 + [1]*20  +  ([0]*30 + [1]*45)*2  +  [0]*2 + [1]*45 )
        assert self.arr_equality(raw_mkrs, exp_mkrs), "WFS_Group failed in marker compilation when using repeats."
        #
        #Test marker decomposition in nested WFS_Groups...
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=237e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], time_len=75e-9))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup2", [
                                        WFS_Group("Sub1", [
                                            WFS_Constant("zero1", None, 3e-9, 0.1),
                                            WFS_Gaussian("init2", None, 2e-9, 0.5-0.1)
                                            ], time_len=5e-9),
                                        WFS_Gaussian("init2", None, 5e-9, 0.5-0.1)
                                        ], time_len=10e-9))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        awg_wfm.get_output_channel(0).marker(0).set_markers_to_segments([ 'init', ['TestGroup','init2'], 'init3', ['TestGroup2', 'Sub1', 'init2'] ])
        raw_mkrs = awg_wfm.get_output_channel(0).marker(0).get_raw_marker_waveform()
        exp_mkrs = np.array( [0]*10 + [1]*20  +  [0]*30 + [1]*45  +  [0]*77 +    [0]*3+[1]*2+[0]*5    + [1]*45 )
        assert self.arr_equality(raw_mkrs, exp_mkrs), "WFS_Group failed in marker compilation in a nested case."
        #
        #Test marker decomposition in nested WFS_Groups and repeats...
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=387e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], time_len=75e-9, num_repeats=3))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup2", [
                                        WFS_Group("Sub1", [
                                            WFS_Constant("zero1", None, 3e-9, 0.1),
                                            WFS_Gaussian("init2", None, 2e-9, 0.5-0.1)
                                            ], time_len=5e-9),
                                        WFS_Gaussian("init2", None, 5e-9, 0.5-0.1)
                                        ], time_len=10e-9))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        awg_wfm.get_output_channel(0).marker(0).set_markers_to_segments([ 'init', ['TestGroup','init2'], 'init3', ['TestGroup2', 'Sub1', 'init2'] ])
        raw_mkrs = awg_wfm.get_output_channel(0).marker(0).get_raw_marker_waveform()
        exp_mkrs = np.array( [0]*10 + [1]*20  +  ([0]*30 + [1]*45)*3  +  [0]*77 +    [0]*3+[1]*2+[0]*5    + [1]*45 )
        assert self.arr_equality(raw_mkrs, exp_mkrs), "WFS_Group failed in marker compilation in a nested case when using repeats."

        #An interesting edge-case
        wait_times = np.linspace(1e-9,2e-6,49)
        WaveformAWG("wfmRabi", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1.25e9)
        self.lab.HAL("wfmRabi").set_valid_total_time((wait_times.size+1)*50e-6)
        self.lab.HAL("wfmRabi").clear_segments()
        read_segs = []
        for m, cur_wait in enumerate(wait_times):
            self.lab.HAL("wfmRabi").add_waveform_segment(WFS_Group("TestGroup", [
                                                    WFS_Constant(f"init{m}", None, -1, 0.0),
                                                    WFS_Gaussian(f"tip{m}", self.lab.WFMT('IQmod').apply(phase=0), 40e-9, 1),
                                                    WFS_Constant(f"wait{m}", None, cur_wait, 0.0),
                                                    WFS_Gaussian(f"untip{m}", self.lab.WFMT('IQmod').apply(), 40e-9, 2),
                                                    WFS_Constant(f"pad{m}", None, 5e-9, 0.0)
                                                ], time_len=46e-6))
            self.lab.HAL("wfmRabi").add_waveform_segment(WFS_Constant(f"read{m}", None, 4e-6, 0.0))
            read_segs += [f"read{m}"]
        self.lab.HAL("wfmRabi").add_waveform_segment(WFS_Constant("init_pad", None, -1, 0.0))
        self.lab.HAL("wfmRabi").get_raw_waveforms()

        shutil.rmtree('test_save_dir')
        self.cleanup()

    def test_SaveReload(self):
        self.initialise()
        self.lab.load_instrument('virACQ')
        hal_acq = ACQ("dum_acq", self.lab, 'virACQ')

        awg_wfm = self.lab.HAL("Wfm1")
        read_segs = []
        read_segs2 = []
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1R", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2R", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 2e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        #Gather initial arrays
        wfm_unmodR = np.vstack(awg_wfm.get_raw_waveforms())
        #Modulations
        WFMT_ModulationIQ('IQmod', self.lab, 47e7)
        WFMT_ModulationIQ('IQmod2', self.lab, 13e7)
        #Test a basic WFS_Group construct with elastic time-frame
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9, total_time=227e-9)
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", self.lab.WFMT('IQmod').apply(), 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Group("TestGroup", [
                                        WFS_Constant("zero1", None, -1, 0.1),
                                        WFS_Gaussian("init2", None, 45e-9, 0.5-0.1)
                                        ], time_len=75e-9, num_repeats=2))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 2e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        init_stencil = np.s_[10:30]
        temp = wfm_unmodR*1.0
        omega = 2*np.pi*self.lab.WFMT('IQmod').IQFrequency
        temp[0, init_stencil] *= np.cos(omega*1e-9*(np.arange(20) + 10))
        temp[1, init_stencil] *= np.sin(omega*1e-9*(np.arange(20) + 10))
        #
        assert self.arr_equality(temp, wfm_mod), "WFS_Group failed in waveform compilation."
               
        expConfig = ExperimentConfiguration('testConf', self.lab, 1.0, ['Wfm1'], 'dum_acq')
        # leConfig = expConfig.save_config()

        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, -1, 0.0))
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        assert not self.arr_equality(temp, wfm_mod), "The waveform randomly compiles correctly even though it has been redone."
        expConfig.init_instruments()
        wfm_mod = np.vstack(awg_wfm.get_raw_waveforms())
        assert self.arr_equality(temp, wfm_mod), "The waveform was not constructed properly on reloading."

        shutil.rmtree('test_save_dir')
        self.cleanup()

class TestAWGChecks(unittest.TestCase):
    def initialise(self):
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab.load_instrument('virAWG')
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
    
    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None

    def test_MemoryChecks(self):
        self.initialise()
        awg_wfm = self.lab.HAL("Wfm1")
        #
        #Verify the waveform memory requirement checks
        #
        #Multiple of N check
        read_segs = []
        read_segs2 = []
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 10e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Constant("zero2", None, 77e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init3", None, 45e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        assert_found = False
        try:
            awg_wfm.prepare_initial()
            awg_wfm.prepare_final()
        except AssertionError:
            assert_found = True
        assert assert_found, "The waveform preparation function incorrectly accepts a waveform that does not satisfy the instrument's memory requirement (multiple of 8)."
        #
        #Minimum N check
        read_segs = []
        read_segs2 = []
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 1e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 1e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("zero2", None, 1e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        assert_found = False
        try:
            awg_wfm.prepare_initial()
            awg_wfm.prepare_final()
        except AssertionError:
            assert_found = True
        assert assert_found, "The waveform preparation function incorrectly accepts a waveform that does not satisfy the instrument's memory requirement (minimum of 8)."
        #
        #Check normal programming works...
        read_segs = []
        read_segs2 = []
        awg_wfm.clear_segments()
        awg_wfm.add_waveform_segment(WFS_Constant("SEQPAD", None, 12e-9, 0.0))
        awg_wfm.add_waveform_segment(WFS_Gaussian("init", None, 4e-9, 0.5-0.1))
        awg_wfm.add_waveform_segment(WFS_Gaussian("zero2", None, 8e-9, 0.5-0.1))
        read_segs += ["init"]
        read_segs2 += ["zero2"]
        awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
        awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(read_segs2)
        assert_found = False
        awg_wfm.prepare_initial()
        awg_wfm.prepare_final()

        shutil.rmtree('test_save_dir')
        self.cleanup()

    def test_ValidLengthFunctions(self):
        self.initialise()
        awg_wfm = self.lab.HAL("Wfm1")
        #
        #Check the valid length functions
        #
        assert awg_wfm.get_valid_length_from_time(12e-9) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
        assert awg_wfm.get_valid_length_from_time(16e-9) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
        assert awg_wfm.get_valid_length_from_time(5e-9) == [8e-9, 8e-9], "Valid time lengths for a given time are incorrect."
        #
        assert awg_wfm.get_valid_length_from_pts(12) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
        assert awg_wfm.get_valid_length_from_pts(16) == [16e-9, 16e-9], "Valid time lengths for a given time are incorrect."
        assert awg_wfm.get_valid_length_from_pts(5) == [8e-9, 8e-9], "Valid time lengths for a given time are incorrect."

        shutil.rmtree('test_save_dir')
        self.cleanup()


if __name__ == '__main__':
    TestSegments().test_SegmentsAndIQ()
    unittest.main()