from sqdtoolz.HAL.TriggerPulse import*
from sqdtoolz.HAL.HALbase import*

class DDG(TriggerOutputCompatible, HALbase):
    '''
    Class to handle interfacing with digital delay generators.
    '''

    def __init__(self, hal_name, lab, instr_ddg_name):
        HALbase.__init__(self, hal_name)
        lab._register_HAL(self)
        #
        self._instr_ddg = lab._get_instrument(instr_ddg_name)
        #Assemble the Trigger objects
        instTrigSrcs = self._instr_ddg.get_all_trigger_sources()
        self._output_trigs = {}
        for cur_output_src in instTrigSrcs:
            cur_trig_name = cur_output_src[0]
            self._output_trigs[cur_trig_name] = Trigger(self, cur_trig_name, cur_output_src[1])

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
            'type' : 'DDG',
            'triggers' : trigDict
            }
        return retDict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['type'] == 'DDG', 'Cannot set configuration to a DDG with a configuration that is of type ' + dict_config['type']
        for cur_trig_name in dict_config['triggers']:
            self.get_trigger_output(cur_trig_name)._set_current_config(dict_config['triggers'][cur_trig_name])
