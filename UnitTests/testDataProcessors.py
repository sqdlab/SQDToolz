from sqdtoolz.Laboratory import*

from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
from sqdtoolz.HAL.Processors.CPU.CPU_Integrate import*
from sqdtoolz.HAL.Processors.CPU.CPU_Max import*
from sqdtoolz.HAL.Processors.CPU.CPU_ConstantArithmetic import*
from sqdtoolz.HAL.Processors.CPU.CPU_ChannelArithmetic import*
TEST_CPU = True

try:
    from sqdtoolz.HAL.Processors.ProcessorGPU import*
    from sqdtoolz.HAL.Processors.GPU.GPU_DDC import*
    from sqdtoolz.HAL.Processors.GPU.GPU_FIR import*
    from sqdtoolz.HAL.Processors.GPU.GPU_Mean import*
    from sqdtoolz.HAL.Processors.GPU.GPU_Integrate import*
    from sqdtoolz.HAL.Processors.GPU.GPU_Max import*
    from sqdtoolz.HAL.Processors.GPU.GPU_ConstantArithmetic import*
    from sqdtoolz.HAL.Processors.GPU.GPU_ChannelArithmetic import*
    TEST_GPU = True
except ModuleNotFoundError:
    pass

from sqdtoolz.HAL.Processors.ProcessorFPGA import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDC import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDCFIR import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_Decimation import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_Integrate import*

import random
import matplotlib.pyplot as plt

INCLUDE_PLOTS = False

import shutil

import unittest

