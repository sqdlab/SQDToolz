import Pyro4

Pyro4.config.SERIALIZER = 'serpent'
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle','json', 'marshal', 'serpent'])

# from uqtools import Parameter
import pickle
import qcodes

from qcodes import Instrument, InstrumentChannel

DAC_TO_VOLT = 1/1000

class QcodesRemoteClient(object):
    
    def __init__(self, uri, remote_name, name=None):
        self._proxy = Pyro4.Proxy(uri)
        if remote_name not in self._proxy.get_instrument_names():
            raise ValueError('Instrument {} not recognized by server.'.format(remote_name))
        self._remote_name = remote_name
        self._name = remote_name if name is None else name
        self._pnames = self._proxy.get_parameters(self._remote_name)
        # self._fnames = self._proxy.get_function_names(self._remote_name)
    
    def update(self):
        # pass
        self._pnames = self._proxy.get_parameters(self._remote_name)
        # self._fnames = self._proxy.get_function_names(self._remote_name)
        
    
    def get(self, pname):
        """Query value of parameter `pname`. kwargs are ignored."""
        return self._proxy.ins_get(self._remote_name, pname)
    
    def set(self, pname, *args):
        """Set value of parameter `pname` to `value`. kwargs are ignored."""
        return self._proxy.ins_set(self._remote_name, pname, args)
    
    # def call(self, pname, *args, **kwargs):
    #     result =  self._proxy.ins_call(self._remote_name, pname, args, kwargs)
    #     return result
    #     # try:
    #     #     return pickle.loads(bytes(result, encoding='utf-8'), encoding='bytes')
    #     # except TypeError:
    #     #     return result
    #     # except pickle.UnpicklingError:
    #     #     return result
    
    # def __dir__(self):
    #     attrs = dir(super(QcodesRemoteClient, self))
    #     attrs += self._proxy.get_parameters(self._remote_name)
    #     attrs += self._proxy.get_function_names(self._remote_name)
    #     return list(set(attrs))
    
    # def __getattr__(self, pname):
    #     """
    #     Return method or construct `Parameter` for instrument attribute `pname`.
    #     """
    #     if pname in self._pnames:
    #         kwargs = {}
    #         kwargs['name'] = '{0}.{1}'.format(self._name, pname)
    #         kwargs['get_func'] = lambda: self.get(pname)
    #         kwargs['set_func'] = lambda value: self.set(pname, value)
    #         return Parameter(**kwargs)
    #     elif pname in self._fnames:
    #         function_spec = self._proxy.get_function_spec(self._remote_name, pname)
    #         if function_spec is not None:
    #             return lambda *args, **kwargs: self.call(pname, *args, **kwargs)
    #     raise AttributeError('Instrument {0} has no parameter or function "{1}".'
    #                          .format(self._name, pname))
    
    # def __setattr__(self, pname, value):
    #     """Block accidential attribute assignment."""
    #     if pname.startswith('_'):
    #         return super(QcodesRemoteClient, self).__setattr__(pname, value)
    #     if (hasattr(self, pname) and not callable(value) and 
    #         (not hasattr(value, 'get') or not hasattr(value, 'set'))):
    #         raise AttributeError(
    #             ('Can only assign Parameter objects or callables to {0}. ' + 
    #             'Use {0}.set(value) to set the value of {0}.').format(pname)
    #         )
    #     else:
    #         super(QcodesRemoteClient, self).__setattr__(pname, value)

    # def __repr__(self):
    #     parts = super(QcodesRemoteClient, self).__repr__().split(' ')
    #     # <uqtools.qtlab.Instrument "{name}" ({qtlab_name}) at 0x...>
    #     parts[1] = '"{0}"'.format(self._name)
    #     if self._name != self._remote_name:
    #         parts.insert(2, '({0})'.format(self._remote_name))
    #     return ' '.join(parts)

class IVVI_pyro_channel(InstrumentChannel):

    def __init__(self, parent, ivvi, ch_ind, name):
        super().__init__(parent, name)
        self.ch_ind = ch_ind
        self._ivvi = ivvi
    
    @property
    def Output(self):
        return True
    @Output.setter
    def Output(self, val):
        pass
        
    @property
    def Voltage(self):
        return self._ivvi.get('dac{:d}'.format(self.ch_ind))*DAC_TO_VOLT
    @Voltage.setter
    def Voltage(self, val):
        self._ivvi.set('dac{:d}'.format(self.ch_ind), val/DAC_TO_VOLT)
        
    @property
    def RampRate(self):
        # harc_coded because the pyro server currently exposes only parameters.
        return 10/0.1/DAC_TO_VOLT
    @RampRate.setter
    def RampRate(self, val):
        pass

class IVVI_pyro(Instrument):

    def __init__(self, url_location=r'Z:\DataAnalysis\Notebooks\qcodes\IVVI_server_uri.txt', **kwargs):
        super().__init__(**kwargs)
        with open(url_location, 'r') as fh:
            uri = fh.read()
            print(uri)

        self._ivvi = QcodesRemoteClient(uri, 'ivvi')

        for ch_ind in range(1,16+1):
            leName = f'CH{ch_ind}'
            cur_module = IVVI_pyro_channel(self, self._ivvi, ch_ind, leName)
            self.add_submodule(leName, cur_module)    #Name is christened inside the channel object...