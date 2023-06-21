from sqdtoolz.HAL.Processors.ProcessorGPU import*
import cupy as cp
import numpy as np

class GPU_Decimation(ProcNodeGPU):
    def __init__(self, param_name, deci_fac):
        '''
        A basic decimation function.

        Inputs:
            - param_name - Name of the parameter in which to decimate.
            - deci_fac - Decimation factor - i.e. number of samples to skip across
        '''
        self._param_name = param_name
        self._deci_fac = int(deci_fac)

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Parameter'], config_dict['DecimationFactor'])

    def process_data(self, data_pkt, **kwargs):
        assert self._param_name in data_pkt['parameters'], f"The indexing parameter '{self._param_name}' is not in the current dataset."
        
        end_stage = kwargs.get('EndStage', False)

        axis_num = data_pkt['parameters'].index(self._param_name)
        assert (not end_stage) or axis_num > 0, "Cannot and should not take the mean across the first variable unless it is in the end-stages."

        #Process means on a per-channel basis
        slices = [np.s_[::] for x in range(len(data_pkt['parameters']))]
        slices[axis_num] = np.s_[::self._deci_fac]
        slices = tuple(slices)
        
        for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
            data_pkt['data'][cur_ch] = data_pkt['data'][cur_ch][slices]

        #Remove the parameter as it no longer exists after the averaging...
        data_pkt['parameters'].pop(axis_num)

        if 'misc' in data_pkt:
            if 'SampleRates' in data_pkt['misc']:
                for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
                    data_pkt['misc']['SampleRates'][ch_ind] = data_pkt['misc']['SampleRates'][ch_ind] / float(self._deci_fac)

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Parameter' : self._param_name,
            'DecimationFactor' : self._deci_fac
        }
