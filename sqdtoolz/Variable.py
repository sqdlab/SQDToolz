
class VariableBase:
    def __init__(self, name):
        self._name = name

    def __new__(cls, *args, **kwargs):
        if len(args) == 0:
            name = kwargs,get('name', '')
            if name == '':
                name = kwargs,get('Name', '')
        else:
            name = args[0]
        assert isinstance(name, str) and name != '', "Name parameter was not passed or does not exist as the first argument in the variable class initialisation?"
        if len(args) < 2:
            lab = kwargs.get('lab', None)
            if lab == None:
                lab = kwargs.get('Lab', None)
        else:
            lab = args[1]
        assert lab.__class__.__name__ == 'Laboratory' and lab != None, "Lab parameter was not passed or does not exist as the second argument in the variable class initialisation?"

        prev_exists = lab.VAR(name)
        if prev_exists:
            assert isinstance(prev_exists, cls), f"A different VAR type ({prev_exists.__class__.__name__}) already exists by this name."
            return prev_exists
        else:
            return super(cls.__class__, cls).__new__(cls)
    
    @property
    def Name(self):
        return self._name

    @property
    def Value(self):
        return self.get_raw()
    @Value.setter
    def Value(self, val):
        self.set_raw(val)

    def set_raw(self, value):
        """Set value of the parameter."""
        raise NotImplementedError()

    def get_raw(self):
        """Return value of the parameter."""
        raise NotImplementedError()

    def _get_current_config(self):
        raise NotImplementedError()

    def _set_current_config(self, dict_config):
        raise NotImplementedError()

class VariableInternal(VariableBase):
    def __init__(self, name, lab, init_val = None):
        super().__init__(name)
        if lab._register_VAR(self):
            if init_val == None:
                self._val = 0.0
        if init_val != None:
            self._val = init_val    #i.e override the value if reinitialised with an initial-value - otherwise, preserve previous instance's value...

    @classmethod
    def fromConfigDict(cls, name, config_dict, lab):
        return cls(name, lab, config_dict["Value"])

    def get_raw(self):
        return self._val

    def set_raw(self, value):
        self._val = value

    def _get_current_config(self):
        return {
            'Value' : self._val,
            'Type'  : self.__class__.__name__
        }

    def _set_current_config(self, dict_config):
        assert dict_config['Type'] == self.__class__.__name__
        self._val = dict_config['Value']
    
class VariableProperty(VariableBase):
    def __init__(self, name, lab, sqdtoolz_obj, prop_name):
        super().__init__(name)
        self._lab = lab
        self._obj_res_list = lab._resolve_sqdobj_tree(sqdtoolz_obj)
        halObj = self._lab._get_resolved_obj(self._obj_res_list)
        assert hasattr(halObj, prop_name), "The given object does not have a property " + prop_name
        self._prop = prop_name
        #
        lab._register_VAR(self)

    @classmethod
    def fromConfigDict(cls, name, config_dict, lab):
        obj = lab._get_resolved_obj(config_dict["ResList"])
        prop = config_dict["Property"]
        setattr(obj, prop, config_dict["Value"])
        return cls(name, lab, obj, prop)   #TODO: Add custom flag to make this a bit less inefficient... Not that bad as it should only be used in cold-loading anyway...

    def get_raw(self):
        obj = self._lab._get_resolved_obj(self._obj_res_list)
        return getattr(obj, self._prop)

    def set_raw(self, value):
        obj = self._lab._get_resolved_obj(self._obj_res_list)
        setattr(obj, self._prop, value)

    def _get_current_config(self):
        return {
            'Value' : self.Value,
            'Type'  : self.__class__.__name__,
            'Property' : self._prop,
            'ResList' : self._obj_res_list
        }

    def _set_current_config(self, dict_config):
        assert dict_config['Type'] == self.__class__.__name__
        self._obj_res_list = dict_config['ResList']
        self._prop = dict_config['Property']

class VariableSpaced(VariableBase):
    def __init__(self, name, lab, var_1, var_2, space_val):
        super().__init__(name)
        self._lab = lab
        self._var_1 = var_1
        self._var_2 = var_2
        self.space_val = space_val
        #
        lab._register_VAR(self)

    @classmethod
    def fromConfigDict(cls, name, config_dict, lab):
        return cls(name, lab, config_dict["Var1"], config_dict["Var2"], config_dict["Space"])

    def get_raw(self):
        return self._lab.VAR(self._var_1).get_raw()

    def set_raw(self, value):
        self._lab.VAR(self._var_1).set_raw(value)
        self._lab.VAR(self._var_2).set_raw(value + self.space_val)

    def _get_current_config(self):
        return {
            'Value' : self.Value,
            'Var1'  : self._var_1,
            'Var2'  : self._var_2,
            'Space' : self.space_val,
            'Type'  : self.__class__.__name__
        }

    def _set_current_config(self, dict_config):
        assert dict_config['Type'] == self.__class__.__name__
        self._var_1 = dict_config['Var1']
        self._var_2 = dict_config['Var2']
        self.space_val = dict_config['Space']
