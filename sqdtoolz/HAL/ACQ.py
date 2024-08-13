from sqdtoolz.HAL.TriggerPulse import*
from sqdtoolz.HAL.HALbase import*

from sqdtoolz.HAL.Decisions.DEC_SVM import DEC_SVM  #TODO: Automate this...

class ACQ(TriggerInputCompatible, TriggerInput, HALbase):
    def __init__(self, hal_name, lab, instr_acq_name):
        HALbase.__init__(self, hal_name)
        self._instr_id = instr_acq_name
        self._instr_acq = lab._get_instrument(instr_acq_name)
        if lab._register_HAL(self):
            #
            self._trig_src_obj = None
            self.data_processor = None
            self._post_processors = []
            self.decision_blocks = []

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def IsACQhal(self):
        return True

    @property
    def ChannelStates(self):
        return self._instr_acq.ChannelStates
    @ChannelStates.setter
    def ChannelStates(self, ch_states):
        self._instr_acq.ChannelStates = ch_states

    @property
    def NumSamples(self):
        return self._instr_acq.NumSamples
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self._instr_acq.NumSamples = int(num_samples)

    @property
    def NumSegments(self):
        return self._instr_acq.NumSegments
    @NumSegments.setter
    def NumSegments(self, num_segs):
        self._instr_acq.NumSegments = int(num_segs)

    @property
    def NumRepetitions(self):
        return self._instr_acq.NumRepetitions
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps):
        self._instr_acq.NumRepetitions = int(num_reps)

    @property
    def SampleRate(self):
        return self._instr_acq.SampleRate
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self._instr_acq.SampleRate = frequency_hertz

    @property
    def InputTriggerEdge(self):
        return self._instr_acq.TriggerInputEdge
    @InputTriggerEdge.setter
    def InputTriggerEdge(self, pol):
        self._instr_acq.TriggerInputEdge = pol
    
    @property
    def SupportedDecisionBlocks(self):
        return self._instr_acq.SupportedDecisionBlocks

    def _get_all_trigger_inputs(self):
        return [self]
    def _get_instr_trig_src(self):
        return self._trig_src_obj
    def _get_instr_input_trig_edge(self):
        return self.InputTriggerEdge
    def _get_timing_diagram_info(self):
        return {'Type' : 'BlockShaded', 'Period' : self.NumSamples / self.SampleRate, 'TriggerType' : 'Edge'}
    def _get_parent_HAL(self):
        return self

    def set_decision_block(self, DEC_objs):
        assert isinstance(DEC_objs, list), "DEC_objs must be a list of DEC-objects - i.e. corresponding to ALL the outputs of the processing pipeline on the acquired data."
        for DEC_obj in DEC_objs:
            if DEC_obj == None:
                continue
            cur_dec_type = DEC_obj.__class__.__name__
            assert cur_dec_type in self.SupportedDecisionBlocks, f"This ACQ instrument does not support {cur_dec_type}."
        self.decision_blocks = DEC_objs

    def set_data_processor(self, proc_obj):
        self.data_processor = proc_obj

    def set_extra_post_processors(self, list_proc_objs):
        assert self.data_processor != None, "Set/use set_data_processor first to set the primary driver-integrated processor. This function is to set extra/auxiliary processors."
        self._post_processors = list_proc_objs[:]

    def get_data(self):
        ret_data = self._instr_acq.get_data(data_processor = self.data_processor, decision_blocks = self.decision_blocks)
        for cur_proc in self._post_processors:
            cur_proc.push_data(ret_data['data'])
            ret_data['data'] = cur_proc.get_all_data()
        return ret_data

    def set_trigger_source(self, trig_src_obj):
        assert isinstance(trig_src_obj, TriggerOutput) or trig_src_obj == None, "Must supply a valid Trigger Output object (i.e. digital trigger output like a marker)."
        self._trig_src_obj = trig_src_obj

    def set_acq_params(self, reps, segs, samples):
        self.NumRepetitions = reps
        self.NumSegments = segs
        self.NumSamples = samples

    def get_trigger_source(self):
        '''
        Get the Trigger object corresponding to the trigger source.
        '''
        return self._trig_src_obj

    def _get_all_PROC_dependencies(self):
        ret_list = []
        if self.data_processor:
            ret_list.append(self.data_processor)
        return ret_list + self._post_processors

    def _get_trigger_sources(self):
        return [self._trig_src_obj]

    def _get_current_config(self):
        if self.data_processor:
            proc_name = self.data_processor.Name
        else:
            proc_name = ''
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            'TriggerSource' : self._get_trig_src_params_dict(),
            'Processor' : proc_name,
            'ExProcessors' : [x.Name for x in self._post_processors]
            }
        self.pack_properties_to_dict(['NumSamples', 'NumSegments', 'NumRepetitions', 'SampleRate', 'InputTriggerEdge', 'ChannelStates'], ret_dict)
        if len(self.decision_blocks) > 0:
            ret_dict['DecisionBlocks'] = [None if x == None else x._get_current_config() for x in self.decision_blocks]
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a ACQ with a configuration that is of type ' + dict_config['Type']
        self.NumSamples = dict_config['NumSamples']
        self.NumSegments = dict_config['NumSegments']
        self.NumRepetitions = dict_config['NumRepetitions']
        self.SampleRate = dict_config['SampleRate']
        self.InputTriggerEdge = dict_config['InputTriggerEdge']
        self.ChannelStates = tuple( dict_config.get('ChannelStates', [True]+[False]*(self._instr_acq.AvailableChannels-1)) )
        trig_src_obj = TriggerInput.process_trigger_source(dict_config['TriggerSource'], lab)
        self.set_trigger_source(trig_src_obj)
        if dict_config['Processor'] != '':
            self.data_processor = lab.PROC(dict_config['Processor'])
        self._post_processors = []
        if 'ExProcessors' in dict_config:
            for cur_proc in dict_config['ExProcessors']:
                self._post_processors.append(lab.PROC(cur_proc))
        if 'DecisionBlocks' in dict_config:
            self.decision_block = []
            for cur_dec_block in dict_config['DecisionBlocks']:
                if cur_dec_block == None:
                    self.decision_block.append(None)
                    continue
                cur_dec_type = globals()[cur_dec_block['Type']]
                self.decision_block.append( cur_dec_type.fromConfigDict(cur_dec_block) )
