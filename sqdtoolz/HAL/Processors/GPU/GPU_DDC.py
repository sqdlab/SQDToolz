from sqdtoolz.HAL.Processors.ProcGPU import*
import cupy as cp
import numpy as np

class GPU_DDC(ProcNodeGPU):
    def __init__(self, ddc_freqs = []):
        #DDC variables
        self._ddc_freqs = ddc_freqs
        #A data store of current cosine|sine CuPy arrays used for DDC with each entry formatted as: (num-samples, sample-rate, ddc-frequency, cosine-array, sine-array)
        self._ddc_cur_cossin_arrays = []

    def input_format(self):
        return ['repetition', 'segment', 'sample']

    def output_format(self):
        return ['repetition', 'segment', 'sample']

    def process_data(self, data_pkt):
        assert 'misc' in data_pkt, "The data packet does not have miscellaneous data under the key 'misc'"
        assert 'SampleRates' in data_pkt['misc'], "The data packet does not have SampleRate under the entry 'misc'"

        assert len(self._ddc_freqs) >= len(data_pkt['data'].keys()), f"The dataset has more channels ({len(data_pkt['data'].keys())}) than specified number of DDC frequencies ({len(self._ddc_freqs)})."

        #Process DDC on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        for ch_ind, cur_ch in enumerate(init_keys):
            num_samples = data_pkt['data'][cur_ch].shape[-1]    #Can be (reps, segments, samples) or (segments, samples), so choose the last index...
            sample_rate = data_pkt['misc']['SampleRates'][2*ch_ind] #The list will be appended for every I and Q - thus, it'll be every 2nd value as it grows...
            ddc_frequency = self._ddc_freqs[ch_ind]

            #A little optimisation to ensure that identical arrays are not unnecessarily replicated...
            ddc_arr_ind = -1
            #Note that entries in the array is formatted as: (num-samples, sample-rate, ddc-frequency, cosine-array, sine-array)
            for arr_num, cur_arrs in enumerate(self._ddc_cur_cossin_arrays):
                if cur_arrs[0] == num_samples and cur_arrs[1] == sample_rate and cur_arrs[2] == ddc_frequency:
                    ddc_arr_ind = arr_num
            #Build/Rebuild array if necessary            
            if ddc_arr_ind == -1:
                omega = 2*cp.pi*ddc_frequency/sample_rate
                #TODO: Investigate the following thought later. One could tie up both the sines and cosines via a vstack and call
                #a single multiply command at the expense of a slight reshape or duplication. The trade-off is calling the data
                #array once versus the better cache performance on calling sine/cosine separately - the second approach is taken
                #for convenience here...
                #TODO: Also investigate the idea of calculating sine/cosine on CPU and passing onto GPU instead of using the GPU...
                self._ddc_cur_cossin_arrays += [(
                    num_samples, sample_rate, ddc_frequency, cp.cos(omega*cp.arange(num_samples)), cp.sin(omega*cp.arange(num_samples))
                )]
                ddc_arr_ind = len(self._ddc_cur_cossin_arrays) - 1
            #Perform the actual DDC...
            cur_data_gpu = ProcNodeGPU.check_conv_to_cupy_array(data_pkt['data'].pop(cur_ch))
            data_pkt['data'][f'{cur_ch}_I'] = cp.multiply(cur_data_gpu, self._ddc_cur_cossin_arrays[ddc_arr_ind][3])
            data_pkt['data'][f'{cur_ch}_Q'] = cp.multiply(cur_data_gpu, self._ddc_cur_cossin_arrays[ddc_arr_ind][4])
            data_pkt['misc']['SampleRates'].insert(2*ch_ind+1, sample_rate)
            del cur_data_gpu    #Perhaps necessary - well it's no time for caution...

        return data_pkt
