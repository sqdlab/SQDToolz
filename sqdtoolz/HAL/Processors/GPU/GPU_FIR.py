from sqdtoolz.HAL.Processors.ProcGPU import*
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
        #A data store of current cosine|sine CuPy arrays used for DDC with each entry formatted as: (num-samples, sample-rate, ddc-frequency, cosine-array, sine-array)
        self._fir_arrays = []

    def input_format(self):
        return ['repetition', 'segment', 'sample']

    def output_format(self):
        return ['repetition', 'segment', 'sample']

    def process_data(self, data_pkt):
        assert 'misc' in data_pkt, "The data packet does not have miscellaneous data under the key 'misc'"
        assert 'SampleRates' in data_pkt['misc'], "The data packet does not have SampleRate under the entry 'misc'"

        assert len(self._fir_specs) >= len(data_pkt['data'].keys()), f"The dataset has more channels ({len(data_pkt['data'].keys())}) than specified number of FIR filters ({len(self._fir_specs)})."

        #Process DDC on a per-channel basis
        for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
            sample_rate = data_pkt['misc']['SampleRates'][ch_ind]
            nyq_rate = sample_rate*0.5
            freq_cutoff_norm = self._fir_specs[ch_ind]['fc']/nyq_rate
            if self._fir_specs[ch_ind]['Type'] == 'low':
                myFilt_vals = cp.array(scipy.signal.firwin(self._fir_specs[ch_ind]['Taps'], freq_cutoff_norm, window=self._fir_specs[ch_ind]['Win']))
            else:
                myFilt_vals = 1.0 - cp.array(scipy.signal.firwin(self._fir_specs[ch_ind]['Taps'], freq_cutoff_norm, window=self._fir_specs[ch_ind]['Win']))
            data_pkt['data'][cur_ch] = cupyx.scipy.ndimage.convolve1d( ProcNodeGPU.check_conv_to_cupy_array(data_pkt['data'][cur_ch]) , myFilt_vals)

        return data_pkt
