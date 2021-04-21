
class HALbase:
    def __init__(self, HAL_Name):
        self._name = HAL_Name
        self._man_activation = False

    @property
    def Name(self):
        return self._name

    @property
    def ManualActivation(self):
        return self._man_activation
    @ManualActivation.setter
    def ManualActivation(self, val):
        self._man_activation = val

    def _get_current_config(self):
        raise NotImplementedError()

    def _set_current_config(self, dict_config, lab):
        raise NotImplementedError()

    def pack_properties_to_dict(self, list_prop_names, ret_dict):
        for cur_prop in list_prop_names:
            ret_dict[cur_prop] = getattr(self, cur_prop)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def prepare_initial(self):
        pass

    def prepare_final(self):
        pass
