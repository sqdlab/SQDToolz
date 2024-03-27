from sqdtoolz.HAL.HALbase import*

class GENswitchTrig(HALbase):
    def __init__(self, hal_name, lab, instr_switch):
        #NOTE: the driver is presumed to be a single-pole many-throw switch (i.e. only one circuit route at a time).
        HALbase.__init__(self, hal_name)
        self._instr_id = instr_switch
        self._instr_switch = lab._get_instrument(instr_switch)
        self._switch_contacts = self._instr_switch.get_all_switch_contacts()
        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def PositionInit(self):
        return self._instr_switch.PositionInit
    @PositionInit.setter
    def PositionInit(self, val):
        self._instr_switch.PositionInit = val

    def get_possible_contacts(self):
        return self._switch_contacts[:]

    def ManualTrigger(self):
        self._instr_switch.manual_trigger()
    
    def Hold(self):
        self._instr_switch.hold()

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            'PositionInit' : self.PositionInit
            #Ignoring ManualActivation
            }
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a Switch with a configuration that is of type ' + dict_config['Type']
        self.PositionInit = dict_config['PositionInit']
