
class VariableBase:
    def __init__(self, name):
        self._name = name
    
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

class VariableInternal(VariableBase):
    def __init__(self, name, init_val = 0.0):
        super().__init__(name)
        self._val = init_val

    def get_raw(self):
        return self._val

    def set_raw(self, value):
        self._val = value
    
class VariableProperty(VariableBase):
    def __init__(self, name, halObj, prop_name):
        super().__init__(name)
        assert hasattr(halObj, prop_name), "The given object does not have a property " + prop_name
        self._obj = halObj
        self._prop = prop_name

    def get_raw(self):
        return getattr(self._obj, self._prop)

    def set_raw(self, value):
        setattr(self._obj, self._prop, value)

class VariableSpaced(VariableBase):
    def __init__(self, name, var_1, var_2, space_val):
        super().__init__(name)
        self._var_1 = var_1
        self._var_2 = var_2
        self.space_val = space_val

    def get_raw(self):
        return self._var_1.get_raw()

    def set_raw(self, value):
        self._var_1.set_raw(value)
        self._var_2.set_raw(value + self.space_val)
