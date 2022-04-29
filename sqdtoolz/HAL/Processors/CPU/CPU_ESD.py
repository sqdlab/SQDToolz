from sqdtoolz.HAL.Processors.ProcessorCPU import*
import numpy as np

class CPU_ESD(ProcNodeCPU):
    def __init__(self, ind_IQ = (0,1)):
        '''
        Takes the Energy-Spectral-Density of a given trace of time values. See: https://en.wikipedia.org/wiki/Spectral_density.

        Inputs:
            - ind_IQ - Tuple of the IQ indices. Default is 0 and 1 (i.e. assuming first and second channels are I and Q).
        '''
        self._ind_IQ = ind_IQ

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['IQindices'])

    def process_data(self, data_pkt, **kwargs):
        cur_chs = [x for x in data_pkt['data'].keys()]
        assert len(cur_chs) == 2, "The incoming data-packet does not have 2 channels for I and Q."

        cur_iq_arrays = []
        for m in range(2):
            cur_iq_arrays.append( data_pkt['data'].pop(cur_chs[self._ind_IQ[m]]) )

        cur_iq_data_complex = cur_iq_arrays[0] + 1j*cur_iq_arrays[1]
        
        #Calculate FFT over the last inner-most axis/index:
        num_samples = cur_iq_data_complex.shape[-1]
        #Assuming that the sample rates are the same across both channels!
        sample_rate = data_pkt['misc']['SampleRates'][0]

        freqs = np.fft.fftfreq(num_samples, 1.0/sample_rate)
        arr_fft = np.fft.fft(cur_iq_data_complex)

        data_pkt['data']['esd'] = np.abs(arr_fft)**2

        #Remove the parameter as it no longer exists after the averaging...
        data_pkt['parameters'][-1] = 'fft_freqency'
        if 'parameter_values' in data_pkt:
            data_pkt['parameter_values']['fft_frequency'] = freqs
        else:
            data_pkt['parameter_values'] = {'fft_frequency' : freqs}

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'IQindices' : self._ind_IQ
        }