import operator #for ConstantArithmetic
import scipy.fft
class TestCPU(unittest.TestCase):
    ERR_TOL = 5e-7

    def initialise(self):
        self.lab = Laboratory('', 'test_save_dir/')
    
    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None
        shutil.rmtree('test_save_dir')

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL

    def arr_equality_pct(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)/np.abs(arr1 + self.ERR_TOL)) < self.ERR_TOL
    
    def test_IQdemod(self):
        self.initialise()
        data_size = 1024#*1024*4
        omega = 2*np.pi*0.14
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000) + (np.random.rand(data_size)-0.5)*2*noise_level
        num_reps = 10
        num_segs = 4
        noise_level = 0.1
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase) + (np.random.rand(data_size)-0.5)*2*noise_level for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data },
            'misc' : {'SampleRates' : [1]}
        }
        #
        # import matplotlib.pyplot as plt
        # for r in range(num_reps):
        #     for s in range(num_segs):
        #         plt.plot(cur_data['data']['ch1'][r][s])
        # plt.show()
        # input('Press ENTER')
        #
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_DDC([0.14]))
        new_proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
        new_proc.add_stage_end(CPU_Mean('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        mus = []
        sds = []
        for s in range(num_segs):
            data_envelope = np.sqrt(cur_data['data']['ch1_I'][s]**2 + cur_data['data']['ch1_Q'][s]**2)
            resids = data_envelope-ampl_envelope(num_segs-s,0.0)#[40:]
            mu, sd = np.mean(resids), np.std(resids)
            mus += [mu]
            sds += [sd]
            if INCLUDE_PLOTS:
                plt.plot(resids)
        if INCLUDE_PLOTS:
            plt.show()
        mus = np.array(mus)
        sds = np.array(sds)
        assert np.max(np.abs(mus)) < noise_level / np.sqrt(num_reps) * 2.56 * 4, "CPU Signal downconversion yields unsuitable results."
        assert np.max(np.abs(sds)) < noise_level / np.sqrt(num_reps) * 2.56 * 4, "CPU Signal downconversion yields unsuitable results."
        if INCLUDE_PLOTS:
            input('Press ENTER')
        self.cleanup()

    def test_IQddc(self):
        self.initialise()

        #Try simple test-case
        data_size = 1024#*1024*4
        f0 = 0.14
        omega = 2*np.pi*f0
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 10
        num_segs = 4
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase) for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data },
            'misc' : {'SampleRates' : [1]}
        }
        #
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_DDC([f0]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase)*2.0*np.cos(omega*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "CPU DDC does not yield expected result for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase)*-2.0*np.sin(omega*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "CPU DDC does not yield expected result for Q-channel."

        #Try with 2 channels
        data_size = 1024#*1024*4
        f0 = 0.29
        f1 = 0.11
        omega0 = 2*np.pi*f0
        omega1 = 2*np.pi*f1
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 13
        num_segs = 8
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase) for s in range(num_segs)] for r in range(num_reps)])
        raw_data2 = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase) for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data, 'ch2' : raw_data2 },
            'misc' : {'SampleRates' : [1, 1]}
        }
        #
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_DDC([f0, f1]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*2.0*np.cos(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*-2.0*np.sin(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for Q-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*2.0*np.cos(omega1*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_I'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*-2.0*np.sin(omega1*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_Q'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for Q-channel."

        #Try with 2 channels and different sample rates
        data_size = 4536#*1024*4
        f0 = 0.29
        f1 = 0.11
        omega0 = 2*np.pi*f0
        omega1 = 2*np.pi*f1
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 11
        num_segs = 7
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase) for s in range(num_segs)] for r in range(num_reps)])
        raw_data2 = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase) for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data, 'ch2' : raw_data2 },
            'misc' : {'SampleRates' : [1, 2]}
        }
        #
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_DDC([f0, f1]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*2.0*np.cos(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*-2.0*np.sin(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for Q-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*2.0*np.cos(omega1*np.arange(data_size)/2) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_I'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*-2.0*np.sin(omega1*np.arange(data_size)/2) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_Q'], expected_ans), "CPU DDC does not yield expected result in the 2-channel case for Q-channel."

        #Try only 1 dimension
        data_size = 5424#*1024*4
        f0 = 0.14
        omega = 2*np.pi*f0
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 10
        num_segs = 4
        phase = 3.0
        raw_data = ampl_envelope(num_segs)*np.sin(omega*np.arange(data_size)+phase)
        #
        cur_data = {
            'parameters' : ['sample'],
            'data' : { 'ch1' : raw_data },
            'misc' : {'SampleRates' : [1]}
        }
        #
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_DDC([f0]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = ampl_envelope(num_segs)*np.sin(omega*np.arange(data_size)+phase)*2.0*np.cos(omega*np.arange(data_size))
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "CPU DDC does not yield expected result for I-channel."
        expected_ans = ampl_envelope(num_segs)*np.sin(omega*np.arange(data_size)+phase)*-2.0*np.sin(omega*np.arange(data_size))
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "CPU DDC does not yield expected result for Q-channel."

        self.cleanup()

    def test_Mean(self):
        self.initialise()
        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Mean('sample'))
        new_proc.add_stage(CPU_Mean('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) / (data_size * num_segs) for x in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
        #Test with multiple-push
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Mean('sample'))
        new_proc.add_stage(CPU_Mean('segment'))
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,3)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(3,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) / (data_size * num_segs) for x in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
        #
        #Test with another simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Mean('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[( (num_segs**2+num_segs)*0.5 +2*r*num_segs)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)]) / num_segs
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
        #Test with multiple-push
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Mean('segment'))
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,3)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(3,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[( (num_segs**2+num_segs)*0.5 +2*r*num_segs)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)]) / num_segs
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
        #
        #Test with full contraction:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Mean('sample'))
        new_proc.add_stage(CPU_Mean('segment'))
        new_proc.add_stage_end(CPU_Mean('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = 0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs)*num_reps + 2*0.5*(num_reps**2+num_reps)*num_segs ) / (data_size * num_segs * num_reps)
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "CPU Mean does not yield expected result."
        self.cleanup()

    def test_MeanBlock(self):
        self.initialise()

        sample_array = [[[x+y+z for x in range(6)] for y in range(10)] for z in range(4)]
        sample_array = np.array(sample_array)

        num_reps, num_segs, num_smpls = sample_array.shape
        #
        #Test with simple case over samples:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('sample', 2))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[(2*x+0.5)+y+z for x in range(3)] for y in range(10)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with simple case over segments:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('segment', 5))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[0.2*((x+5*y) + (x+5*y)+1 + (x+5*y)+2 + (x+5*y)+3 + (x+5*y)+4)+z for x in range(6)] for y in range(2)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with simple case over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('repetition', 2))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [0.5*(sample_array[2*x]+sample_array[2*x+1]) for x in range(2)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."

        #
        #Test with case where block-size is not divisible over array size over samples:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('sample', 4))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[(0+1+2+3)*0.25+y+z for x in range(1)] for y in range(10)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with case where block-size is not divisible over array size over segments:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('segment', 3))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[1/3*((x+3*y) + (x+3*y)+1 + (x+3*y)+2)+z for x in range(6)] for y in range(3)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with case where block-size is not divisible over array size over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('repetition', 3))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [1/3*(sample_array[3*x]+sample_array[3*x+1]+sample_array[3*x+2]) for x in range(1)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."

        #
        #Test case where block-size is greater than array size over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('repetition', 5))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [1/4*(sample_array[4*x]+sample_array[4*x+1]+sample_array[4*x+2]+sample_array[4*x+3]) for x in range(1)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test case where block-size is equal to the array size over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorCPU('CPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_MeanBlock('repetition', 4))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [1/4*(sample_array[4*x]+sample_array[4*x+1]+sample_array[4*x+2]+sample_array[4*x+3]) for x in range(1)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."

        self.cleanup()

    def test_Integrate(self):
        self.initialise()
        data_size = 1024#*1024*4
        num_reps = 17
        num_segs = 4
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Integrate('sample'))
        new_proc.add_stage(CPU_Integrate('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) for x in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Integrate does not yield expected result."
        #
        #Test with another simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Integrate('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[( (num_segs**2+num_segs)*0.5 +2*r*num_segs)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Integrate does not yield expected result."
        #
        #Test with full contraction:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Integrate('sample'))
        new_proc.add_stage(CPU_Integrate('segment'))
        new_proc.add_stage_end(CPU_Integrate('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = 0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs)*num_reps + 2*0.5*(num_reps**2+num_reps)*num_segs )
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "CPU Integrate does not yield expected result."
        #Test with multiple-push
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Integrate('sample'))
        new_proc.add_stage(CPU_Integrate('segment'))
        new_proc.add_stage_end(CPU_Integrate('repetition'))
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,3)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(3,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = 0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs)*num_reps + 2*0.5*(num_reps**2+num_reps)*num_segs )
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "CPU Integrate does not yield expected result."
        self.cleanup()

    def test_Max(self):
        self.initialise()
        data_size = 1024#*1024*4
        num_reps = 10
        num_segs = 47
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            #Shuffle the list to make it interesting...
            'data' : { 'ch1' : np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Max('sample'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[(s+2*r)*data_size for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Max does not yield expected result."
        #
        #Test with another simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Max('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[(num_segs+2*r)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Max does not yield expected result."
        #
        #Test with full contraction
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            #Shuffle the list to make it interesting...
            'data' : { 'ch1' : np.array([[sorted([(s+24*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Max('sample'))
        new_proc.add_stage(CPU_Max('segment'))
        new_proc.add_stage_end(CPU_Max('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = (num_segs+24*num_reps)*data_size
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "CPU Max does not yield expected result."
        self.cleanup()

    def test_ConstantArithmetic(self):
        self.initialise()
        data_size = 1024#*1024*4
        num_reps = 10
        num_segs = 47
        #
        #Test with simple case:
        ops = ['+', '-', '*', '/', '%']
        opsMap = {
            '+' : operator.add,
            '-' : operator.sub,
            '*' : operator.mul,
            '/' : operator.truediv,  # use operator.div for Python 2
            '%' : operator.mod,
        }
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0 },
                'misc' : {'SampleRates' : [1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ConstantArithmetic(12,ops[m],None))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, 12)
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for operator: {ops[m]}."
        
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ConstantArithmetic(13,ops[m],None))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, 13)
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 13)
            assert self.arr_equality(fin_data['data']['ch2'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
         
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ConstantArithmetic(14,ops[m],[1]))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = leOrigArray
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 14)
            assert self.arr_equality(fin_data['data']['ch2'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
         
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0 },
                'misc' : {'SampleRates' : [1,1,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ConstantArithmetic(15,ops[m],[0,2]))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, 15)
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = leOrigArray2
            assert self.arr_equality(fin_data['data']['ch2'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray3, 15)
            assert self.arr_equality(fin_data['data']['ch3'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
        
        self.cleanup()

    def test_ChannelArithmetic(self):
        self.initialise()
        data_size = 512#*1024*4
        num_reps = 10
        num_segs = 47
        #
        #Test with simple case:
        ops = ['+', '-', '*', '/', '%']
        opsMap = {
            '+' : operator.add,
            '-' : operator.sub,
            '*' : operator.mul,
            '/' : operator.truediv,  # use operator.div for Python 2
            '%' : operator.mod,
        }

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([0,1],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray2)
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch2'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([0,0],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray)
            assert 'ch2' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch1'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,1]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0 },
                'misc' : {'SampleRates' : [1,5,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([0,2],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray3)
            assert 'ch2' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch3'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([5,1]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray4 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0, 'ch4' : leOrigArray4*1.0 },
                'misc' : {'SampleRates' : [1,5,2,5]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([1,3],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray2, leOrigArray4)
            assert 'ch1' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch3' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert not 'ch2' in fin_data['data'], "CPU Channel-Arithmetic did not delete a channel."
            assert not 'ch4' in fin_data['data'], "CPU Channel-Arithmetic did not delete a channel."
            assert self.arr_equality(fin_data['data'][f'ch2_{ops[m]}_ch4'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch3'], leOrigArray3), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,2,5]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        #Run same things again, but keeping input data...

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([0,1],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray2)
            assert 'ch1' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch2'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,1,1]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([0,0],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray)
            assert 'ch1' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch1'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,1,1]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0 },
                'misc' : {'SampleRates' : [1,5,1]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([0,2],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray3)
            assert 'ch1' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch3' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch3'], leOrigArray3), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch3'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,5,1,1]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray4 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0, 'ch4' : leOrigArray4*1.0 },
                'misc' : {'SampleRates' : [1,5,2,5]}
            }
            new_proc = ProcessorCPU('cpu_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(CPU_ChannelArithmetic([1,3],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray2, leOrigArray4)
            assert 'ch1' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch3' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch4' in fin_data['data'], "CPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch3'], leOrigArray3), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch4'], leOrigArray4), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2_{ops[m]}_ch4'], expected_ans), f"CPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"CPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,5,2,5,5]) ), f"CPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        self.cleanup()

    def test_FFT(self):
        self.initialise()

        #Test with 1 channel
        data_size = 1504#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_FFT())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['fft_real'], np.real(expected_ans)), "CPU FFT does not yield expected result."
        assert self.arr_equality_pct(fin_data['data']['fft_imag'], np.imag(expected_ans)), "CPU FFT does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "CPU FFT does not give right frequencies."
        
        #Test with 1 channel
        data_size = 1700#*1024*4
        num_reps = 1   #keep greater than 2
        num_segs = 1
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_FFT())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['fft_real'], np.real(expected_ans)), "CPU FFT does not yield expected result."
        assert self.arr_equality_pct(fin_data['data']['fft_imag'], np.imag(expected_ans)), "CPU FFT does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "CPU FFT does not give right frequencies."
        
        #Test with 2 channels
        data_size = 2048#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+5*r)*x**2 for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [10,10]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_FFT())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x + 1j*(s+5*r)*x**2 for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['fft_real'], np.real(expected_ans)), "CPU FFT does not yield expected result."
        assert self.arr_equality_pct(fin_data['data']['fft_imag'], np.imag(expected_ans)), "CPU FFT does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/10)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "CPU FFT does not give right frequencies."
        
        self.cleanup()

    def test_ESD(self):
        self.initialise()

        #Test with 1 channel
        data_size = 1504#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_ESD())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['esd'], np.abs(expected_ans)**2), "CPU ESD does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "CPU FFT does not give right frequencies."
        
        #Test with 1 channel
        data_size = 1700#*1024*4
        num_reps = 1   #keep greater than 2
        num_segs = 1
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_ESD())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['esd'], np.abs(expected_ans)**2), "CPU ESD does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "CPU FFT does not give right frequencies."
        
        #Test with 2 channels
        data_size = 2048#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+5*r)*x**2 for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [10,10]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_ESD())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x + 1j*(s+5*r)*x**2 for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['esd'], np.abs(expected_ans)**2), "CPU ESD does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/10)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "CPU FFT does not give right frequencies."

        self.cleanup()

    def test_Duplicate(self):
        self.initialise()

        data_size = 2048#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Duplicate([3]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1_0'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_1'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_2'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(np.array(fin_data['misc']['SampleRates']), np.array([1,1,1])), "CPU Duplicate does not yield expected result on sample rates."
        fin_data['data'].pop('ch1_0')
        fin_data['data'].pop('ch1_1')
        fin_data['data'].pop('ch1_2')
        assert len(fin_data['data'].keys()) == 0, "CPU Duplicate has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 5
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,3]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Duplicate([3,1]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1_0'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_1'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_2'], expected_ans), "CPU Duplicate does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(np.array(fin_data['misc']['SampleRates']), np.array([1,1,1,3])), "CPU Duplicate does not yield expected result on sample rates."
        fin_data['data'].pop('ch1_0')
        fin_data['data'].pop('ch1_1')
        fin_data['data'].pop('ch1_2')
        fin_data['data'].pop('ch2')
        assert len(fin_data['data'].keys()) == 0, "CPU Duplicate has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 13   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,4]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Duplicate([3,2]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1_0'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_1'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_2'], expected_ans), "CPU Duplicate does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch2_0'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch2_1'], expected_ans), "CPU Duplicate does not yield expected result."
        assert self.arr_equality(np.array(fin_data['misc']['SampleRates']), np.array([1,1,1,4,4])), "CPU Duplicate does not yield expected result on sample rates."
        fin_data['data'].pop('ch1_0')
        fin_data['data'].pop('ch1_1')
        fin_data['data'].pop('ch1_2')
        fin_data['data'].pop('ch2_0')
        fin_data['data'].pop('ch2_1')
        assert len(fin_data['data'].keys()) == 0, "CPU Duplicate has left superfluous data keys."

        self.cleanup()

    def test_Rename(self):
        self.initialise()

        data_size = 2048#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Rename(['mark']))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['mark'], expected_ans), "CPU Rename does not yield expected result."
        fin_data['data'].pop('mark')
        assert len(fin_data['data'].keys()) == 0, "CPU Duplicate has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 5
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,3]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Rename(['mark', 'space']))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['mark'], expected_ans), "CPU Rename does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['space'], expected_ans), "CPU Rename does not yield expected result."
        fin_data['data'].pop('mark')
        fin_data['data'].pop('space')
        assert len(fin_data['data'].keys()) == 0, "CPU Rename has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 5
        #
        #Test with permutation of names case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,3]}
        }
        new_proc = ProcessorCPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(CPU_Rename(['ch2', 'ch1']))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "CPU Rename does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Rename does not yield expected result."
        fin_data['data'].pop('ch2')
        fin_data['data'].pop('ch1')
        assert len(fin_data['data'].keys()) == 0, "CPU Rename has left superfluous data keys."

        self.cleanup()




class TestGPU(unittest.TestCase):
    ERR_TOL = 5e-5

    def initialise(self):
        self.lab = Laboratory('', 'test_save_dir/')
    
    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None
        shutil.rmtree('test_save_dir')

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL

    def arr_equality_pct(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)/np.abs(arr2 + 2*self.ERR_TOL)) < self.ERR_TOL
    
    def test_IQdemod(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"
        data_size = 1024#*1024*4
        omega = 2*np.pi*0.14
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000) + (np.random.rand(data_size)-0.5)*2*noise_level
        num_reps = 10
        num_segs = 4
        noise_level = 0.1
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase) + (np.random.rand(data_size)-0.5)*2*noise_level for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data },
            'misc' : {'SampleRates' : [1]}
        }
        #
        # import matplotlib.pyplot as plt
        # for r in range(num_reps):
        #     for s in range(num_segs):
        #         plt.plot(cur_data['data']['ch1'][r][s])
        # plt.show()
        # input('Press ENTER')
        #
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_DDC([0.14]))
        new_proc.add_stage(GPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
        new_proc.add_stage_end(GPU_Mean('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        mus = []
        sds = []
        for s in range(num_segs):
            data_envelope = np.sqrt(fin_data['data']['ch1_I'][s]**2 + fin_data['data']['ch1_Q'][s]**2)
            resids = data_envelope-ampl_envelope(num_segs-s,0.0)#[40:]
            mu, sd = np.mean(resids), np.std(resids)
            mus += [mu]
            sds += [sd]
            if INCLUDE_PLOTS:
                plt.plot(resids)
        if INCLUDE_PLOTS:
            plt.show()
        mus = np.array(mus)
        sds = np.array(sds)
        assert np.max(np.abs(mus)) < noise_level / np.sqrt(num_reps) * 2.56 * 4, "GPU Signal downconversion yields unsuitable results."
        assert np.max(np.abs(sds)) < noise_level / np.sqrt(num_reps) * 2.56 * 4, "GPU Signal downconversion yields unsuitable results."
        if INCLUDE_PLOTS:
            input('Press ENTER')
        self.cleanup()


    def test_IQddc(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"

        #Try simple test-case
        data_size = 1024#*1024*4
        f0 = 0.14
        omega = 2*np.pi*f0
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 10
        num_segs = 4
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase) for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data },
            'misc' : {'SampleRates' : [1]}
        }
        #
        new_proc = ProcessorGPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_DDC([f0]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase)*2.0*np.cos(omega*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "GPU DDC does not yield expected result for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega*np.arange(data_size)+phase)*-2.0*np.sin(omega*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "GPU DDC does not yield expected result for Q-channel."

        #Try with 2 channels
        data_size = 1024#*1024*4
        f0 = 0.29
        f1 = 0.11
        omega0 = 2*np.pi*f0
        omega1 = 2*np.pi*f1
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 13
        num_segs = 8
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase) for s in range(num_segs)] for r in range(num_reps)])
        raw_data2 = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase) for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data, 'ch2' : raw_data2 },
            'misc' : {'SampleRates' : [1, 1]}
        }
        #
        new_proc = ProcessorGPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_DDC([f0, f1]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*2.0*np.cos(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*-2.0*np.sin(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for Q-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*2.0*np.cos(omega1*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_I'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*-2.0*np.sin(omega1*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_Q'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for Q-channel."

        #Try with 2 channels and different sample rates
        data_size = 4536#*1024*4
        f0 = 0.29
        f1 = 0.11
        omega0 = 2*np.pi*f0
        omega1 = 2*np.pi*f1
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 11
        num_segs = 7
        phase = 3.0
        raw_data = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase) for s in range(num_segs)] for r in range(num_reps)])
        raw_data2 = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase) for s in range(num_segs)] for r in range(num_reps)])
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : raw_data, 'ch2' : raw_data2 },
            'misc' : {'SampleRates' : [1, 2]}
        }
        #
        new_proc = ProcessorGPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_DDC([f0, f1]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*2.0*np.cos(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs-s)*np.sin(omega0*np.arange(data_size)+phase)*-2.0*np.sin(omega0*np.arange(data_size)) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for Q-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*2.0*np.cos(omega1*np.arange(data_size)/2) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_I'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for I-channel."
        expected_ans = np.array([[ampl_envelope(num_segs+s)*np.sin(omega1*np.arange(data_size)-phase)*-2.0*np.sin(omega1*np.arange(data_size)/2) for s in range(num_segs)] for r in range(num_reps)])
        assert self.arr_equality(fin_data['data']['ch2_Q'], expected_ans), "GPU DDC does not yield expected result in the 2-channel case for Q-channel."

        #Try only 1 dimension
        data_size = 5424#*1024*4
        f0 = 0.14
        omega = 2*np.pi*f0
        def ampl_envelope(ampl, noise_level=1.0):
            return ampl * np.exp(-(np.arange(data_size)-200.0)**2/10000)
        num_reps = 10
        num_segs = 4
        phase = 3.0
        raw_data = ampl_envelope(num_segs)*np.sin(omega*np.arange(data_size)+phase)
        #
        cur_data = {
            'parameters' : ['sample'],
            'data' : { 'ch1' : raw_data },
            'misc' : {'SampleRates' : [1]}
        }
        #
        new_proc = ProcessorGPU('cpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_DDC([f0]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        #
        expected_ans = ampl_envelope(num_segs)*np.sin(omega*np.arange(data_size)+phase)*2.0*np.cos(omega*np.arange(data_size))
        assert self.arr_equality(fin_data['data']['ch1_I'], expected_ans), "GPU DDC does not yield expected result for I-channel."
        expected_ans = ampl_envelope(num_segs)*np.sin(omega*np.arange(data_size)+phase)*-2.0*np.sin(omega*np.arange(data_size))
        assert self.arr_equality(fin_data['data']['ch1_Q'], expected_ans), "GPU DDC does not yield expected result for Q-channel."

        self.cleanup()

    def test_Mean(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"
        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Mean('sample'))
        new_proc.add_stage(GPU_Mean('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) / (data_size * num_segs) for x in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
        #Test with multiple-push
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Mean('sample'))
        new_proc.add_stage(GPU_Mean('segment'))
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,3)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(3,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) / (data_size * num_segs) for x in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
        #
        #Test with another simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Mean('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[( (num_segs**2+num_segs)*0.5 +2*r*num_segs)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)]) / num_segs
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
        #Test with multiple-push
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Mean('segment'))
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,3)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(3,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[( (num_segs**2+num_segs)*0.5 +2*r*num_segs)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)]) / num_segs
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
        #
        #Test with full contraction:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Mean('sample'))
        new_proc.add_stage(GPU_Mean('segment'))
        new_proc.add_stage_end(GPU_Mean('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = 0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs)*num_reps + 2*0.5*(num_reps**2+num_reps)*num_segs ) / (data_size * num_segs * num_reps)
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "GPU Mean does not yield expected result."
        self.cleanup()

    def test_MeanBlock(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"

        sample_array = [[[x+y+z for x in range(6)] for y in range(10)] for z in range(4)]
        sample_array = np.array(sample_array)

        num_reps, num_segs, num_smpls = sample_array.shape
        #
        #Test with simple case over samples:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('sample', 2))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[(2*x+0.5)+y+z for x in range(3)] for y in range(10)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with simple case over segments:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('segment', 5))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[0.2*((x+5*y) + (x+5*y)+1 + (x+5*y)+2 + (x+5*y)+3 + (x+5*y)+4)+z for x in range(6)] for y in range(2)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with simple case over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('repetition', 2))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [0.5*(sample_array[2*x]+sample_array[2*x+1]) for x in range(2)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."

        #
        #Test with case where block-size is not divisible over array size over samples:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('sample', 4))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[(0+1+2+3)*0.25+y+z for x in range(1)] for y in range(10)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with case where block-size is not divisible over array size over segments:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('segment', 3))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [[[1/3*((x+3*y) + (x+3*y)+1 + (x+3*y)+2)+z for x in range(6)] for y in range(3)] for z in range(4)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test with case where block-size is not divisible over array size over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('repetition', 3))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [1/3*(sample_array[3*x]+sample_array[3*x+1]+sample_array[3*x+2]) for x in range(1)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."

        #
        #Test case where block-size is greater than array size over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('repetition', 5))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [1/4*(sample_array[4*x]+sample_array[4*x+1]+sample_array[4*x+2]+sample_array[4*x+3]) for x in range(1)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."
        #
        #Test case where block-size is equal to the array size over repetitions:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : sample_array*1.0, 'ch2' : sample_array*2.0 },
            'misc' : {'SampleRates' : [1,1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_MeanBlock('repetition', 4))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = [1/4*(sample_array[4*x]+sample_array[4*x+1]+sample_array[4*x+2]+sample_array[4*x+3]) for x in range(1)]
        assert self.arr_equality(fin_data['data']['ch1'], np.array(expected_ans)), "GPU MeanBlock does not yield expected result."
        expected_ans = np.array(expected_ans)*2.0
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU MeanBlock does not yield expected result."

        self.cleanup()

    def test_Integrate(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"
        data_size = 1024#*1024*4
        num_reps = 17
        num_segs = 4
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Integrate('sample'))
        new_proc.add_stage(GPU_Integrate('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) for x in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Integrate does not yield expected result."
        #
        #Test with another simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Integrate('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[( (num_segs**2+num_segs)*0.5 +2*r*num_segs)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Integrate does not yield expected result."
        #
        #Test with full contraction:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Integrate('sample'))
        new_proc.add_stage(GPU_Integrate('segment'))
        new_proc.add_stage_end(GPU_Integrate('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = 0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs)*num_reps + 2*0.5*(num_reps**2+num_reps)*num_segs )
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "GPU Integrate does not yield expected result."
        #Test with multiple-push
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Integrate('sample'))
        new_proc.add_stage(GPU_Integrate('segment'))
        new_proc.add_stage_end(GPU_Integrate('repetition'))
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,3)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(3,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = 0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs)*num_reps + 2*0.5*(num_reps**2+num_reps)*num_segs )
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "GPU Integrate does not yield expected result."
        self.cleanup()

    def test_Max(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"
        data_size = 1024#*1024*4
        num_reps = 10
        num_segs = 47
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            #Shuffle the list to make it interesting...
            'data' : { 'ch1' : np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Max('sample'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[(s+2*r)*data_size for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Max does not yield expected result."
        #
        #Test with another simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Max('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[(num_segs+2*r)*x for x in range(1,data_size+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "GPU Max does not yield expected result."
        #
        #Test with full contraction
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            #Shuffle the list to make it interesting...
            'data' : { 'ch1' : np.array([[sorted([(s+24*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Max('sample'))
        new_proc.add_stage(GPU_Max('segment'))
        new_proc.add_stage_end(GPU_Max('repetition'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = (num_segs+24*num_reps)*data_size
        assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "GPU Max does not yield expected result."
        self.cleanup()

    def test_ConstantArithmetic(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"
        data_size = 1024#*1024*4
        num_reps = 10
        num_segs = 47
        #
        #Test with simple case:
        ops = ['+', '-', '*', '/', '%']
        opsMap = {
            '+' : operator.add,
            '-' : operator.sub,
            '*' : operator.mul,
            '/' : operator.truediv,  # use operator.div for Python 2
            '%' : operator.mod,
        }
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0 },
                'misc' : {'SampleRates' : [1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ConstantArithmetic(12,ops[m],None))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, 12)
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for operator: {ops[m]}."
        
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ConstantArithmetic(13,ops[m],None))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, 13)
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 13)
            assert self.arr_equality(fin_data['data']['ch2'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
         
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ConstantArithmetic(14,ops[m],[1]))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = leOrigArray
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 14)
            assert self.arr_equality(fin_data['data']['ch2'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
         
        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0 },
                'misc' : {'SampleRates' : [1,1,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ConstantArithmetic(15,ops[m],[0,2]))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, 15)
            assert self.arr_equality(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = leOrigArray2
            assert self.arr_equality(fin_data['data']['ch2'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray3, 15)
            assert self.arr_equality(fin_data['data']['ch3'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
        
        self.cleanup()

    def test_ChannelArithmetic(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"
        data_size = 512#*1024*4
        num_reps = 10
        num_segs = 47
        #
        #Test with simple case:
        ops = ['+', '-', '*', '/', '%']
        opsMap = {
            '+' : operator.add,
            '-' : operator.sub,
            '*' : operator.mul,
            '/' : operator.truediv,  # use operator.div for Python 2
            '%' : operator.mod,
        }

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([0,1],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray2)
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch2'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([0,0],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray)
            assert 'ch2' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch1'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,1]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0 },
                'misc' : {'SampleRates' : [1,5,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([0,2],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray3)
            assert 'ch2' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch3'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([5,1]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray4 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0, 'ch4' : leOrigArray4*1.0 },
                'misc' : {'SampleRates' : [1,5,2,5]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([1,3],ops[m],True))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray2, leOrigArray4)
            assert 'ch1' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch3' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert not 'ch2' in fin_data['data'], "GPU Channel-Arithmetic did not delete a channel."
            assert not 'ch4' in fin_data['data'], "GPU Channel-Arithmetic did not delete a channel."
            assert self.arr_equality(fin_data['data'][f'ch2_{ops[m]}_ch4'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch3'], leOrigArray3), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,2,5]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        #Run same things again, but keeping input data...

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([0,1],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray2)
            assert 'ch1' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch2'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,1,1]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0 },
                'misc' : {'SampleRates' : [1,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([0,0],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray)
            assert 'ch1' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch1'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,1,1]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0 },
                'misc' : {'SampleRates' : [1,5,1]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([0,2],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, leOrigArray3)
            assert 'ch1' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch3' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch3'], leOrigArray3), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1_{ops[m]}_ch3'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,5,1,1]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        for m in range(len(ops)):
            leOrigArray = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray2 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray3 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            leOrigArray4 = np.array([[sorted([(s+2*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
            cur_data = {
                'parameters' : ['repetition', 'segment', 'sample'],
                #Shuffle the list to make it interesting...
                'data' : { 'ch1' : leOrigArray*1.0, 'ch2' : leOrigArray2*1.0, 'ch3' : leOrigArray3*1.0, 'ch4' : leOrigArray4*1.0 },
                'misc' : {'SampleRates' : [1,5,2,5]}
            }
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ChannelArithmetic([1,3],ops[m],False))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray2, leOrigArray4)
            assert 'ch1' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch2' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch3' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert 'ch4' in fin_data['data'], "GPU Channel-Arithmetic incorrectly deleted a channel."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2'], leOrigArray2), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch3'], leOrigArray3), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch4'], leOrigArray4), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch2_{ops[m]}_ch4'], expected_ans), f"GPU Channel-Arithmetic does not yield expected result for operator: {ops[m]}."
            assert self.arr_equality(fin_data['data'][f'ch1'], leOrigArray), f"GPU Channel-Arithmetic modified wrong channel when using operator: {ops[m]}."
            assert self.arr_equality( np.array(fin_data['misc']['SampleRates']), np.array([1,5,2,5,5]) ), f"GPU Channel-Arithmetic did not settle SampleRates properly when using operator: {ops[m]}."

        self.cleanup()

    def test_FFT(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"

        #Test with 1 channel
        data_size = 1504#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorGPU('gpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_FFT())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['fft_real'], np.real(expected_ans)), "GPU FFT does not yield expected result."
        assert self.arr_equality_pct(fin_data['data']['fft_imag'], np.imag(expected_ans)), "GPU FFT does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "GPU FFT does not give right frequencies."

        #Test with 1 channel
        data_size = 1700#*1024*4
        num_reps = 1   #keep greater than 2
        num_segs = 1
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorGPU('gpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_FFT())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['fft_real'], np.real(expected_ans)), "GPU FFT does not yield expected result."
        assert self.arr_equality_pct(fin_data['data']['fft_imag'], np.imag(expected_ans)), "GPU FFT does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "GPU FFT does not give right frequencies."

        #Test with 2 channels
        data_size = 2048#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+5*r)*x**2 for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [10,10]}
        }
        new_proc = ProcessorGPU('gpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_FFT())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x + 1j*(s+5*r)*x**2 for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['fft_real'], np.real(expected_ans)), "GPU FFT does not yield expected result."
        assert self.arr_equality_pct(fin_data['data']['fft_imag'], np.imag(expected_ans)), "GPU FFT does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/10)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "GPU FFT does not give right frequencies."
        
        self.cleanup()

    def test_ESD(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"

        #Test with 1 channel
        data_size = 1501#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_ESD())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['esd'], np.abs(expected_ans)**2), "GPU ESD does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "GPU FFT does not give right frequencies."
        
        #Test with 1 channel
        data_size = 2048#*1024*4
        num_reps = 1   #keep greater than 2
        num_segs = 1
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [15]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_ESD())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['esd'], np.abs(expected_ans)**2), "GPU ESD does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/15)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "GPU FFT does not give right frequencies."
        
        #Test with 2 channels
        data_size = 705#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+5*r)*x**2 for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [10,10]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_ESD())
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[np.fft.fft([(s+2*r)*x + 1j*(s+5*r)*x**2 for x in range(1,data_size+1)]) for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality_pct(fin_data['data']['esd'], np.abs(expected_ans)**2), "GPU ESD does not yield expected result."
        expected_ans = np.fft.fftfreq(data_size, 1.0/10)
        assert self.arr_equality(fin_data['parameter_values']['fft_frequency'], expected_ans), "GPU FFT does not give right frequencies."

        self.cleanup()

    def test_Duplicate(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"

        data_size = 2048#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Duplicate([3]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1_0'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_1'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_2'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(np.array(fin_data['misc']['SampleRates']), np.array([1,1,1])), "GPU Duplicate does not yield expected result on sample rates."
        fin_data['data'].pop('ch1_0')
        fin_data['data'].pop('ch1_1')
        fin_data['data'].pop('ch1_2')
        assert len(fin_data['data'].keys()) == 0, "GPU Duplicate has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 5
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,3]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Duplicate([3,1]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1_0'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_1'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_2'], expected_ans), "GPU Duplicate does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(np.array(fin_data['misc']['SampleRates']), np.array([1,1,1,3])), "GPU Duplicate does not yield expected result on sample rates."
        fin_data['data'].pop('ch1_0')
        fin_data['data'].pop('ch1_1')
        fin_data['data'].pop('ch1_2')
        fin_data['data'].pop('ch2')
        assert len(fin_data['data'].keys()) == 0, "GPU Duplicate has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 13   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,4]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Duplicate([3,2]))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1_0'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_1'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch1_2'], expected_ans), "GPU Duplicate does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch2_0'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(fin_data['data']['ch2_1'], expected_ans), "GPU Duplicate does not yield expected result."
        assert self.arr_equality(np.array(fin_data['misc']['SampleRates']), np.array([1,1,1,4,4])), "GPU Duplicate does not yield expected result on sample rates."
        fin_data['data'].pop('ch1_0')
        fin_data['data'].pop('ch1_1')
        fin_data['data'].pop('ch1_2')
        fin_data['data'].pop('ch2_0')
        fin_data['data'].pop('ch2_1')
        assert len(fin_data['data'].keys()) == 0, "GPU Duplicate has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 5
        #
        #Test with permutation of names case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,3]}
        }
        new_proc = ProcessorGPU('gpu_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Rename(['ch2', 'ch1']))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch2'], expected_ans), "CPU Rename does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['ch1'], expected_ans), "CPU Rename does not yield expected result."
        fin_data['data'].pop('ch2')
        fin_data['data'].pop('ch1')
        assert len(fin_data['data'].keys()) == 0, "CPU Rename has left superfluous data keys."

        self.cleanup()

    def test_Rename(self):
        self.initialise()
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            assert False, "GPU Processor could not be initialised - has CuPy been installed?"

        data_size = 2048#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 6
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Rename(['mark']))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['mark'], expected_ans), "GPU Rename does not yield expected result."
        fin_data['data'].pop('mark')
        assert len(fin_data['data'].keys()) == 0, "GPU Rename has left superfluous data keys."

        data_size = 1024#*1024*4
        num_reps = 10   #keep greater than 2
        num_segs = 5
        #
        #Test with simple case:
        cur_data = {
            'parameters' : ['repetition', 'segment', 'sample'],
            'data' : {  'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]),
                        'ch2' : np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
            'misc' : {'SampleRates' : [1,3]}
        }
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Rename(['mark', 'space']))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['mark'], expected_ans), "GPU Rename does not yield expected result."
        expected_ans = np.array([[[(s+4*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert self.arr_equality(fin_data['data']['space'], expected_ans), "GPU Rename does not yield expected result."
        fin_data['data'].pop('mark')
        fin_data['data'].pop('space')
        assert len(fin_data['data'].keys()) == 0, "GPU Rename has left superfluous data keys."

        self.cleanup()


class TestFPGA(unittest.TestCase):
    def initialise(self):
        self.lab = Laboratory('', 'test_save_dir/')
    
    def cleanup(self):
        self.lab.release_all_instruments()
        self.lab = None
        shutil.rmtree('test_save_dir')

    def arr_equality(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)) < self.ERR_TOL

    def arr_equality_pct(self, arr1, arr2):
        if arr1.size != arr2.size:
            return False
        return np.max(np.abs(arr1 - arr2)/np.abs(arr2 + 2*self.ERR_TOL)) < self.ERR_TOL
    
    def test_reprogram(self):
        self.initialise()
        test_proc = ProcessorFPGA('test',self.lab)

        self.lab.PROC('test').reset_pipeline()
        self.lab.PROC('test').add_stage(FPGA_DDC([[105e6],[100e6]]))
        self.lab.PROC('test').add_stage(FPGA_Decimation('sample', 10))

        leState = self.lab.PROC('test').get_pipeline_state()
        assert self.lab.PROC('test').compare_pipeline_state(leState), "FPGA processor reprogramming check failed when there were no changes made."

        self.lab.PROC('test').add_stage(FPGA_Integrate('sample'))
        assert not self.lab.PROC('test').compare_pipeline_state(leState), "FPGA processor reprogramming check failed when changes were made."

        self.lab.PROC('test').reset_pipeline()
        self.lab.PROC('test').add_stage(FPGA_DDC([[105e6],[100e6]]))
        self.lab.PROC('test').add_stage(FPGA_Decimation('sample', 10))
        assert self.lab.PROC('test').compare_pipeline_state(leState), "FPGA processor reprogramming check failed when there were no changes made."

        self.lab.PROC('test').reset_pipeline()
        self.lab.PROC('test').add_stage(FPGA_DDC([[105e6],[100e6]]))
        self.lab.PROC('test').add_stage(FPGA_Decimation('sample', 20))
        assert not self.lab.PROC('test').compare_pipeline_state(leState), "FPGA processor reprogramming check failed when changes were made."

        self.cleanup()

if __name__ == '__main__':
    TestGPU().test_ESD()
    # TestFPGA().test_reprogram()
    unittest.main()
