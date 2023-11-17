
class DecisionBlock:
    def get_params(self):
        return self._get_current_config()

    def _get_current_config(self):
        raise NotImplementedError()

    def _set_current_config(self, dict_config, lab):
        raise NotImplementedError()
