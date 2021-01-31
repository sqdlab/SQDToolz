from numpy import pi
from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals

import Pyro4

Pyro4.config.SERIALIZER = 'serpent'
Pyro4.config.PICKLE_PROTOCOL_VERSION = 2
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle','json', 'marshal', 'serpent'])
# from uqtools import Parameter
import pickle

class ETHFPGA(Instrument):
    def __init__(self, name, uri, **kwargs):
        super().__init__(name, **kwargs)

        self._remote_name = 'fpga'
        with open(uri, 'r') as fh:
            self._uri = uri
            
            self._proxy = Pyro4.Proxy(fh.read())
            if self._remote_name not in self._proxy.get_instrument_names():
                raise ValueError('Instrument {} not recognized by server.'.format(self._remote_name))
            
    def _set_app(self, appname):
        result = self._proxy.set_app(self._remote_name, appname)
        return result
    
    def _get(self, pname, **kwargs):
        """Query value of parameter `pname`. kwargs are ignored."""
        return self._proxy.ins_get(self._remote_name, pname, kwargs)
    
    def _set(self, pname, *args, **kwargs):
        """Set value of parameter `pname` to `value`. kwargs are ignored."""
        return self._proxy.ins_set(self._remote_name, pname, args, kwargs)
    
    def _call(self, pname, *args, **kwargs):
        result =  self._proxy.ins_call(self._remote_name, pname, args, kwargs)
#         return result
        try:
            return pickle.loads(bytes(result, encoding='utf-8'), encoding='bytes')
        except TypeError:
            return result
        except pickle.UnpicklingError:
            return result
    
    def __dir__(self):
        '''
        Get available parameters...
        '''
        attrs = []#dir(super(ETHFPGA, self))
        attrs += self._proxy.get_parameter_names(self._remote_name)
        attrs += self._proxy.get_function_names(self._remote_name)
        return list(set(attrs))

    @property
    def NumSamples(self):
        return self._get('tv_samples')
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self._set('tv_samples', num_samples)

    @property
    def NumSegments(self):
        return self._get('tv_segments')
    @NumSegments.setter
    def NumSegments(self, num_reps):
        self._set('tv_segments', num_reps)

    #TODO: WRITE A DDC PROPERTY - look up ddc_if2 and ddc_adc1 as well...
    # @property
    # def DdcIfFrequency(self):
    #     return self._get('ddc_adc1')
    # @DdcIfFrequency.setter
    # def DdcIfFrequency(self, freqHertz):
    #     self._set('ddc_adc1', freqHertz)

    @property
    def SampleRate(self):
        return self._call('get_sample_rate')

    
    @property
    def TriggerInputEdge(self):
        return 1    #Always positive edge
    # @TriggerInputEdge.setter
    # def TriggerInputEdge(self, pol):
    #     self._trigger_edge = pol
    

#To get data (as a bunch; needs to be desegmented - e.g. chunks of 256 etc...).
#Okay - it's packed as channels, segments, samples
#fpga.call('get_data')

