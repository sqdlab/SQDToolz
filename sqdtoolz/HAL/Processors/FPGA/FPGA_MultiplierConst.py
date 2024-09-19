from sqdtoolz.HAL.Processors.ProcessorFPGA import*
import numpy as np
import scipy.signal

class FPGA_MultiplierConst(ProcNodeFPGA):
    def __init__(self, mult_specs = [[1]]):
        '''
        A general DDC filter applied across different channels in the input dataset.

        It is a list of lists - i.e. on a per-channel basis (xx is a floating-point number for the constant to multiply onto the multiplier channel):
            [[xx, xx, xx], [xx, xx]]
            would work for 2 channels where channel 1 is multiplied over 3 constants (if broken into I and Q, they are the same value), while channel 2
            is multiplied over 2 constants (once again, if broken into I and Q, they are the same value).
        '''
        assert isinstance(mult_specs, list), "Must supply \'mult_specs\' as a list of lists (i.e. for every physical channel and multiplier channel)."
        for cur_elem in mult_specs:
            assert isinstance(cur_elem, list), "Must supply \'mult_specs\' as a list of lists (i.e. for every physical channel and multiplier channel)."
        self._mult_specs = mult_specs

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['MultConsts'])

    def get_params(self, **kwargs):        
        assert 'num_samples' in kwargs, "FPGA_MultiplierConst requires a \'num_samples\' parameter."
        num_samples = kwargs['num_samples']
        
        #Given as a list of (kI,kQ) pairs
        ret_channels = []
        for c, cur_ch in enumerate(self._mult_specs):
            ret_kernels = []
            for m, cur_const in enumerate(cur_ch):
                ret_kernels += [(
                    np.zeros(num_samples)+cur_const,
                    np.zeros(num_samples)+cur_const
                )]
            ret_channels += [ret_kernels]

        post_fac = 2
        return ret_channels, post_fac

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'MultConsts' : self._mult_specs
        }

