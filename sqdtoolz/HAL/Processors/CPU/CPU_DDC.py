from sqdtoolz.HAL.Processors.ProcessorCPU import*
import numpy as np

class CPU_DDC(ProcNodeCPU):
    def __init__(self, ddc_freqs):
        #DDC variables
        self._ddc_freqs = ddc_freqs
        #A data store of current cosine|sine CuPy arrays used for DDC with each entry formatted as: (num-samples, sample-rate, ddc-frequency, cosine-array, sine-array)
        self._ddc_cossin_arrays = []

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Frequencies'])

    def process_data(self, data_pkt, **kwargs):
        assert 'misc' in data_pkt, "The data packet does not have miscellaneous data under the key 'misc'"
        assert 'SampleRates' in data_pkt['misc'], "The data packet does not have SampleRate under the entry 'misc'"

        assert len(self._ddc_freqs) >= len(data_pkt['data'].keys()), f"The dataset has more channels ({len(data_pkt['data'].keys())}) than specified number of DDC frequencies ({len(self._ddc_freqs)})."

        #Process DDC on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        if len(self._ddc_cossin_arrays) == 0:
            self._ddc_cossin_arrays = [(0, 0, 0, None, None) for x in init_keys]
        init_sample_rates = data_pkt['misc'].pop('SampleRates', None)
        final_sample_rates = []
        for ch_ind, cur_ch in enumerate(init_keys):
            num_samples = data_pkt['data'][cur_ch].shape[-1]    #Can be (reps, segments, samples) or (segments, samples), so choose the last index...
            ddc_frequency = self._ddc_freqs[ch_ind]
            sample_rate = init_sample_rates[ch_ind]

            if ddc_frequency != None and ddc_frequency != 0:
                if self._ddc_cossin_arrays[ch_ind][0] != num_samples or self._ddc_cossin_arrays[ch_ind][1] != sample_rate or self._ddc_cossin_arrays[ch_ind][2] != ddc_frequency:
                    omega = 2*np.pi*ddc_frequency/sample_rate
                    self._ddc_cossin_arrays[ch_ind] = (
                        num_samples, sample_rate, ddc_frequency, 2.0*np.cos(omega*np.arange(num_samples)), 2.0*np.sin(omega*np.arange(num_samples)) )
                #Perform the actual DDC...
                cur_data_cpu = data_pkt['data'].pop(cur_ch)
                data_pkt['data'][f'{cur_ch}_I'] = np.multiply(cur_data_cpu, self._ddc_cossin_arrays[ch_ind][3])
                data_pkt['data'][f'{cur_ch}_Q'] = np.multiply(cur_data_cpu, self._ddc_cossin_arrays[ch_ind][4])
                final_sample_rates += [sample_rate]*2
                del cur_data_cpu    #Perhaps necessary - well it's no time for caution...
            else:
                final_sample_rates.append(sample_rate)
        data_pkt['misc']['SampleRates'] = final_sample_rates
        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Frequencies' : self._ddc_freqs[:]
        }
