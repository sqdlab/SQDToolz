
class GEN:
    def __init__(self, name):
        self._name = name

    @property
    def Name(self):
        return self._name

    def _get_current_config(self):
        prop_names = [name for name, value in vars(type(self)).items() if isinstance(value, property)]

        retDict = {}
        retDict['type'] = 'GEN'
        retDict['GenericType'] = self.__class__.__name__
        for cur_prop in prop_names:
            retDict[cur_prop] = getattr(self, cur_prop)

        return retDict

    def _set_current_config(self, dict_config, instr_obj = None):
        assert retDict['type'] == 'GEN', "The dict_config dictionary must be for a type GEN."
        assert retDict['GenericType'] == self.__class__.__name__, f"The dict_config dictionary must be for this generic type ({self.__class__.__name__})"

        for cur_key in dict_config:
            assert hasattr(self, cur_key), "This HAL object does not have the attribute " + cur_key
            setattr(self, cur_key, dict_config[cur_key])
