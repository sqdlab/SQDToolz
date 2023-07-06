from sqdtoolz.HAL.Processors.ProcessorFPGA import*
import numpy as np
import scipy.signal

class FPGA_Integrate(ProcNodeFPGA):
    def __init__(self, index_parameter_name):
        '''
        General function that averages each channel across some parameter - e.g. over repetition or over all the samples. 

        Inputs:
            - index_parameter_name - Name of the parameter in which to average across.
        '''
        self._param_name = index_parameter_name

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Parameter'])

    def get_params(self, **kwargs):
        return self._param_name

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Parameter' : self._param_name
        }

