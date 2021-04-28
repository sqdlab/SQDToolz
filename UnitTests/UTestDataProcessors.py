from sqdtoolz.Laboratory import*

from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
from sqdtoolz.HAL.Processors.CPU.CPU_Integrate import*
from sqdtoolz.HAL.Processors.CPU.CPU_Max import*

from sqdtoolz.HAL.Processors.ProcessorGPU import*
from sqdtoolz.HAL.Processors.GPU.GPU_DDC import*
from sqdtoolz.HAL.Processors.GPU.GPU_FIR import*
from sqdtoolz.HAL.Processors.GPU.GPU_Mean import*
from sqdtoolz.HAL.Processors.GPU.GPU_Integrate import*
from sqdtoolz.HAL.Processors.GPU.GPU_Max import*

import random

import matplotlib.pyplot as plt

new_lab = Laboratory('', 'savedir')

INCLUDE_PLOTS = False
TEST_CPU = True
TEST_GPU = True

###################################################
####################TESTING CPU####################

if TEST_CPU:
    #
    #TESTING DDC WITH FALSE DATA
    #
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
    new_proc = ProcessorCPU('cpu_test', new_lab)
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

    #
    #TESTING MEAN
    #
    num_reps = 10   #keep greater than 2
    num_segs = 6
    #
    #Test with simple case:
    cur_data = {
        'parameters' : ['repetition', 'segment', 'sample'],
        'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
        'misc' : {'SampleRates' : [1]}
    }
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

    #
    #TESTING INTEGRATE
    #
    num_reps = 17
    num_segs = 4
    #
    #Test with simple case:
    cur_data = {
        'parameters' : ['repetition', 'segment', 'sample'],
        'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
        'misc' : {'SampleRates' : [1]}
    }
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

    #
    #TESTING MAX
    #
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


###################################################
####################TESTING GPU####################

if TEST_GPU:
    #
    #TESTING DDC WITH FALSE DATA
    #
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
    new_proc = ProcessorGPU('gpu_test', new_lab)
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

    #
    #TESTING MEAN
    #
    num_reps = 10
    num_segs = 6
    #
    #Test with simple case:
    cur_data = {
        'parameters' : ['repetition', 'segment', 'sample'],
        'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
        'misc' : {'SampleRates' : [1]}
    }
    new_proc.reset_pipeline()
    new_proc.add_stage(GPU_Mean('sample'))
    new_proc.add_stage(GPU_Mean('segment'))
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

    #
    #TESTING INTEGRATE
    #
    num_reps = 17
    num_segs = 4
    #
    #Test with simple case:
    cur_data = {
        'parameters' : ['repetition', 'segment', 'sample'],
        'data' : { 'ch1' : np.array([[[(s+2*r)*x for x in range(1,data_size+1)] for s in range(1,num_segs+1)] for r in range(1,num_reps+1)]) },
        'misc' : {'SampleRates' : [1]}
    }
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

    #
    #TESTING MAX
    #
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
    #Test with multiple-push
    new_proc.reset_pipeline()
    new_proc.add_stage(GPU_Max('sample'))
    new_proc.add_stage(GPU_Max('segment'))
    new_proc.add_stage_end(GPU_Max('repetition'))
    cur_data = {
        'parameters' : ['repetition', 'segment', 'sample'],
        #Shuffle the list to make it interesting...
        'data' : { 'ch1' : np.array([[sorted([(s+24*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(1,3)]) },
        'misc' : {'SampleRates' : [1]}
    }
    new_proc.push_data(cur_data)
    cur_data = {
        'parameters' : ['repetition', 'segment', 'sample'],
        #Shuffle the list to make it interesting...
        'data' : { 'ch1' : np.array([[sorted([(s+24*r)*x for x in range(1,data_size+1)], key=lambda k: random.random()) for s in range(1,num_segs+1)] for r in range(3,num_reps+1)]) },
        'misc' : {'SampleRates' : [1]}
    }
    new_proc.push_data(cur_data)
    fin_data = new_proc.get_all_data()
    expected_ans = (num_segs+24*num_reps)*data_size
    assert np.abs(expected_ans - fin_data['data']['ch1']) < 1e-16, "GPU Max does not yield expected result."



#########################################################
####################TESTING SAVE/LOAD####################

if TEST_CPU:
    #Basic one to check nothing goes wrong...
    new_proc = new_lab.PROC('cpu_test')
    new_proc.reset_pipeline()
    new_proc.add_stage(CPU_DDC([0.14]))
    new_proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
    new_proc.add_stage(CPU_Max('sample'))
    new_proc.add_stage(CPU_Mean('segment'))
    new_proc.add_stage_end(CPU_Max('repetition'))
    #
    new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration_procs.txt')
    #
    new_lab._station.close_all_registered_instruments()
    new_lab = Laboratory('', 'savedir')
    with open("UnitTests/laboratory_configuration_procs.txt") as json_file:
        data = json.load(json_file)
        new_lab.cold_reload_labconfig(data)
    new_proc = new_lab.PROC('cpu_test')

    #Testing with actual datsets...
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
    new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration_procs.txt')
    #
    new_lab._station.close_all_registered_instruments()
    new_lab = Laboratory('', 'savedir')
    with open("UnitTests/laboratory_configuration_procs.txt") as json_file:
        data = json.load(json_file)
        new_lab.cold_reload_labconfig(data)
    new_proc = new_lab.PROC('cpu_test')
    #
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

if TEST_GPU:
    #Basic one to check nothing goes wrong...
    new_proc = ProcessorGPU('gpu_test', new_lab)
    new_proc.reset_pipeline()
    new_proc.add_stage(GPU_DDC([0.14]))
    new_proc.add_stage(GPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))
    new_proc.add_stage(GPU_Max('sample'))
    new_proc.add_stage(GPU_Mean('segment'))
    new_proc.add_stage_end(GPU_Max('repetition'))
    #
    new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration_procs.txt')
    #
    new_lab._station.close_all_registered_instruments()
    new_lab = Laboratory('', 'savedir')
    with open("UnitTests/laboratory_configuration_procs.txt") as json_file:
        data = json.load(json_file)
        new_lab.cold_reload_labconfig(data)
    new_proc = new_lab.PROC('gpu_test')

    #Testing with actual datsets...
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
    new_lab.save_laboratory_config('UnitTests/', 'laboratory_configuration_procs.txt')
    #
    new_lab._station.close_all_registered_instruments()
    new_lab = Laboratory('', 'savedir')
    with open("UnitTests/laboratory_configuration_procs.txt") as json_file:
        data = json.load(json_file)
        new_lab.cold_reload_labconfig(data)
    new_proc = new_lab.PROC('gpu_test')
    #
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

print("Data Processor Unit Tests completed successfully.")
