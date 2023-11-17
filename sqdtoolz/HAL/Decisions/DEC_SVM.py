from sqdtoolz.HAL.DecisionBlock import DecisionBlock

class DEC_SVM(DecisionBlock):
    def __init__(self, eqns):
        #eqns is given as list of (a,b,c) where ax+by>c
        self.set_equations(eqns)

    @classmethod
    def fromConfigDict(cls, config_dict):
        assert 'Type' in config_dict, "Configuration dictionary does not have the key: type"
        assert config_dict['Type'] == cls.__name__, "Configuration dictionary has the wrong type."
        for cur_key in ["Equations"]:
            assert cur_key in config_dict, "Configuration dictionary does not have the key: " + cur_key
        return cls(config_dict["Equations"])

    def set_equations(self, eqns):
        assert isinstance(eqns, list), "Equations in eqns must be given as a list of tuples (a,b,c) where ax+by>c"
        for x in eqns:
            assert isinstance(x, list) or isinstance(x, tuple), "Equations in eqns must be given as a list of tuples (a,b,c) where ax+by>c"
            assert len(x) == 3, "Equations in eqns must be given as a list of tuples (a,b,c) where ax+by>c"
        self._eqns = [x[:] for x in eqns]

    def set_equation(self, eqn, index):
        assert isinstance(eqn, list) or isinstance(eqn, tuple), "Equations in eqns must be given as a list of tuples (a,b,c) where ax+by>c"
        assert len(eqn) == 3, "Equations in eqns must be given as a list of tuples (a,b,c) where ax+by>c"
        assert index < len(self._eqns), "Supplied index must match an equation index already defined in the SVM..."
        self._eqns[index] = eqn[:]

    def _get_current_config(self):
        ret_dict = {
            'Type' : self.__class__.__name__,
            'Equations' : self._eqns
            }
        return ret_dict

    def _set_current_config(self, dict_config):
        assert dict_config['Type'] == self.__class__.__name__, f"The configuration dictionary is of wrong type (i.e. {dict_config['Type']}) for DEC_SVM."
        self.set_equations(dict_config['Equations'])
