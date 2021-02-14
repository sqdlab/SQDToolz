
class VariableBase:
    def __init__(self, name):
        self.name = name
    
    def set_raw(self, value):
        """Set value of the parameter."""
        raise NotImplementedError

    def get_raw(self):
        """Return value of the parameter."""
        raise NotImplementedError



class VariableInternal:
    def __init(self, name, init_val = 0.0):
        super.__init__(self, name)
        self._val = init_val

    def get_raw(self, value):
        return self._val

    def set_raw(self, value):
        self._val = value
    
class VariableProperty(VariableBase):
    def __init__(self, name, halObj, prop_name):
        super().__init__(name)
        assert hasattr(halObj, prop_name), "The given object does not have a property " + prop_name
        self._obj = halObj
        self._prop = prop_name

    def get_raw(self, value):
        return getattr(self._obj, self._prop)

    def set_raw(self, value):
        setattr(self._obj, self._prop, value)




