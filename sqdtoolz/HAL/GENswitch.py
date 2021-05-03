from sqdtoolz.HAL.HALbase import*

class GENswitch(HALbase):
    def __init__(self, hal_name, lab, instr_switch):
        #NOTE: the driver is presumed to be a single-pole many-throw switch (i.e. only one circuit route at a time).
        HALbase.__init__(self, hal_name)
        if lab._register_HAL(self):
            self._instr_id = instr_switch
            self._instr_switch = lab._get_instrument(instr_switch)
            self._switch_contacts = self._instr_switch.get_all_switch_contacts()

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def Position(self):
        return self._instr_switch.Position
    @Position.setter
    def Position(self, val):
        self._instr_switch.Position = val

    def get_possible_contacts(self):
        return self._switch_contacts[:]

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            'Position' : self.Position
            }
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a Voltage-Source with a configuration that is of type ' + dict_config['Type']
        self.Position = dict_config['Position']
