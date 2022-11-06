from sqdtoolz.HAL.HALbase import*

class GENtherm(HALbase):
    def __init__(self, hal_name, lab, instr_therm_channel):
        HALbase.__init__(self, hal_name)
        self._instr_therm = lab._get_instrument(instr_therm_channel)
        self._instr_id = instr_therm_channel
        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def Temperature(self):
        return self._instr_therm.Temperature

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            #Ignoring ManualActivation
            }
        self.pack_properties_to_dict(['Temperature'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a Thermometer with a configuration that is of type ' + dict_config['Type']
