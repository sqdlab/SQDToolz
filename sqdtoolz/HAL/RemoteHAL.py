from xml.dom.minidom import Attr
from sqdtoolz.HAL.HALbase import*
import Pyro4
import logging

class RemoteHAL(HALbase):

    def __init__(self, hal_name, lab, proxy_uri):
        HALbase.__init__(self, hal_name)
        self.remote_obj = Pyro4.Proxy(proxy_uri)
        lab._register_HAL(self)

    def __getattribute__(self, __name: str):
        try:
            return super().__getattribute__(__name)
        except AttributeError:
            if __name == 'remote_obj':
                raise AttributeError
            else:
                return self.remote_obj.__getattr__(__name)

    def __setattr__(self, prop, value):
        if prop == 'remote_obj':
            super().__setattr__('remote_obj', value)
            return True
        else:
            try:
                actual_prop = self.remote_obj.__getattr__(prop)
                self.remote_obj.__setattr__(prop, value)
                return True
            except AttributeError:
                super().__setattr__(prop, value)

    def _get_current_config(self):
        ret_dict = {
            'Type' : self.__class__.__name__,
            #Ignoring ManualActivation
            }
        self.pack_properties_to_dict(['Name'] + list(self.remote_obj._pyroAttrs), ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a Voltage-Source with a configuration that is of type ' + dict_config['Type']
        dict_config.pop('Type')
        logging.warn("Cannot set configuration as RemoteHAL doesn't know what type of object it is.")