from sqdtoolz.HAL.Processors.ProcessorFPGA import*
import numpy as np
import scipy.signal

class FPGA_DDC(ProcNodeFPGA):
    def __init__(self, ddc_specs = [[25e6]]):
        '''
        A general DDC filter applied across different channels in the input dataset.

        It is a list of lists - i.e. on a per-channel basis (xx is a floating-point number for the downconversion frequency):
            [[xx, xx, xx], [xx, xx]]
            would work for 2 channels where channel 1 is demodulated into 3 IQ pairs, while channel 2 is demodulated into
            2 IQ pairs.
        '''
        assert isinstance(ddc_specs, list), "Must supply \'fir_specs\' as a list of lists (i.e. for every channel and IQ pair)."
        for cur_elem in ddc_specs:
            assert isinstance(ddc_specs, list), "Must supply \'fir_specs\' as a list of lists (i.e. for every channel and IQ pair)."
        self._ddc_specs = ddc_specs

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['DDCfreqs'])

    def get_params(self, **kwargs):
        assert 'sample_rate' in kwargs, "FPGA_DDC requires a \'sample_rate\' parameter."
        sample_rates = kwargs['sample_rate']
        
        if kwargs.get('only_params', False):
            return self._ddc_specs

        assert 'num_samples' in kwargs, "FPGA_DDC requires a \'num_samples\' parameter."
        num_samples = kwargs['num_samples']
        
        #Given as a list of (kI,kQ) pairs
        ret_channels = []
        for c, cur_ch in enumerate(self._ddc_specs):
            ret_kernels = []
            for m, cur_freq in enumerate(cur_ch):
                phase_vals = 2*np.pi*cur_freq/sample_rates[m] * np.arange(num_samples)
                ret_kernels += [(
                    np.cos(phase_vals),
                    -np.sin(phase_vals)
                )]
            ret_channels += [ret_kernels]

        post_fac = 2
        return ret_channels, post_fac

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'DDCfreqs' : self._ddc_specs
        }

