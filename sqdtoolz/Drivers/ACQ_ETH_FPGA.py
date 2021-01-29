import Pyro4

Pyro4.config.SERIALIZER = 'serpent'
Pyro4.config.PICKLE_PROTOCOL_VERSION = 2
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle','json', 'marshal', 'serpent'])

# from uqtools import Parameter
import pickle

class RemoteFPGA(object):
    
    def __init__(self, uri, remote_name, name=None):
        self._proxy = Pyro4.Proxy(uri)
        if remote_name not in self._proxy.get_instrument_names():
            raise ValueError('Instrument {} not recognized by server.'.format(remote_name))
        self._remote_name = remote_name
        self._name = remote_name if name is None else name
        self._pnames = self._proxy.get_parameter_names(self._remote_name)
        self._fnames = self._proxy.get_function_names(self._remote_name)
    
    def update(self):
        self._pnames = self._proxy.get_parameter_names(self._remote_name)
        self._fnames = self._proxy.get_function_names(self._remote_name)
        
    def set_app(self, appname):
        result = self._proxy.set_app(self._remote_name, appname)
        self.update()
        return result
    
    def get(self, pname, **kwargs):
        """Query value of parameter `pname`. kwargs are ignored."""
        return self._proxy.ins_get(self._remote_name, pname, kwargs)
    
    def set(self, pname, *args, **kwargs):
        """Set value of parameter `pname` to `value`. kwargs are ignored."""
        return self._proxy.ins_set(self._remote_name, pname, args, kwargs)
    
    def call(self, pname, *args, **kwargs):
        result =  self._proxy.ins_call(self._remote_name, pname, args, kwargs)
#         return result
        try:
            return pickle.loads(bytes(result, encoding='utf-8'), encoding='bytes')
        except TypeError:
            return result
        except pickle.UnpicklingError:
            return result
    
    def __dir__(self):
        attrs = dir(super(RemoteFPGA, self))
        attrs += self._proxy.get_parameter_names(self._remote_name)
        attrs += self._proxy.get_function_names(self._remote_name)
        return list(set(attrs))
    
    def __getattr__(self, pname):
        """
        Return method or construct `Parameter` for instrument attribute `pname`.
        """
        if pname in self._pnames:
            kwargs = {}
            kwargs['name'] = '{0}.{1}'.format(self._name, pname)
            kwargs['get_func'] = lambda: self.get(pname)
            kwargs['set_func'] = lambda value: self.set(pname, value)
            return Parameter(**kwargs)
        elif pname in self._fnames:
            function_spec = self._proxy.get_function_spec(self._remote_name, pname)
            if function_spec is not None:
                return lambda *args, **kwargs: self.call(pname, *args, **kwargs)
        raise AttributeError('Instrument {0} has no parameter or function "{1}". If you changed the FPGA app, then try update()'
                             .format(self._name, pname))
    
    def __setattr__(self, pname, value):
        """Block accidential attribute assignment."""
        if pname.startswith('_'):
            return super(RemoteFPGA, self).__setattr__(pname, value)
        if (hasattr(self, pname) and not callable(value) and 
            (not hasattr(value, 'get') or not hasattr(value, 'set'))):
            raise AttributeError(
                ('Can only assign Parameter objects or callables to {0}. ' + 
                'Use {0}.set(value) to set the value of {0}.').format(pname)
            )
        else:
            super(RemoteFPGA, self).__setattr__(pname, value)

    def __repr__(self):
        parts = super(RemoteFPGA, self).__repr__().split(' ')
        # <uqtools.qtlab.Instrument "{name}" ({qtlab_name}) at 0x...>
        parts[1] = '"{0}"'.format(self._name)
        if self._name != self._remote_name:
            parts.insert(2, '({0})'.format(self._remote_name))
        return ' '.join(parts)

with open(r'R:/EQUS-SQDLab/DataAnalysis/Notebooks/qcodes/FPGA_Rack1_URI.txt', 'r') as fh:
    fpga = RemoteFPGA(fh.read(), 'fpga')

a = 0

#To set number of samples to take
#fpga.get('tv_samples')
#fpga.set('tv_samples',256)

#To set the number of repetitions to take, use
#fpga.get('tv_segments')
#fpga.set('tv_segments',2)

#To get data (as a bunch; needs to be desegmented - e.g. chunks of 256 etc...).
#Okay - it's packed as channels, segments, samples
#fpga.call('get_data')

#To get available parameters:
#fpga.__dir__()
