from  sqdtoolz.HAL.DataProcessor import DataProcessor
import queue

class ProcNodeFPGA:
    def __init__(self):
        pass

    def get_params(self, **kwargs):
        raise NotImplementedError()

    def _get_current_config(self):
        raise NotImplementedError()

from sqdtoolz.HAL.Processors.FPGA.FPGA_DDC import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDCFIR import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_Integrate import*
from sqdtoolz.HAL.Processors.FPGA.FPGA_Decimation import*

class ProcessorFPGA(DataProcessor):
    def __init__(self, proc_name, lab, pipeline_main = []):
        super().__init__(proc_name, lab)
        self.cur_async_handle = None

        self.pipeline = pipeline_main
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
        return cls(config_dict['Name'], lab, pipeline_main)

    def push_data(self, data_pkt):
        assert False, "Cannot manually push data into this processor type; it's done so automatically when acquiring data on the FPGA."

    def get_all_data(self):
        assert False, "Cannot manually obtain data into this processor type; it's done so automatically when acquiring data on the FPGA."

    def ready(self):
        return True

    def reset_pipeline(self):
        self.pipeline.clear()

    def add_stage(self, ProcNodeFPGAobj):
        assert isinstance(ProcNodeFPGAobj, ProcNodeFPGA), "Can only add FPGA Processing stages in a FPGA Processor."
        self.pipeline.append(ProcNodeFPGAobj)

    def __str__(self):
        cur_str = f"Name: {self.Name}\n"
        cur_str += f"Type: {self.__class__.__name__}\n"
        cur_str += f"Main Pipeline:\n"
        for cur_pipe in self.pipeline:
            cur_data = cur_pipe._get_current_config()
            cur_type = cur_data.pop('Type')
            cur_str += f"\t{cur_type}: {cur_data}\n"
        return cur_str

    def _get_current_config(self):
        return {
            'Name' : self.Name,
            'Type'  : self.__class__.__name__,
            'Pipeline' : [x._get_current_config() for x in self.pipeline]
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
