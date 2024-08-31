from sqdtoolz.HAL.Processors.ProcessorCPU import*
import numpy as np

class CPU_MeanVariance(ProcNodeCPU):
    def __init__(self, index_parameter_name):
        '''
        General function that calculates the mean and variance of each channel across some parameter - e.g. over repetition or over all the samples. 

        Inputs:
            - index_parameter_name - Name of the parameter in which to average across.
        '''
        self._param_name = index_parameter_name

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Parameter'])

    def process_data(self, data_pkt, **kwargs):
        assert self._param_name in data_pkt['parameters'], f"The indexing parameter '{self._param_name}' is not in the current dataset."

        end_stage = kwargs.get('EndStage', False)

        axis_num = data_pkt['parameters'].index(self._param_name)
        assert (not end_stage) or axis_num > 0, "Cannot and should not take the variance across the first variable unless it is in the end-stages."

        #Process means on a per-channel basis
        orig_keys = list(data_pkt['data'].keys())
        for cur_ch in orig_keys:
            data_pkt['data'][f'{cur_ch}_{self._param_name}_Mean'] = np.mean(data_pkt['data'][cur_ch], axis=axis_num)
            data_pkt['data'][f'{cur_ch}_{self._param_name}_Var'] = np.var(data_pkt['data'][cur_ch], axis=axis_num)
        for cur_ch in orig_keys:
            data_pkt['data'].pop(cur_ch)

        #Remove the parameter as it no longer exists after the averaging...
        data_pkt['parameters'].pop(axis_num)

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Parameter' : self._param_name
        }
