from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.HAL.ZI.ZIbase import ZIbase
import laboneq.simple as lbeqs
from laboneq.dsl.quantum import (
    QPU,
    QuantumElement,
    QuantumOperations,
    QuantumParameters,
    Transmon,
)
import inspect
from sqdtoolz.HAL.ZI.QuantumElements import *

class ZIQuantumElement(HALbase, ZIbase):
    def __init__(self, element_name, lab, cls_zi_quantum_element:type[QuantumElement], **kwargs):
        HALbase.__init__(self, element_name)
        
        lab._register_HAL(self)
        self._setup_zi_element(cls_zi_quantum_element, kwargs)
        assert len(kwargs) == 0, "Do not supply arguments other than relevant signals. Set parameters explictly after instantiation..."

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict['Name'], lab, globals()[dict_config['ZI_QuantumElement']], **dict_config['ZI_QuantumElementEx'])

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        elif '_elem_params' in self.__dict__ and name in self._elem_params:
            return getattr(self._zi_qelem.parameters, name)
        else:
            raise AttributeError(f"The \"{self._qelem_name}\" object does not have an parameter '{name}'")

    def __setattr__(self, name, value):
        if '_elem_params' in self.__dict__ and name in self._elem_params:
            setattr(self._zi_qelem.parameters, name, value)
        else:
            self.__dict__[name] = value

    def _setup_zi_element(self, cls_zi_quantum_element, elem_params):
        self._qelem_name = cls_zi_quantum_element.__name__
        signals = {}
        self.signals = {}
        for cur_signal in cls_zi_quantum_element.REQUIRED_SIGNALS:
            assert cur_signal in elem_params, f"Must supply \"{cur_signal}\" signal"
            signals[cur_signal] = elem_params.pop(cur_signal)
            self.signals[cur_signal] = signals[cur_signal]
        self._zi_qelem = cls_zi_quantum_element(uid=self.Name, signals=signals)

        #Check if the operations class is just the class name with Operations appeneded. Otherwise, if the standard is not adhered,
        #search for it...
        zi_ops_name = cls_zi_quantum_element.__name__ + 'Operations'
        if zi_ops_name in globals():
            cur_zi_ops_class = globals()[zi_ops_name]
            if not (hasattr(cur_zi_ops_class, 'QUBIT_TYPES') and cur_zi_ops_class.QUBIT_TYPES == cls_zi_quantum_element):
                zi_ops_name = ''
        else:
            zi_ops_name = ''
        if zi_ops_name == '':
            print(f"{cls_zi_quantum_element.__name__ + 'Operations'} not found. Try to adhere to the standard of defining the operations class with the \'Operations\' suffix and defining the correct \'QUBIT_TYPES\' attribute.")
            qop_classes = [globals()[x] for x in globals() if inspect.isclass(globals()[x]) and issubclass(globals()[x], QuantumOperations)]
            qop_classes = [x for x in qop_classes if x.QUBIT_TYPES == cls_zi_quantum_element] #TODO: Change if QUBIT_TYPES can be a list...
            assert len(qop_classes) < 2, f"There are multiple QuantumOperations classes supporting {self._qelem_name}."
            assert len(qop_classes) > 0, f"There are no QuantumOperations classes supporting {self._qelem_name}."
            print(f"Found the class {qop_classes[0].__name__}. Again, try to name it {self._qelem_name+'Operations'} instead to adhere to a standard.")
            zi_ops_name = qop_classes[0].__name__
            a=0
        self._zi_qops = globals()[zi_ops_name]

        #Filter out all the capitalised parameters in the associated parameters
        attributes = inspect.getmembers(cls_zi_quantum_element.PARAMETERS_TYPE, lambda a: not(inspect.isroutine(a)))
        attributes = [x[0] for x in attributes if not x[0].startswith('__') and x[0]!='' and x[0][0].isupper()]
        self._elem_params = attributes

    def get_ZI_parameters(self):
        return self._zi_qelem, self._zi_qops

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__,
            'ManualActivation' : self.ManualActivation,
            'ZI_QuantumElement' : self._qelem_name,
            'ZI_QuantumElementEx': self.signals
            }
        for cur_param in self._elem_params:
            ret_dict[cur_param] = getattr(self._zi_qelem.parameters, cur_param)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config.pop('Type') == self.__class__.__name__, 'Cannot set configuration to a ZIQuantumElement with a configuration that is of type ' + dict_config['Type']
        self.ManualActivation = dict_config.pop('ManualActivation', False)
        dict_config.pop('Name')

        self._setup_zi_element(globals()[dict_config.pop('ZI_QuantumElement')], dict_config.pop('ZI_QuantumElementEx'))
        
        for cur_param in dict_config:
            setattr(self._zi_qelem.parameters, cur_param, dict_config[cur_param])

if __name__=='__main__':
    from sqdtoolz.Laboratory import Laboratory
    lab = Laboratory('', 'temp')
    test_elem = ZIQuantumElement('testcpl', lab, TunableTransmonCouplerFixed, flux='q0/flux')
    dict_config = test_elem._get_current_config()
    ZIQuantumElement.fromConfigDict(dict_config, lab)
    lab.HAL('testcpl')._set_current_config(dict_config, lab)
    a=0
