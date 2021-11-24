from sqdtoolz.HAL.Processors.ProcessorGPU import ProcNodeGPU
from copy import deepcopy

class GPU_ChannelSum(ProcNodeGPU):
    def __init__(self, channels):
        assert len(channels) == 2, 'Can only add 2 channels together'
        self.channels = channels
        self.sorted_channels = deepcopy(self.channels)
        self.sorted_channels.sort(reverse=True)

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Channels'])

    def process_data(self, data_pkt, **kwargs):
        #duplicate data on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        ch_key1 = init_keys[self.channels[0]]
        ch_key2 = init_keys[self.channels[1]]
        cur_data1 = ProcNodeGPU.check_conv_to_cupy_array(data_pkt['data'].pop(ch_key1))
        cur_data2 = ProcNodeGPU.check_conv_to_cupy_array(data_pkt['data'].pop(ch_key2))
        data_pkt['data'][f'{ch_key1}_plus_{ch_key2}'] = cur_data1 + cur_data2

        sample_rates = data_pkt['misc'].pop('SampleRates', None)
        assert sample_rates[self.channels[0]] == sample_rates[self.channels[1]], 'Sample rates of channels being added are not the same'
        sample_rate = sample_rates[self.channels[0]]
        for c in self.sorted_channels:
            del sample_rates[c]
        sample_rates.append(sample_rate)
        data_pkt['misc']['SampleRates'] = sample_rates

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Channels' : self.channels
        }