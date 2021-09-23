from sqdtoolz.HAL.Processors.ProcessorCPU import ProcNodeCPU

class CPU_Duplicate(ProcNodeCPU):
    def __init__(self, reps):
        self.reps = reps

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Repetitions'])

    def process_data(self, data_pkt, **kwargs):
        #duplicate data on a per-channel basis
        init_keys = [x for x in data_pkt['data'].keys()]
        for ch_ind, cur_ch in enumerate(init_keys):
            sample_rate = data_pkt['misc']['SampleRates'][2*ch_ind]
            cur_data_cpu = data_pkt['data'].pop(cur_ch)
            for rep_idx in range(self.reps[ch_ind]):
                data_pkt['data'][f'{cur_ch}_{rep_idx}'] = cur_data_cpu
            data_pkt['misc']['SampleRates'].insert(2*ch_ind+1, sample_rate)
            del cur_data_cpu    #Perhaps necessary - well it's no time for caution...

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Repetitions' : self.reps
        }