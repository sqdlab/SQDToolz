from sqdtoolz.HAL.Processors.ProcessorCPU import*
import numpy as np
import scipy.ndimage
import scipy.signal

class CPU_FIR(ProcNodeCPU):
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

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['FIRspecs'])

    def process_data(self, data_pkt, **kwargs):
        assert 'misc' in data_pkt, "The data packet does not have miscellaneous data under the key 'misc'"
        assert 'SampleRates' in data_pkt['misc'], "The data packet does not have SampleRate under the entry 'misc'"

        assert len(self._fir_specs) >= len(data_pkt['data'].keys()), f"The dataset has more channels ({len(data_pkt['data'].keys())}) than specified number of FIR filters ({len(self._fir_specs)})."

        #Process FIR on a per-channel basis
        for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
            sample_rate = data_pkt['misc']['SampleRates'][ch_ind]
            nyq_rate = sample_rate*0.5
            freq_cutoff_norm = self._fir_specs[ch_ind]['fc']/nyq_rate
            if self._fir_specs[ch_ind]['Type'] == 'low':
                myFilt_vals = np.array(scipy.signal.firwin(self._fir_specs[ch_ind]['Taps'], freq_cutoff_norm, window=self._fir_specs[ch_ind]['Win']))
            else:
                myFilt_vals = 1.0 - np.array(scipy.signal.firwin(self._fir_specs[ch_ind]['Taps'], freq_cutoff_norm, window=self._fir_specs[ch_ind]['Win']))
            
            # param_slicer = [np.s_[0:]]*len(data_pkt['data'][cur_ch].shape)
            # param_slicer[-1] = np.s_[int(self._fir_specs[ch_ind]['Taps']):]
            # param_slicer = tuple(x for x in param_slicer)
            data_pkt['data'][cur_ch] = scipy.ndimage.convolve1d( data_pkt['data'][cur_ch] , myFilt_vals) #[param_slicer]

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'FIRspecs' : self._fir_specs
        }
