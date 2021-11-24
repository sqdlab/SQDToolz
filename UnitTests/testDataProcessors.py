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

import random
import matplotlib.pyplot as plt

INCLUDE_PLOTS = False

import shutil

import unittest

import operator #for ConstantArithmetic

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
        assert np.max(np.abs(mus)) < noise_level / np.sqrt(num_reps) * 2.56, "CPU Signal downconversion yields unsuitable results."
        assert np.max(np.abs(sds)) < noise_level / np.sqrt(num_reps) * 2.56, "CPU Signal downconversion yields unsuitable results."
        if INCLUDE_PLOTS:
            input('Press ENTER')
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Mean does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Integrate does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Integrate does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Max does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "CPU Max does not yield expected result."
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
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for operator: {ops[m]}."
        
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
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 13)
            assert np.array_equal(fin_data['data']['ch2'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
         
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
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 14)
            assert np.array_equal(fin_data['data']['ch2'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
         
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
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = leOrigArray2
            assert np.array_equal(fin_data['data']['ch2'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray3, 15)
            assert np.array_equal(fin_data['data']['ch3'], expected_ans), f"CPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
        
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




class TestGPU(unittest.TestCase):
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
    
    def test_IQdemod(self):
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            return
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
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.add_stage(GPU_DDC([0.14]))
        new_proc.add_stage(GPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
        new_proc.add_stage_end(GPU_Mean('repetition'))
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
        assert np.max(np.abs(mus)) < noise_level / np.sqrt(num_reps) * 2.56, "GPU Signal downconversion yields unsuitable results."
        assert np.max(np.abs(sds)) < noise_level / np.sqrt(num_reps) * 2.56, "GPU Signal downconversion yields unsuitable results."
        if INCLUDE_PLOTS:
            input('Press ENTER')
        self.cleanup()

    def test_Mean(self):
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            return
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
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Mean('sample'))
        new_proc.add_stage(GPU_Mean('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) / (data_size * num_segs) for x in range(1,num_reps+1)])
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Mean does not yield expected result."
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

    def test_Integrate(self):
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            return
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
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Integrate('sample'))
        new_proc.add_stage(GPU_Integrate('segment'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([0.5*(data_size**2+data_size) * ( 0.5*(num_segs**2+num_segs) + 2*x*num_segs ) for x in range(1,num_reps+1)])
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Integrate does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Integrate does not yield expected result."
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
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            return
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
        new_proc = ProcessorGPU('GPU_test', self.lab)
        new_proc.reset_pipeline()
        new_proc.add_stage(GPU_Max('sample'))
        new_proc.push_data(cur_data)
        fin_data = new_proc.get_all_data()
        expected_ans = np.array([[(s+2*r)*data_size for s in range(1,num_segs+1)] for r in range(1,num_reps+1)])
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Max does not yield expected result."
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
        assert np.array_equal(fin_data['data']['ch1'], expected_ans), "GPU Max does not yield expected result."
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
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            return
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
            new_proc = ProcessorGPU('GPU_test', self.lab)
            new_proc.reset_pipeline()
            new_proc.add_stage(GPU_ConstantArithmetic(12,ops[m],None))
            new_proc.push_data(cur_data)
            fin_data = new_proc.get_all_data()
            expected_ans = opsMap[ops[m]](leOrigArray, 12)
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for operator: {ops[m]}."
        
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
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 13)
            assert np.array_equal(fin_data['data']['ch2'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for global multi-channel application for operator: {ops[m]}."
         
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
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray2, 14)
            assert np.array_equal(fin_data['data']['ch2'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
         
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
            assert np.array_equal(fin_data['data']['ch1'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = leOrigArray2
            assert np.array_equal(fin_data['data']['ch2'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
            expected_ans = opsMap[ops[m]](leOrigArray3, 15)
            assert np.array_equal(fin_data['data']['ch3'], expected_ans), f"GPU Constant-Arithmetic does not yield expected result for multi-channel application for operator: {ops[m]}."
        
        self.cleanup()

    def test_ChannelArithmetic(self):
        try:
            test_proc = ProcessorGPU('test',self.lab)
        except:
            return
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




if __name__ == '__main__':
    unittest.main()