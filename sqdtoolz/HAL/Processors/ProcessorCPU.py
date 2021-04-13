from  sqdtoolz.HAL.ACQProcessor import ACQProcessor
from multiprocessing.pool import ThreadPool
import queue
import numpy as np

class ProcNodeCPU:
    def __init__(self):
        pass

    def input_format(self):
        raise NotImplementedError()

    def output_format(self):
        raise NotImplementedError()

    def process_data(self, data_pkt, **kwargs):
        raise NotImplementedError()


class ProcessorCPU(ACQProcessor):
    def __init__(self):
        self.tp_CPU = ThreadPool(processes=1)
        self.cur_async_handle = None

        self.pipeline = []
        self.pipeline_end = []
        self.cur_data_queue = queue.Queue()
        self.cur_data_processed = []

    def push_data(self, data_pkt):
        self.cur_data_queue.put(data_pkt)
        #Start a new thread - otherwise, the thread will automatically check and pop the new array for processing
        # if self.cur_async_handle == None:
        #     self.cur_async_handle = self.tp_CPU.apply_async(self._process_all)
        # elif self.cur_async_handle.ready():
        #     self.cur_async_handle = self.tp_CPU.apply_async(self._process_all)
        # self._process_all()

    def get_all_data(self):
        #Wait until ready
        # while not self.ready():
        #     continue
        #Empty the queue just in case...
        self._process_all()

        if len(self.cur_data_processed) == 0:
            return None

        #Concatenate the individual data packets
        ret_data = self.cur_data_processed[0]
        #Loop through each channel
        for cur_ch in ret_data['data'].keys():
            #For each channel, take the associated data array from each cached processed data
            dataarrays = [cur_data['data'][cur_ch] for cur_data in self.cur_data_processed]
            #Concatenate the data arrays while checking if the result is a singleton...
            if type(dataarrays[0]) is np.ndarray:
                ret_data['data'][cur_ch] = np.concatenate( dataarrays )
            else:
                assert len(dataarrays) == 1, "There is some operation (e.g. average across all repetitions) that produces a singleton. Processing is pipelined and not global. Ensure that such operations are added using add_stage_end instead of add_stage."
                #Should only arrive here if it happens to be one repetition for example (i.e. on passing through all packets, it is still a single singleton)
                ret_data['data'][cur_ch] = dataarrays[0]

        #Run the processes that are to occur on the entire collated dataset
        for cur_proc in self.pipeline_end:
            ret_data = cur_proc.process_data(ret_data, end_stage=True)

        if len(self.cur_data_processed) > 1:
            for cur_arr in self.cur_data_processed[1:]:
                del cur_arr
        self.cur_data_processed = []

        return ret_data

    def ready(self):
        if self.cur_async_handle == None:
            return True
        return self.cur_async_handle.ready()

    def _process_all(self):
        while not self.cur_data_queue.empty():
            cur_data = self.cur_data_queue.get()
            
            #Run the processes
            for cur_proc in self.pipeline:
                cur_data = cur_proc.process_data(cur_data)
            
            self.cur_data_processed.append(cur_data)


    def reset_pipeline(self):
        self.pipeline.clear()

    def add_stage(self, ProcNodeCPUobj):
        self.pipeline.append(ProcNodeCPUobj)

    def add_stage_end(self, ProcNodeCPUobj):
        self.pipeline_end.append(ProcNodeCPUobj)


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
