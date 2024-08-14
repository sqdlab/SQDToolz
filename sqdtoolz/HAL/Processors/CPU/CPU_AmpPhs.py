from sqdtoolz.HAL.Processors.ProcessorCPU import ProcNodeCPU
import numpy as np

class CPU_AmpPhs(ProcNodeCPU):
    def __init__(self, channels, discard_inputs=True):
        '''
        Function to calculate the amplitude and phase of IQ values in a data-stream.

        Inputs:
            - channels    - Indices denoting IQ-pairs. List/tuple size must be divisible by 2
            - discard_inputs - If True, the inputs channels will be deleted after inserting the new channels for amplitude and phase for each IQ-pair.
        '''
        assert len(channels) % 2 == 0, 'Can only process N IQ-pairs - i.e. must give an even number of indices.'
        self.channels = channels
        self.discard_inputs = discard_inputs

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Channels'], config_dict['DiscardInputs'])

    def process_data(self, data_pkt, **kwargs):
        init_keys = [x for x in data_pkt['data'].keys()]
        ch_keys = [init_keys[x] for x in self.channels]
        if self.discard_inputs:
            dataIQs = [data_pkt['data'].pop(x) for x in ch_keys]
        else:
            dataIQs = [data_pkt['data'][x] for x in ch_keys]
        sample_rates = data_pkt['misc'].pop('SampleRates', None)
        new_sample_rates = []
        for x in range(int(len(self.channels)/2)):
            data_pkt['data'][f'Amp_{ch_keys[2*x]}{ch_keys[2*x+1]}'] = np.sqrt(dataIQs[2*x]**2+dataIQs[2*x+1]**2)
            data_pkt['data'][f'Phs_{ch_keys[2*x]}{ch_keys[2*x+1]}'] = np.arctan2(dataIQs[2*x+1], dataIQs[2*x])
            new_sample_rates += [sample_rates[self.channels[2*x]]]*2
        if len(sample_rates) > 0:
            assert sample_rates[self.channels[2*x]] == sample_rates[self.channels[2*x+1]], f'Sample rates of IQ-pair {x} are not the same.'
            if self.discard_inputs:
                sample_rates = [sample_rates[x] for x in range(len(sample_rates)) if not x in self.channels]
            sample_rates += new_sample_rates
        data_pkt['misc']['SampleRates'] = sample_rates

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Channels' : self.channels,
            'DiscardInputs' : self.discard_inputs
        }