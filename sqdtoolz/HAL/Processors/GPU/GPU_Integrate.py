from sqdtoolz.HAL.Processors.ProcessorGPU import*
import cupy as cp

class GPU_Integrate(ProcNodeGPU):
    def __init__(self, index_parameter_name):
        '''
        General function that averages each channel across some parameter - e.g. over repetition or over all the samples. 

        Inputs:
            - index_parameter_name - Name of the parameter in which to average across.
        '''
        self._param_name = index_parameter_name

    def input_format(self):
        return ['repetition', 'segment', 'sample']

    def output_format(self):
        return ['repetition', 'segment', 'sample']

    def process_data(self, data_pkt):
        assert self._param_name in data_pkt['parameters'], f"The indexing parameter '{self._param_name}' is not in the current dataset."

        axis_num = data_pkt['parameters'].index(self._param_name)

        #Process means on a per-channel basis
        for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
            data_pkt['data'][cur_ch] = cp.sum(data_pkt['data'][cur_ch], axis=axis_num)

        #Remove the parameter as it no longer exists after the averaging...
        data_pkt['parameters'].pop(axis_num)

        return data_pkt
