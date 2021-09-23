from sqdtoolz.HAL.Processors.ProcessorCPU import ProcNodeCPU
from copy import copy

class CPU_Slice(ProcNodeCPU):
    def __init__(self, slices=[(None,None,None)], axis=2):
        self.slices = slices
        self.axis = axis

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Slices'], config_dict['Axis'])

    def process_data(self, data_pkt, **kwargs):
        #duplicate data on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        for ch_ind, cur_ch in enumerate(init_keys):
            cur_data_cpu = data_pkt['data'].pop(cur_ch)
            cur_slices = [slice(None,None,None) for _ in range(len(cur_data_cpu.shape)-1)]
            for s_idx, s in enumerate(self.slices):
                slices = copy(cur_slices)
                slices.insert(self.axis, slice(*s))
                data_pkt['data'][f'{cur_ch}_slice{s_idx}'] = cur_data_cpu[tuple(slices)]
            del cur_data_cpu    #Perhaps necessary - well it's no time for caution...

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Slices' : self.slices,
            'Axis' : self.axis
        }