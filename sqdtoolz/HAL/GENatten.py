from sqdtoolz.HAL.HALbase import*

class GENatten(HALbase):
    def __init__(self, hal_name, lab, instr_atten_channel):
        HALbase.__init__(self, hal_name)
        self._instr_atten = lab._get_instrument(instr_atten_channel)
        self._instr_id = instr_atten_channel
        #
        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def Attenuation(self):
        return self._instr_atten.Attenuation
    @Attenuation.setter
    def Attenuation(self, val):
        self._instr_atten.Attenuation = val

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__
            #Ignoring ManualActivation here...
            }
        self.pack_properties_to_dict(['Attenuation'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a Attenuator with a configuration that is of type ' + dict_config['Type']
        self.Attenuation = dict_config.get('Attenuation', 0.0)
