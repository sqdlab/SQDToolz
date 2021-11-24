from sqdtoolz.HAL.Processors.ProcessorGPU import ProcNodeGPU
import cupy as cp
import numpy as np
import cupyx.scipy.ndimage
import scipy.signal

class GPU_FIR(ProcNodeGPU):
    def __init__(self, fir_specs = [{'Type' : 'low', 'Taps' : 40, 'fc' : 10e6, 'Win' : 'hamming'}]):
        '''
        A general FIR filter applied across different channels in the input dataset.

        The input fir_specs is a per-channel list specifying the parameters in a DICTIONARY with the keys:
            - Type - Specifying whether it is a low or high pass filter via the strings: 'low' or 'high'
            - Taps - Number of taps to use in the FIR filter
            - fc   - Cutoff frequency of the filter
            - Win  - The filter window (e.g. 'hamming') as fed into the function scipy.signal.firwin
        '''
        self._fir_specs = fir_specs
        #A data store of current fir_filter_specs
        self._fir_arrays = []

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['FIRspecs'])

    def process_data(self, data_pkt, **kwargs):
        assert 'misc' in data_pkt, "The data packet does not have miscellaneous data under the key 'misc'"
        assert 'SampleRates' in data_pkt['misc'], "The data packet does not have SampleRate under the entry 'misc'"

        assert len(self._fir_specs) >= len(data_pkt['data'].keys()), f"The dataset has more channels ({len(data_pkt['data'].keys())}) than specified number of FIR filters ({len(self._fir_specs)})."

        #Process FIR on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        if len(self._fir_arrays) == 0:
            self._fir_arrays = [(None, None, None, None, None, None) for x in init_keys]
        for ch_ind, cur_ch in enumerate(init_keys):
            cur_data_gpu = ProcNodeGPU.check_conv_to_cupy_array(data_pkt['data'][cur_ch])
            sample_rate = data_pkt['misc']['SampleRates'][ch_ind]
            filter_type = self._fir_specs[ch_ind]['Type']
            taps = self._fir_specs[ch_ind]['Taps']
            if taps is None:
                taps = cur_data_gpu.shape[-1]
            window = self._fir_specs[ch_ind]['Win']
            cutoff = self._fir_specs[ch_ind]['fc']
            if cutoff is None:
                cutoff = 1/cur_data_gpu.shape[-1]
            if self._fir_arrays[ch_ind][0] != sample_rate or self._fir_arrays[ch_ind][1] != filter_type or \
               self._fir_arrays[ch_ind][2] != taps or self._fir_arrays[ch_ind][3] != window or self._fir_arrays[ch_ind][4] != cutoff:
                nyq_rate = sample_rate*0.5
                freq_cutoff_norm = cutoff/nyq_rate
                if filter_type == 'low':
                    fir_coeffs = cp.array(scipy.signal.firwin(taps, freq_cutoff_norm, window=window))
                else:
                    fir_coeffs = 1.0 - cp.array(scipy.signal.firwin(taps, freq_cutoff_norm, window=window))
                self._fir_arrays[ch_ind] = (sample_rate,filter_type,taps,window,cutoff, fir_coeffs)
            data_pkt['data'][cur_ch] = self.apply_fir(cur_data_gpu, self._fir_arrays[ch_ind][5])
            del cur_data_gpu #Perhaps necessary - well it's no time for caution...

        return data_pkt

    def apply_fir(self, data, fir_coeffs):
        return cupyx.scipy.ndimage.convolve1d(data, fir_coeffs)

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'FIRspecs' : self._fir_specs
        }

class GPU_MultiplySum(GPU_FIR):
    def __init__(self, fir_specs=[{ 'Type': 'low','fc': None,'Win': 'hamming' }]):
        '''
        A general FIR filter with number of taps equal to number of samples (assumed to be the last axis)
        is applied across different channels in the input dataset and summed across samples.
        This returns one sample.

        The input fir_specs is a per-channel list specifying the parameters in a DICTIONARY with the keys:
            - Type - Specifying whether it is a low or high pass filter via the strings: 'low' or 'high'
            - fc   - Cutoff frequency of the filter. If None, lowest cutoff possible is used.
            - Win  - The filter window (e.g. 'hamming') as fed into the function scipy.signal.firwin
        '''
        for i in range(len(fir_specs)):
            fir_specs[i]['Taps'] = None
        super().__init__(fir_specs=fir_specs)

    def apply_fir(self, data, fir_coeffs):
        return cp.sum(data*fir_coeffs, axis=-1)