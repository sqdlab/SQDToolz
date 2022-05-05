from sqdtoolz.HAL.Processors.ProcessorGPU import ProcNodeGPU

class GPU_Rename(ProcNodeGPU):
    def __init__(self, names):
        self.names = names

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Names'])

    def process_data(self, data_pkt, **kwargs):
        #duplicate data on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        assert len(self.names) == len(init_keys), 'The number of new channel names must be the same'
        for ch_ind, cur_ch in enumerate(init_keys):
            data_pkt['data'][self.names[ch_ind]] = data_pkt['data'].pop(cur_ch)

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Names' : self.names
        }