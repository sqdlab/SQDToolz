from sqdtoolz.HAL.Processors.ProcessorCPU import*
import numpy as np

class CPU_MeanBlock(ProcNodeCPU):
    def __init__(self, index_parameter_name, block_fac):
        '''
        General function that averages each channel across some parameter (e.g. over repetition or over all the samples) over blocks. 

        Inputs:
            - index_parameter_name - Name of the parameter in which to average across.
            - block_fac            - Size of the block-window
        '''
        self._param_name = index_parameter_name
        self._block_fac = int(block_fac)

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Parameter'], config_dict['BlockFac'])

    def process_data(self, data_pkt):
        assert self._param_name in data_pkt['parameters'], f"The indexing parameter '{self._param_name}' is not in the current dataset."

        axis_num = data_pkt['parameters'].index(self._param_name)

        #Process means on a per-channel basis
        for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
            temp = list(data_pkt['data'][cur_ch].shape)

            if self._block_fac > temp[axis_num]:
                temp[axis_num:axis_num+1] = [1, temp[0]]
            else:
                temp[axis_num:axis_num+1] = [int(temp[axis_num]/self._block_fac), self._block_fac]

            slice_inds = [np.s_[:] for x in data_pkt['data'][cur_ch].shape]
            slice_inds[axis_num] = np.s_[:temp[axis_num]*self._block_fac]

            data_pkt['data'][cur_ch] = np.mean(data_pkt['data'][cur_ch][tuple(slice_inds)].reshape(tuple(temp)), axis_num+1)

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Parameter' : self._param_name,
            'BlockFac' : self._block_fac
        }
