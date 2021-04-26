from sqdtoolz.HAL.TriggerPulse import*
from sqdtoolz.HAL.HALbase import*

class DDG(TriggerOutputCompatible, HALbase):
    '''
    Class to handle interfacing with digital delay generators.
    '''
    def __init__(self, hal_name, lab, instr_ddg_name):
        HALbase.__init__(self, hal_name)
        if lab._register_HAL(self):
            #Only initialise if it's a new instance
            self._instr_ddg = lab._get_instrument(instr_ddg_name)
            #Assemble the Trigger objects
            instTrigSrcs = self._instr_ddg.get_all_trigger_sources()
            self._output_trigs = {}
            for cur_output_src in instTrigSrcs:
                cur_trig_name = cur_output_src[0]
                self._output_trigs[cur_trig_name] = Trigger(self, cur_trig_name, cur_output_src[1])

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def RepetitionTime(self):
        return self._instr_ddg.RepetitionTime
    @RepetitionTime.setter
    def RepetitionTime(self, val):
        self._instr_ddg.RepetitionTime = val

    def _get_child(self, tuple_name_group):
        cur_name, cur_type = tuple_name_group
        if cur_name in self._output_trigs:
            return self._output_trigs[cur_name]
        return None

    def get_trigger_output(self, outputID):
        '''
        Returns a TriggerSource object 
        '''
        assert outputID in self._output_trigs, "Trigger output " + str(outputID) + " does not exist in " + self._name
        return self._output_trigs[outputID]

    def _get_trigger_output_by_id(self, outputID):
        return self.get_trigger_output(outputID)
    def _get_all_trigger_outputs(self):
        return list(self._output_trigs.keys())

    def get_all_outputs(self):
        return [self._output_trigs[x] for x in self._output_trigs]

    def set_trigger_output_params(self, trigOutputName, trigPulseDelay, trigPulseLength=-1, trigPulsePolarity=1):
        '''
        trigPulseLength must be positive (otherwise, it is not set)
        '''
        if (trigPulseLength > 0):
            self.get_trigger_output(trigOutputName).TrigPulseLength = 50e-9        
        self.get_trigger_output(trigOutputName).TrigPolarity = trigPulsePolarity
        self.get_trigger_output(trigOutputName).TrigPulseDelay = trigPulseDelay

    def _get_current_config(self):
        #Get settings for the trigger objects
        trigObjs = self.get_all_outputs()
        trigDict = {}
        for cur_trig in trigObjs:
            trigDict = {**trigDict, **cur_trig._get_current_config()}
        retDict = {
            'Name' : self.Name,
            'instrument' : self._instr_ddg.name,
            'Type' : self.__class__.__name__,
            'RepetitionTime' : self.RepetitionTime,
            'triggers' : trigDict
            }
        return retDict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a DDG with a configuration that is of type ' + dict_config['Type']
        for cur_trig_name in dict_config['triggers']:
            self.get_trigger_output(cur_trig_name)._set_current_config(dict_config['triggers'][cur_trig_name])
        self.RepetitionTime = dict_config['RepetitionTime']
