from sqdtoolz.HAL.TriggerPulse import*

class DDG:
    '''
    Class to handle interfacing with digital delay generators.
    '''

    def __init__(self, instr_ddg):
        '''
        '''
        self._instr_ddg = instr_ddg
        self._name = instr_ddg.name
        #Assemble the Trigger objects
        instTrigSrcs = self._instr_ddg.get_all_trigger_sources()
        self._output_trigs = {}
        for cur_output_src in instTrigSrcs:
            cur_trig_name = cur_output_src[0]
            self._output_trigs[cur_trig_name] = Trigger(self, cur_trig_name, cur_output_src[1])

    @property
    def Name(self):
        return self._name

    def get_trigger_output(self, outputID):
        '''
        Returns a TriggerSource object 
        '''
        assert outputID in self._output_trigs, "Trigger output " + str(outputID) + " does not exist in " + self._name
        return self._output_trigs[outputID]

    def _get_trigger_output_by_id(self, outputID, ch_ID):
        return self.get_trigger_output(outputID)

    def get_trigger_source(self):
        '''
        Get the Trigger object corresponding to the trigger source.
        '''
        return None

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
            'instrument' : self.Name,
            'type' : 'DDG',
            'triggers' : trigDict
            }
        return retDict

    def _set_current_config(self, dict_config, instr_obj = None):
        assert dict_config['type'] == 'DDG', 'Cannot set configuration to a DDG with a configuration that is of type ' + dict_config['type']
        if (instr_obj != None):
            self._instr_ddg = instr_obj
        for cur_trig_name in dict_config['triggers']:
            self.get_trigger_output(cur_trig_name)._set_current_config(dict_config['triggers'][cur_trig_name])
