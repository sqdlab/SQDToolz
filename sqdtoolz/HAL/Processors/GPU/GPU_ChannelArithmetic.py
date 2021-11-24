from sqdtoolz.HAL.Processors.ProcessorGPU import ProcNodeGPU
import operator

class GPU_ChannelArithmetic(ProcNodeGPU):
    def __init__(self, channels, operation='+', discard_inputs=True):
        '''
        General function to perform binary arithmetic between two different channels.

        Inputs:
            - channels    - Two channel indices - can be the same one!
            - operation   - '+', '-', '*', '/', '%'
            - discard_inputs - If True, the inputs channels will be deleted after inserting the new channel for the arithmetic result.
        '''
        assert len(channels) == 2, 'Can only add 2 channels together'
        self.channels = channels
        self.operation = operation
        self.discard_inputs = discard_inputs

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Channels'], config_dict['Operation'], config_dict['DiscardInputs'])

    def process_data(self, data_pkt, **kwargs):
        opsMap = {
            '+' : operator.add,
            '-' : operator.sub,
            '*' : operator.mul,
            '/' : operator.truediv,  # use operator.div for Python 2
            '%' : operator.mod,
        }

        init_keys = [x for x in data_pkt['data'].keys()]
        ch_key1 = init_keys[self.channels[0]]
        ch_key2 = init_keys[self.channels[1]]
        if self.discard_inputs:
            cur_data1 = data_pkt['data'].pop(ch_key1)
            if ch_key2 != ch_key1:
                cur_data2 = data_pkt['data'].pop(ch_key2)
            else:
                cur_data2 = cur_data1
        else:
            cur_data1 = data_pkt['data'][ch_key1]
            cur_data2 = data_pkt['data'][ch_key2]
        cur_data1 = ProcNodeGPU.check_conv_to_cupy_array(cur_data1)
        cur_data2 = ProcNodeGPU.check_conv_to_cupy_array(cur_data2)
        data_pkt['data'][f'{ch_key1}_{self.operation}_{ch_key2}'] = opsMap[self.operation](cur_data1, cur_data2)

        sample_rates = data_pkt['misc'].pop('SampleRates', None)
        assert sample_rates[self.channels[0]] == sample_rates[self.channels[1]], 'Sample rates of channels being added are not the same'
        #
        sample_rate = sample_rates[self.channels[0]]
        if self.discard_inputs:
            sample_rates_to_keep = [x for x in range(len(sample_rates)) if x != self.channels[0] and x != self.channels[1]]
            if len(sample_rates_to_keep) == 0:
                sample_rates = []
            else:
                inds = operator.itemgetter(*sample_rates_to_keep)(sample_rates)
                if type(inds) == int:
                    inds = [inds]   #It returns a singleton instead of a tuple...
                else:
                    inds = list(inds)
                sample_rates = inds
        sample_rates.append(sample_rate)
        data_pkt['misc']['SampleRates'] = sample_rates

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Channels' : self.channels,
            'Operation' : self.operation,
            'DiscardInputs' : self.discard_inputs
        }
