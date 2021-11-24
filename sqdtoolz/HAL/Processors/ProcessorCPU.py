from  sqdtoolz.HAL.DataProcessor import DataProcessor
from multiprocessing.pool import ThreadPool
import queue
import numpy as np

class ProcNodeCPU:
    def __init__(self):
        pass

    def process_data(self, data_pkt, **kwargs):
        raise NotImplementedError()

    def _get_current_config(self):
        raise NotImplementedError()

from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Integrate import*
from sqdtoolz.HAL.Processors.CPU.CPU_Max import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
from sqdtoolz.HAL.Processors.CPU.CPU_Duplicate import*
from sqdtoolz.HAL.Processors.CPU.CPU_Slice import*
from sqdtoolz.HAL.Processors.CPU.CPU_Rename import*
from sqdtoolz.HAL.Processors.CPU.CPU_ChannelArithmetic import*
from sqdtoolz.HAL.Processors.CPU.CPU_ConstantArithmetic import*

from sqdtoolz.HAL.Processors.CPU.CPU_FFT import*
from sqdtoolz.HAL.Processors.CPU.CPU_ESD import*


class ProcessorCPU(DataProcessor):
    def __init__(self, proc_name, lab, pipeline_main = [], pipeline_end = []):
        super().__init__(proc_name, lab)
        self.tp_CPU = ThreadPool(processes=1)
        self.cur_async_handle = None

        self.pipeline = pipeline_main
        self.pipeline_end = pipeline_end
        self.cur_data_queue = queue.Queue()
        self.cur_data_processed = []

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        pipeline_main = []
        for cur_proc in config_dict['Pipeline']:
            cur_proc_type = cur_proc['Type']
            assert cur_proc_type in globals(), cur_proc_type + " is not in the current namespace. Need to perhaps include this class in this file..."
            cur_proc_type = globals()[cur_proc_type]
            new_proc = cur_proc_type.fromConfigDict(cur_proc)
            pipeline_main.append(new_proc)
        pipeline_end = []
        for cur_proc in config_dict['PipelineEnd']:
            cur_proc_type = cur_proc['Type']
            assert cur_proc_type in globals(), cur_proc_type + " is not in the current namespace. Need to perhaps include this class in this file..."
            cur_proc_type = globals()[cur_proc_type]
            new_proc = cur_proc_type.fromConfigDict(cur_proc)
            pipeline_end.append(new_proc)
        return cls(config_dict['Name'], lab, pipeline_main, pipeline_end)

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
        self.pipeline_end.clear()

    def add_stage(self, ProcNodeCPUobj):
        assert isinstance(ProcNodeCPUobj, ProcNodeCPU), "Can only add CPU Processing stages in a CPU Processor."
        self.pipeline.append(ProcNodeCPUobj)

    def add_stage_end(self, ProcNodeCPUobj):
        assert isinstance(ProcNodeCPUobj, ProcNodeCPU), "Can only add CPU Processing stages in a CPU Processor."
        self.pipeline_end.append(ProcNodeCPUobj)

    def __str__(self):
        cur_str = f"Name: {self.Name}\n"
        cur_str += f"Type: {self.__class__.__name__}\n"
        cur_str += f"Main Pipeline:\n"
        for cur_pipe in self.pipeline:
            cur_data = cur_pipe._get_current_config()
            cur_type = cur_data.pop('Type')
            cur_str += f"\t{cur_type}: {cur_data}\n"
        cur_str += f"Ending Pipeline:\n"
        for cur_pipe in self.pipeline_end:
            cur_data = cur_pipe._get_current_config()
            cur_type = cur_data.pop('Type')
            cur_str += f"\t{cur_type}: {cur_data}\n"
        return cur_str

    def _get_current_config(self):
        return {
            'Name' : self.Name,
            'Type'  : self.__class__.__name__,
            'Pipeline' : [x._get_current_config() for x in self.pipeline],
            'PipelineEnd' : [x._get_current_config() for x in self.pipeline_end]
        }

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, f"Dictionary specifies wrong processor class type ({self.__class__.__name__})."
        #Delete everything...
        self.reset_pipeline()
        for cur_proc in dict_config['Pipeline']:
            cur_proc_type = cur_proc['Type']
            assert cur_proc_type in globals(), cur_proc_type + " is not in the current namespace. Need to perhaps include this class in this file..."
            cur_proc_type = globals()[cur_proc_type]
            new_proc = cur_proc_type.fromConfigDict(cur_proc)
            self.pipeline.append(new_proc)
        for cur_proc in dict_config['PipelineEnd']:
            cur_proc_type = cur_proc['Type']
            assert cur_proc_type in globals(), cur_proc_type + " is not in the current namespace. Need to perhaps include this class in this file..."
            cur_proc_type = globals()[cur_proc_type]
            new_proc = cur_proc_type.fromConfigDict(cur_proc)
            self.pipeline_end.append(new_proc)
