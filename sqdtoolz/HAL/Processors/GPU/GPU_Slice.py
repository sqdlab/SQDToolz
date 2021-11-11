from sqdtoolz.HAL.Processors.ProcessorGPU import ProcNodeGPU
from copy import copy

class GPU_Slice(ProcNodeGPU):
    def __init__(self, slices=[(None,None,None)], axis=2):
        self.slices = slices
        self.axis = axis

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Slices'], config_dict['Axis'])

    def process_data(self, data_pkt, **kwargs):
        #duplicate data on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        init_sample_rates = data_pkt['misc'].pop('SampleRates', None)
        final_sample_rates = []
        for ch_ind, cur_ch in enumerate(init_keys):
            cur_data_gpu = ProcNodeGPU.check_conv_to_cupy_array(data_pkt['data'].pop(cur_ch))
            cur_slices = [slice(None,None,None) for _ in range(len(cur_data_gpu.shape)-1)]
            for s_idx, s in enumerate(self.slices):
                slices = copy(cur_slices)
                slices.insert(self.axis, slice(*s))
                data_pkt['data'][f'{cur_ch}_slice{s_idx}'] = cur_data_gpu[tuple(slices)]
                if init_sample_rates is not None:
                    final_sample_rates.append(init_sample_rates[ch_ind])
            del cur_data_gpu    #Perhaps necessary - well it's no time for caution...
        data_pkt['misc']['SampleRates'] = final_sample_rates

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Slices' : self.slices,
            'Axis' : self.axis
        }