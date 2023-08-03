from sqdtoolz.HAL.Processors.ProcessorFPGA import*

class FPGA_FFT(ProcNodeFPGA):
    def __init__(self, ind_IQ = (0,1)):
        '''
        Takes the FFT of a given trace of time values.

        Inputs:
            - ind_IQ - Tuple of the IQ indices. Default is 0 and 1 (i.e. assuming first and second channels are I and Q).
        '''
        self._ind_IQ = ind_IQ

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['IQindices'])

    def get_params(self, **kwargs):
        return self._ind_IQ

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'IQindices' : self._ind_IQ
        }
