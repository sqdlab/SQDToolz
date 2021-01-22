
class DDG:
    '''
    Class to handle interfacing with digital delay generators.
    '''

    def __init__(self, instr_ddg):
        '''
        '''
        self._instr_ddg = instr_ddg
        self._name = instr_ddg.name

    @property
    def name(self):
        return self._name

    def get_trigger_output(self, outputID):
        '''
        Returns a TriggerSource object 
        '''
        return self._instr_ddg.get_trigger_output(outputID)

    def get_all_outputs(self):
        return self._instr_ddg.get_all_trigger_sources()