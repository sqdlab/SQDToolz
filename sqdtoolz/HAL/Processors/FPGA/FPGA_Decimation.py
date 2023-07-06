from sqdtoolz.HAL.Processors.ProcessorFPGA import*
import numpy as np
import scipy.signal

class FPGA_Decimation(ProcNodeFPGA):
    def __init__(self, param_name, deci_fac):
        '''
        A basic decimation function.

        Inputs:
            - param_name - Name of the parameter in which to decimate.
            - deci_fac - Decimation factor - i.e. number of samples to skip across
        '''
        self._param_name = param_name
        self._deci_fac = int(deci_fac)

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Parameter'], config_dict['DecimationFactor'])

    def get_params(self, **kwargs):
        return self._param_name, self._deci_fac

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Parameter' : self._param_name,
            'DecimationFactor' : self._deci_fac
        }
