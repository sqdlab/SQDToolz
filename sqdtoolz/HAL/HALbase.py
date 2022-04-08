from sqdtoolz.HAL.LockableProperties import LockableProperties

class HALbase(LockableProperties):
    def __init__(self, HAL_Name):
        self._name = HAL_Name
        self._man_activation = False

    def __new__(cls, *args, **kwargs):
        if len(args) == 0:
            hal_name = kwargs.get('hal_name', '')
        else:
            hal_name = args[0]
        assert isinstance(hal_name, str) and hal_name != '', "Parameter hal_name was not passed or does not exist as the first argument in the variable class initialisation?"
        if len(args) < 2:
            lab = kwargs.get('lab', None)
            if lab == None:
                lab = kwargs.get('Lab', None)
        else:
            lab = args[1]
        assert lab.__class__.__name__ == 'Laboratory' and lab != None, "Lab parameter was not passed or does not exist as the second argument in the variable class initialisation?"

        prev_exists = lab.HAL(hal_name, True)
        if prev_exists:
            assert isinstance(prev_exists, cls), f"A different HAL type ({prev_exists.__class__.__name__}) already exists by this name."
            return prev_exists
        else:
            return super(cls.__class__, cls).__new__(cls)

    def __str__(self):
        cur_dict = self._get_current_config()
        cur_str = ""
        for cur_key in cur_dict:
            cur_str += f"{cur_key}: {cur_dict[cur_key]}\n"
        return cur_str

    @property
    def Name(self):
        return self._name

    @property
    def Parent(self):
        return None

    @property
    def IsACQhal(self):
        return False

    def _get_child(self, tuple_name_group):
        raise NotImplementedError()

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
