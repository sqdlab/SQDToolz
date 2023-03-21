from sqdtoolz.HAL.Processors.ProcessorCPU import ProcNodeCPU
try:
    from pomegranate.kmeans import Kmeans
except ModuleNotFoundError:
    pass
import numpy as np

class CPU_kMeans(ProcNodeCPU):
    def __init__(self, k, index_parameter_name):
        '''
        Perfoms kmeans using the kmeans functions in the pomegranate class

        Inputs:
            - index_parameter_name - which is the iteration index
            - k   - number of classes
        '''
        self.k = k
        self._param_name = index_parameter_name

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['k'], config_dict['Parameter'])

    def process_data(self, data_pkt, **kwargs):
        # assert len(data_pkt['parameters']) == 1, "kmeans must be run on the innermost parameter."
        assert data_pkt['parameters'].index(self._param_name) == len(data_pkt['parameters'])-1, "kmeans must be run on the innermost parameter."
        assert self._param_name in data_pkt['parameters'], f"The indexing parameter '{self._param_name}' is not in the current dataset."

        data = np.vstack([data_pkt['data'][ch] for ch in data_pkt['data']]).T

        model = Kmeans.from_samples(self.k, data)

        # for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
        #     data_pkt['data'][cur_ch] = model.centroids[:,ch_ind]
        
        data_pkt['data']['State'] = model.predict(data)
        #Process means on a per-channel basis

        #Remove the parameter as it no longer exists after the averaging...
        # data_pkt['parameters'] = ['cluster']

        return data_pkt
    
    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'k': self.k,
            'Parameter' : self._param_name
        }
