from  sqdtoolz.HAL.ACQProcessor import ACQProcessor
from multiprocessing.pool import ThreadPool
import numpy as np

class ProcNodeCPU:
    def __init__(self):
        pass

    def input_format(self):
        raise NotImplementedError()

    def output_format(self):
        raise NotImplementedError()

    def process_data(self, data_pkt):
        raise NotImplementedError()


class ProcessorCPU(ACQProcessor):
    def __init__(self):
        self.tp_CPU = ThreadPool(processes=1)
        self.cur_async_handle = None

        self.pipeline = []
        self.cur_data_queue = []
        self.cur_data_processed = []

    def push_data(self, data_pkt):
        self.cur_data_queue.append(data_pkt)
        Start a new thread - otherwise, the thread will automatically check and pop the new array for processing
        if self.cur_async_handle == None:
            self.cur_async_handle = self.tp_GPU.apply_async(self._process_all)
        elif self.cur_async_handle.ready():
            self.cur_async_handle = self.tp_GPU.apply_async(self._process_all)
        # self._process_all()

    def get_all_data(self):
        #Wait until ready
        while not self.ready():
            continue

        if len(self.cur_data_processed) == 0:
            return None
        
        #Concatenate the individual data packets
        ret_data = self.cur_data_processed[0]
        for cur_ch in ret_data['data'].keys():
            ret_data['data'][cur_ch] = np.concatenate( [cur_data['data'][cur_ch] for cur_data in self.cur_data_processed] )

        del self.cur_data_processed
        self.cur_data_processed = []

        return ret_data

    def ready(self):
        if self.cur_async_handle == None:
            return True
        return self.cur_async_handle.ready()

    def _process_all(self):
        while (len(self.cur_data_queue) > 0):
            cur_data = self.cur_data_queue.pop(0)
            
            #Run the processes
            for cur_proc in self.pipeline:
                cur_data = cur_proc.process_data(cur_data)
            
            self.cur_data_processed.append(cur_data)


    def reset_pipeline(self):
        self.pipeline.clear()

    def add_stage(self, ProcNodeCPUobj):
        self.pipeline.append(ProcNodeCPUobj)


# from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
# from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
# from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
# def runme():
#     new_proc = ProcessorCPU()
#     new_proc.add_stage(CPU_DDC([0.1]))
#     new_proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 0.01, 'Win' : 'hamming'}]*2))

#     data_size = 1024#*1024*4
#     omega = 2*np.pi*0.1
#     data = np.exp(-(np.arange(data_size)-200.0)**2/10000)*np.sin(omega*np.arange(data_size)+1.5+1.5)
#     num_reps = 3
#     num_segs = 4
#     raw_data = np.hstack([data]*(num_reps*num_segs)).reshape(num_reps,num_segs,data.size)

#     cur_data = {
#         'parameters' : ['repetition', 'segment', 'sample'],
#         'data' : { 'ch1' : raw_data },
#         'misc' : {'SampleRates' : [1]}
#     }

#     new_proc.push_data(cur_data)
#     fin_data = new_proc.get_all_data()

#     import matplotlib.pyplot as plt
#     # print(dataIQ[-1])
#     plt.plot(fin_data['data']['ch1_I'][0][0])
#     plt.plot(fin_data['data']['ch1_Q'][0][0])
#     plt.plot(data)
#     plt.show()

#     input('Press ENTER')

#     cur_data = {
#         'parameters' : ['repetition', 'segment', 'sample'],
#         'data' : { 'ch1' : raw_data },
#         'misc' : {'SampleRates' : [1]}
#     }

#     new_proc.add_stage(CPU_Mean('repetition'))
#     new_proc.push_data(cur_data)
#     fin_data = new_proc.get_all_data()

#     input('Press ENTER')


# if __name__ == '__main__':
#     runme()
