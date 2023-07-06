from sqdtoolz.HAL.Processors.ProcessorFPGA import*
import numpy as np
import scipy.signal

class FPGA_DDCFIR(ProcNodeFPGA):
    def __init__(self, fir_specs = [[{'fLO' : 25e6, 'fc' : 10e6, 'Taps' : 40, 'Win' : 'hamming'}]]):
        '''
        A general FIR filter applied across different channels in the input dataset.

        The input fir_specs is a per-channel list of lists specifying the parameters in a DICTIONARY with the keys:
            - fLO  - The demodulation/downconversion frequency
            - fc   - Cutoff frequency of the filter
            - Taps - Number of taps to use in the FIR filter
            - Win  - (defaults to 'hamming') filter window (e.g. 'hamming') as fed into the function scipy.signal.firwin

        It is a list of lists - i.e. on a per-channel basis:
            [[{}, {}, {}], [{}, {}]]
            would work for 2 channels where channel 1 is demodulated into 3 IQ pairs, while channel 2 is demodulated into
            2 IQ pairs.
        '''
        assert isinstance(fir_specs, list), "Must supply \'fir_specs\' as a list of lists (i.e. for every channel and demodulation pair)."
        for cur_elem in fir_specs:
            assert isinstance(fir_specs, list), "Must supply \'fir_specs\' as a list of lists (i.e. for every channel and demodulation pair)."
            for cur_dict in cur_elem:
                assert isinstance(cur_dict, dict), "Must supply \'fir_specs\' as a list of dictionary lists (i.e. for every channel and demodulation pair)."
        self._fir_specs = fir_specs

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['FIRspecs'])

    def get_params(self, **kwargs):
        assert 'sample_rate' in kwargs, "FPGA_DDCFIR requires a \'sample_rate\' parameter."
        sample_rates = kwargs['sample_rate']
        assert 'num_samples' in kwargs, "FPGA_DDCFIR requires a \'num_samples\' parameter."
        num_samples = kwargs['num_samples']
        
        #Given as a list of (kI,kQ) pairs
        ret_channels = []
        for c, cur_ch in enumerate(self._fir_specs):
            ret_kernels = []
            for m, cur_spec in enumerate(cur_ch):
                nyq_rate = sample_rates[m]*0.5
                freq_cutoff_norm = cur_spec['fc']/nyq_rate
                cur_filts = scipy.signal.firwin(cur_spec['Taps'], freq_cutoff_norm, window=cur_spec.get('window', 'hamming'))
                fLOonFs = cur_spec['fLO']/sample_rates[m]
                ret_kernels += [(
                    np.array([np.cos(2*np.pi*fLOonFs*n) * np.sum(cur_filts[:num_samples-n]) for n in range(num_samples)]),
                    np.array([-np.sin(2*np.pi*fLOonFs*n) * np.sum(cur_filts[:num_samples-n]) for n in range(num_samples)])
                )]
            ret_channels += [ret_kernels]

        post_fac = 2
        return ret_channels, post_fac

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'FIRspecs' : self._fir_specs
        }

