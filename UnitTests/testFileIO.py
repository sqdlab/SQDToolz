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

from pathlib import Path

import numpy as np
import shutil
import os.path

import unittest

class TestExpFileIO(unittest.TestCase):
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
        time.sleep(1)
        #
        res.release()
        res = None
        reader = None
        self.cleanup()
    
    def test_ManyOneSampling(self):
        self.initialise()
        VariableInternal('test_var', self.lab, 0)
        #
        #Test with one simple one-many variable - and check it sets correctly via rec_params 
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        res = self.lab.run_single(exp, [('testAmal', [self.lab.VAR("myFreq"), self.lab.VAR("testAmpl")], np.array([[1,2],[3,4],[5,6]]))],
                                    rec_params=[self.lab.VAR("myFreq"), self.lab.VAR("testAmpl")])
        assert 'testAmal' in res.param_many_one_maps, "FileIOReader failed to parse a many-one sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][0] == 'myFreq', "FileIOReader failed to parse a many-one sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][1] == 'testAmpl', "FileIOReader failed to parse a many-one sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][0], np.array([1,3,5])), "FileIOReader failed to parse a many-one sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][1], np.array([2,4,6])), "FileIOReader failed to parse a many-one sweeping variable."
        assert self.arr_equality(exp.last_rec_params.get_numpy_array(), np.array([[1,2],[3,4],[5,6]]))
        time.sleep(1)
        #
        #Test with one simple one-many variable and a normal variable - and check it sets correctly via rec_params
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        res = self.lab.run_single(exp, [('testAmal', [self.lab.VAR("myFreq"), self.lab.VAR("testAmpl")], np.array([[1,2],[3,4],[5,6]])),
                                        (self.lab.VAR('test_var'), np.arange(4))],
                                    rec_params=[self.lab.VAR("myFreq"), self.lab.VAR("testAmpl")])
        assert 'testAmal' in res.param_many_one_maps, "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][0] == 'myFreq', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][1] == 'testAmpl', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][0], np.array([1,3,5])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][1], np.array([2,4,6])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_names[:2] == ['testAmal', 'test_var'], "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(exp.last_rec_params.get_numpy_array(), np.array([[[1,2]]*4,[[3,4]]*4,[[5,6]]*4])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        time.sleep(1)
        #
        #Test with one normal variable and one one-many variable - and check it sets correctly via rec_params
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        res = self.lab.run_single(exp, [(self.lab.VAR('test_var'), np.arange(4)),
                                        ('testAmal', [self.lab.VAR("myFreq"), self.lab.VAR("testAmpl")], np.array([[1,2],[3,4],[5,6]]))],
                                    rec_params=[self.lab.VAR("myFreq"), self.lab.VAR("testAmpl")])
        assert 'testAmal' in res.param_many_one_maps, "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][0] == 'myFreq', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][1] == 'testAmpl', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][0], np.array([1,3,5])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][1], np.array([2,4,6])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_names[:2] == ['test_var', 'testAmal'], "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(exp.last_rec_params.get_numpy_array(), np.array([[[1,2],[3,4],[5,6]]]*4)), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        time.sleep(1)
        #
        #Test with one normal variable and two one-many variables - and check it sets correctly via rec_params
        VariableInternal('test_var2', self.lab, 0)
        VariableInternal('test_var3', self.lab, 0)
        VariableInternal('test_var4', self.lab, 0)
        exp = Experiment("test", self.lab.CONFIG('testConf'))
        res = self.lab.run_single(exp, [('testAmal', [self.lab.VAR("myFreq"), self.lab.VAR("testAmpl")], np.array([[1,2],[3,4],[5,6]])),
                                        (self.lab.VAR('test_var'), np.arange(4)),
                                        ('testAmal2', [self.lab.VAR("test_var2"), self.lab.VAR("test_var3"), self.lab.VAR("test_var4")], np.array([[11,12,13],[14,15,16],[17,18,19],[20,21,22]]))],
                                    rec_params=[self.lab.VAR("myFreq"), self.lab.VAR("testAmpl"), self.lab.VAR("test_var2"), self.lab.VAR("test_var3"), self.lab.VAR("test_var4")])
        assert 'testAmal' in res.param_many_one_maps, "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][0] == 'myFreq', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal']['param_names'][1] == 'testAmpl', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][0], np.array([1,3,5])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal']['param_vals'][1], np.array([2,4,6])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        #
        assert 'testAmal2' in res.param_many_one_maps, "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal2']['param_names'][0] == 'test_var2', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal2']['param_names'][1] == 'test_var3', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert res.param_many_one_maps['testAmal2']['param_names'][2] == 'test_var4', "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal2']['param_vals'][0], np.array([11,14,17,20])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal2']['param_vals'][1], np.array([12,15,18,21])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(res.param_many_one_maps['testAmal2']['param_vals'][2], np.array([13,16,19,22])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        #
        assert res.param_names[:3] == ['testAmal', 'test_var', 'testAmal2'], "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        assert self.arr_equality(exp.last_rec_params.get_numpy_array(), np.array([[[[y, y+1, x, x+1, x+2] for x in np.arange(11,23,3)]]*4 for y in np.arange(1,7,2)])), "FileIOReader failed to parse a many-one sweeping variable when combined with a normal sweeping variable."
        time.sleep(1)
        #
        #
        exp.last_rec_params.release()
        res.release()
        res = None
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
        time.sleep(1)
        #
        res.release()
        res = None
        reader = None
        self.cleanup()

    def test_WriteFileDirect(self):
        data_array = np.zeros( (2,3,4,2) )
        param_names = ["power", "frequency", "flux"]
        param_vals = [np.array([-10,0]), np.array([0,1,2]), np.array([0,1,2,3])]
        dep_param_names = ['rf_I', 'rf_Q']
        FileIOWriter.write_file_direct('testFile.h5', data_array, param_names, param_vals, dep_param_names)
        #TODO: Write more test-cases verifying asserts...

        tempRdr = FileIOReader('testFile.h5')
        assert self.arr_equality(data_array, tempRdr.get_numpy_array()), "Writing HDF5 file directly caused error in data array."
        assert param_names == tempRdr.param_names, "Writing HDF5 file directly caused error in parameter names."
        assert len(param_vals) == len(tempRdr.param_vals), "Writing HDF5 file directly caused error in parameter values."
        for m in range(len(param_vals)):
            assert self.arr_equality(param_vals[m], tempRdr.param_vals[m]), f"Writing HDF5 file directly caused error in parameter values (index {m})."
        assert dep_param_names == tempRdr.dep_params, "Writing HDF5 file directly caused error in dependent parameter names."
        tempRdr.release()
        tempRdr = None
        os.remove('testFile.h5')

    def test_DataResizing(self):
        self.initialise()
        VariableInternal('test_var', self.lab, 0)

        wrtr = FileIOWriter('test_save_dir/test.h5', store_timestamps=False)    
        for m in range(1,10):
            sweep_arr = [(self.lab.VAR('test_var'), np.arange(m)), (self.lab.VAR("myFreq"), np.arange(3))]
            data_pkt = self.lab.HAL("dum_acq").get_data()
            for n in range(3):
                wrtr.push_datapkt(data_pkt, sweep_arr)
        wrtr.close()
        wrtr = None
        #
        leData = FileIOReader('test_save_dir/test.h5')
        arr = leData.get_numpy_array()
        assert arr.shape[0] == 9, "Something went wrong in the resizing?"
        assert self.arr_equality(leData.param_vals[0], np.arange(9)), "The parameter array did not write properly on resizing..."
        leData.release()
        leData = None

        wrtr = FileIOWriter('test_save_dir/test2.h5', store_timestamps=True)    
        for m in range(1,10):
            sweep_arr = [(self.lab.VAR('test_var'), np.arange(m)), (self.lab.VAR("myFreq"), np.arange(3))]
            data_pkt = self.lab.HAL("dum_acq").get_data()
            for n in range(3):
                wrtr.push_datapkt(data_pkt, sweep_arr)
        wrtr.close()
        wrtr = None
        #
        leData = FileIOReader('test_save_dir/test2.h5')
        arr = leData.get_numpy_array()
        assert arr.shape[0] == 9, "Something went wrong in the resizing?"
        assert self.arr_equality(leData.param_vals[0], np.arange(9)), "The parameter array did not write properly on resizing..."
        arrTS = leData.get_time_stamps()
        assert arrTS.shape[0] == 9, "Something went wrong in the resizing time-stamps?"
        leData.release()
        leData = None


        self.cleanup()


if __name__ == '__main__':
    temp = TestExpFileIO()
    temp.test_DataResizing()
    unittest.main()