from sqdtoolz.HAL.ACQ import ACQ
from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.Drivers.ACQ_ETH_FPGA import ETHFPGA
from sqdtoolz.HAL.TriggerPulse import Trigger, TriggerInput
from multiprocessing.pool import ThreadPool
from functools import partial
import logging
import time

class MultiACQ(ACQ):
    def __init__(self, hal_name, lab, instr_acq_names, trigger):
        HALbase.__init__(self, hal_name)
        if lab._register_HAL(self):
            self._instr_ids = instr_acq_names
            self._trig_src_obj = None
            self.data_processor = None
            self._instr_acqs = []
            for name in instr_acq_names:
                instr = lab._get_instrument(name)
                assert type(instr) == ETHFPGA, f'{type(instr)} are not supported yet. Some more functions need to be implemented.'
                self._instr_acqs.append(instr)
            self._instr_acq = self._instr_acqs[0]
            self._tp = ThreadPool(processes=len(instr_acq_names))
        assert type(trigger) == Trigger
        self.set_trigger_source(trigger)

    def get_data(self, **kwargs):
        cur_processor = kwargs.pop('data_processor', self.data_processor)
        self.get_trigger_source().TrigEnable = False
        
        for inst in self._instr_acqs:
            inst._start(**kwargs)

        datas = []
        handles = []
        for inst in self._instr_acqs:
            handles.append(self._tp.apply_async(inst._acquire))

        self.get_trigger_source().TrigEnable = True

        for handle in handles:
            while not handle.ready():
                time.sleep(10e-3)
            datas.append(handle.get())

        for i, inst in enumerate(self._instr_acqs):
            datas[i] = inst._stop(datas[i], **kwargs)

        final_data_pkt = {}
        final_data_pkt['data'] = {}
        final_data_pkt['misc'] = {'SampleRates' : []}
        for i, d in enumerate(datas):
            if 'parameters' in final_data_pkt:
                assert d['parameters'] == final_data_pkt['parameters']
            else:
                final_data_pkt['parameters'] = d['parameters']
            for key in d['data']:
                final_data_pkt['data'][f'{i}_{key}'] = d['data'][key]
            final_data_pkt['misc']['SampleRates'] += d['misc']['SampleRates']
            for key in d['misc']:
                if key != 'SampleRates':
                    final_data_pkt['misc'][f'{i}_{key}'] = d['misc'][key]
        if cur_processor is None:
            return final_data_pkt
        else:
            cur_processor.push_data(final_data_pkt)
            return cur_processor.get_all_data()
            
    @property
    def ChannelStates(self):
        ch_states = []
        for inst in self._instr_acqs:
            ch_states += inst.ChannelStates
        return ch_states
    @ChannelStates.setter
    def ChannelStates(self, ch_states):
        counter = 0
        ch_states = list(ch_states)
        for inst in self._instr_acqs:
            num_channels = inst.AvailableChannels
            inst.ChannelStates = ch_states[counter:counter+num_channels]
            counter += num_channels

    @property
    def NumSamples(self):
        return self._instr_acq.NumSamples
    @NumSamples.setter
    def NumSamples(self, num_samples):
        for inst in self._instr_acqs:
            inst.NumSamples = num_samples
        logging.warn("All Samples are set to the same value. You can set them separately.")

    @property
    def NumSegments(self):
        return self._instr_acq.NumSegments
    @NumSegments.setter
    def NumSegments(self, num_segs):
        for inst in self._instr_acqs:
            inst.NumSegments = num_segs

    @property
    def NumRepetitions(self):
        return self._instr_acq.NumRepetitions
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps):
        for inst in self._instr_acqs:
            inst.NumRepetitions = num_reps

    @property
    def SampleRate(self):
        return self._instr_acq.SampleRate
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        for inst in self._instr_acqs:
            inst.SampleRate = frequency_hertz
        logging.warn("All Sample Rates are set to the same value. You can set them separately.")

    @property
    def InputTriggerEdge(self):
        return self._instr_acq.TriggerInputEdge
    @InputTriggerEdge.setter
    def InputTriggerEdge(self, pol):
        for inst in self._instr_acqs:
            inst.TriggerInputEdge = pol

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instruments"], config_dict["TriggerSource"])

    def _get_current_config(self):
        if self.data_processor:
            proc_name = self.data_processor.Name
        else:
            proc_name = ''
        ret_dict = {
            'Name' : self.Name,
            'instruments' : self._instr_ids,
            'Type' : self.__class__.__name__,
            'TriggerSource' : self._get_trig_src_params_dict(),
            'Processor' : proc_name
            }
        self.pack_properties_to_dict(['NumSamples', 'NumSegments', 'NumRepetitions', 'SampleRate', 'InputTriggerEdge', 'ChannelStates'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a ACQ with a configuration that is of type ' + dict_config['Type']
        self.NumSamples = dict_config['NumSamples']
        self.NumSegments = dict_config['NumSegments']
        self.NumRepetitions = dict_config['NumRepetitions']
        self.SampleRate = dict_config['SampleRate']
        self.InputTriggerEdge = dict_config['InputTriggerEdge']
        default_channel_states = []
        for inst in self._instr_acqs:
            num_channels = inst.AvailableChannels
            default_channel_states += [False]*num_channels
        self.ChannelStates = tuple(dict_config.get('ChannelStates', default_channel_states))
        trig_src_obj = TriggerInput.process_trigger_source(dict_config['TriggerSource'], lab)
        self.set_trigger_source(trig_src_obj)
        if dict_config['Processor'] != '':
            self.data_processor = lab.PROC(dict_config['Processor'])
