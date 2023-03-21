from sqdtoolz.HAL.Processors.ProcessorCPU import ProcNodeCPU
from copy import copy

class CPU_Slice(ProcNodeCPU):
    def __init__(self, param_name, slices=[(None,None,None)]):
        self.param_name = param_name
        self.slices = slices

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['ParamToSlice'], config_dict['Slices'])

    def process_data(self, data_pkt, **kwargs):
        #duplicate data on a per-channel basis
        axis = data_pkt['parameters'].index(self.param_name)
        init_keys = [x for x in data_pkt['data'].keys()]
        init_sample_rates = None
        if 'misc' in data_pkt:
            init_sample_rates = data_pkt['misc'].pop('SampleRates', None)
        final_sample_rates = []
        for ch_ind, cur_ch in enumerate(init_keys):
            cur_data_cpu = data_pkt['data'].pop(cur_ch)
            cur_slices = [slice(None,None,None) for _ in range(len(cur_data_cpu.shape)-1)]
            for s_idx, s in enumerate(self.slices):
                slices = copy(cur_slices)
                slices.insert(axis, slice(*s))
                data_pkt['data'][f'{cur_ch}_slice{s_idx}'] = cur_data_cpu[tuple(slices)]
                if init_sample_rates is not None:
                    final_sample_rates.append(init_sample_rates[ch_ind])
            del cur_data_cpu    #Perhaps necessary - well it's no time for caution...
        if 'misc' in data_pkt:
            data_pkt['misc']['SampleRates'] = final_sample_rates

        #TODO: Make sure to check that the sliced arrays are all the same size above!!!

        #TODO: Clean this up... Not sure how to make this axis consistent anyway...
        data_pkt['parameter_values'][self.param_name] = data_pkt['parameter_values'][self.param_name][slice(*self.slices[0])]

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Slices' : self.slices,
            'ParamToSlice' : self.param_name
        }
