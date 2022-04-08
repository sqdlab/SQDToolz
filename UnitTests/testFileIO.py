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
import os.path

import unittest

class TestFileIDirectory(unittest.TestCase):
    def initialise(self):
        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir/')

        self.lab.load_instrument('virACQ')
        self.lab.load_instrument('virDDG')
        self.lab.load_instrument('virAWG')
        self.lab.load_instrument('virMWS')

        #Initialise test-modules
        hal_acq = ACQ("dum_acq", self.lab, 'virACQ')
        hal_ddg = DDG("ddg", self.lab, 'virDDG', )
        awg_wfm = WaveformAWG("Wfm1", self.lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
        awg_wfm2 = WaveformAWG("Wfm2", self.lab, [('virAWG', 'CH3'), ('virAWG', 'CH4')], 1e9)
        hal_mw = GENmwSource("MW-Src", self.lab, 'virMWS', 'CH1')

        ExperimentConfiguration('testConf', self.lab, 1.0, ['ddg'], 'dum_acq')
        #
        VariableInternal('myFreq', self.lab)
        VariableInternal('testAmpl', self.lab)

    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None
        shutil.rmtree('test_save_dir')

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.sum(np.abs(arr1 - arr2)) < 1e-15
    
    def test_UniformSampling(self):
        self.initialise()
        VariableInternal('test_var', self.lab, 0)
        #
        self.lab.group_open("test_group")
        for m in self.lab.VAR("testAmpl").arange(0,4,1):
            self.lab.VAR('test_var').Value = 7+m
            exp = Experiment("test", self.lab.CONFIG('testConf'))
            res = self.lab.run_single(exp, [(self.lab.VAR("myFreq"), np.arange(3))])
            time.sleep(1)
        self.lab.group_close()
        #
        reader = FileIODirectory.fromReader(res)
        assert reader.param_names[0] == 'testAmpl', "FileIODirectory returns wrong outer slicing variable for uniform sampling."
        assert self.arr_equality(reader.param_vals[0], np.arange(0,4,1)), "FileIODirectory returns wrong outer slicing values for uniform sampling."
        assert reader.param_names[1] == 'myFreq', "FileIODirectory returns wrong inner slicing variable for uniform sampling."
        assert self.arr_equality(reader.param_vals[1], np.arange(3)), "FileIODirectory returns wrong inner slicing values for uniform sampling."
        #
        var_dicts = reader.get_var_dict_arrays()
        assert 'test_var' in var_dicts, "FileIODirectory failed to parse in VARs correctly."
        assert self.arr_equality(var_dicts['test_var'], 7+np.arange(0,4,1)), "FileIODirectory failed to parse in VARs correctly."
        assert 'myFreq' in var_dicts, "FileIODirectory failed to parse in VARs correctly."
        assert self.arr_equality(var_dicts['myFreq'], np.array([2]*4)), "FileIODirectory failed to parse in VARs correctly."
        assert 'testAmpl' in var_dicts, "FileIODirectory failed to parse in VARs correctly."
        assert self.arr_equality(var_dicts['testAmpl'], np.arange(0,4,1)), "FileIODirectory failed to parse in VARs correctly."
        #
        res.release()
        res = None
        reader = None
        self.cleanup()
    
    def test_NonUniformSampling(self):
        self.initialise()
        #
        self.lab.group_open("test_group")
        for m in range(3,6):
            exp = Experiment("test", self.lab.CONFIG('testConf'))
            res = self.lab.run_single(exp, [(self.lab.VAR("myFreq"), np.arange(m))])
            time.sleep(1)
        self.lab.group_close()
        #
        reader = FileIODirectory.fromReader(res)
        assert reader.param_names[0] == 'DirFileNo', "FileIODirectory returns wrong outer slicing variable for uniform sampling."
        assert self.arr_equality(reader.param_vals[0], np.arange(3)), "FileIODirectory returns wrong outer slicing values for uniform sampling."
        #
        res.release()
        res = None
        reader = None
        self.cleanup()


if __name__ == '__main__':
    temp = TestFileIDirectory()
    temp.test_NonUniformSampling()
    unittest.main()