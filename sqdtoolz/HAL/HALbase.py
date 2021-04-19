
class HALbase:
    def __init__(self, HAL_Name):
        self._name = HAL_Name

    @property
    def Name(self):
        return self._name

    def _get_current_config(self):
        raise NotImplementedError()

    def _set_current_config(self, dict_config, lab):
        raise NotImplementedError()

    def pack_properties_to_dict(self, list_prop_names, ret_dict):
        for cur_prop in list_prop_names:
            ret_dict[cur_prop] = getattr(self, cur_prop)
