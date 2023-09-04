import numpy as np
from qcodes import Instrument, InstrumentChannel, VisaInstrument
import qcodes.utils.validators as valids

import time

import Pyro4

Pyro4.config.SERIALIZER = 'serpent'
Pyro4.config.PICKLE_PROTOCOL_VERSION = 2
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle','json', 'marshal', 'serpent'])
# from uqtools import Parameter
import pickle

class ETHFPGA(Instrument):
    def __init__(self, name, uri, app_name='TVMODEV02', **kwargs):
        super().__init__(name, **kwargs)

        self._proxy = None
        self._remote_name = 'fpga'
        with open(uri, 'r') as fh:
            self._uri = uri
            
            self._proxy = Pyro4.Proxy(fh.read())
            if self._remote_name not in self._proxy.get_instrument_names():
                raise ValueError('Instrument {} not recognized by server.'.format(self._remote_name))
        assert self._proxy != None, "The FPGA card was not properly initialised with the Pyro Server."
        
        self.add_parameter('mem_hold', label='Memory Hold', 
                           get_cmd=lambda : self._get('mem_hold'), vals=valids.Bool(),
                           set_cmd=lambda x : self._set('mem_hold', x), initial_value=False)        
        #!!!!!ONLY UserPin1 and UserPin4 are available in TVModeV02 !!!!!
        #TODO: Tie the trigger port selection to this internally via the HAL later...
        self.add_parameter('trigger_src_shot', label='Individual segment trigger', 
                           get_cmd=lambda : self._get('trigger_src_shot'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('trigger_src_shot', x), initial_value='UserPin1')
        self.add_parameter('trigger_src_ddc', label='DDC input trigger', 
                           get_cmd=lambda : self._get('trigger_src_ddc'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('trigger_src_ddc', x), initial_value='UserPin1')
        self.add_parameter('trigger_src_seq_start', label='Sequence start trigger', 
                           get_cmd=lambda : self._get('trigger_src_seq_start'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('trigger_src_seq_start', x), initial_value='UserPin4')

        #!!!!! Set small delays to avoid crosstalk !!!!! But what are the units?b
        self.add_parameter('trigger_acq_delay', label='Trigger acquisition delay', 
                           get_cmd=lambda : self._get('trigger_acq_delay'), vals=valids.Numbers(),
                           set_cmd=lambda x : self._set('trigger_acq_delay', x), initial_value=10.0)
        self.add_parameter('trigger_pulse_delay', label='Trigger pulse delay', 
                           get_cmd=lambda : self._get('trigger_pulse_delay'), vals=valids.Numbers(),
                           set_cmd=lambda x : self._set('trigger_pulse_delay', x), initial_value=10.0)

        #25MHz IF, straight ADC mapping
        self.add_parameter('ddc_adc1', label='ADC input for DDC1', 
                           get_cmd=lambda : self._get('ddc_adc1'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('ddc_adc1', x), initial_value='ADC1')
        self.add_parameter('ddc_adc2', label='ADC input for DDC2', 
                           get_cmd=lambda : self._get('ddc_adc2'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('ddc_adc2', x), initial_value='ADC2')
        self.add_parameter('ddc_if1', label='DDC1 IF downconversion frequency', 
                           get_cmd=lambda : self._get('ddc_if1'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('ddc_if1', x), initial_value='25MHz')
        self.add_parameter('ddc_if2', label='DDC2 IF downconversion frequency', 
                           get_cmd=lambda : self._get('ddc_if2'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('ddc_if2', x), initial_value='25MHz')
        
        #Default math: measure complex voltage
        self.add_parameter('math_f1', label='Math function 1', 
                           get_cmd=lambda : self._get('math_f1'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('math_f1', x), initial_value='1(a*b)')
        self.add_parameter('math_f2', label='Math function 2', 
                           get_cmd=lambda : self._get('math_f2'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('math_f2', x), initial_value='1(a*b)')
        self.add_parameter('math_a1', label='Math function 1 argument format for a',
                           get_cmd=lambda : self._get('math_a1'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('math_a1', x), initial_value='I1 + iQ1')
        self.add_parameter('math_a2', label='Math function 2 argument format for a',
                           get_cmd=lambda : self._get('math_a2'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('math_a2', x), initial_value='I2 + iQ2')
        self.add_parameter('math_b1', label='Math function 1 argument format for b',
                           get_cmd=lambda : self._get('math_b1'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('math_b1', x), initial_value='1*')
        self.add_parameter('math_b2', label='Math function 2 argument format for b',
                           get_cmd=lambda : self._get('math_b2'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('math_b2', x), initial_value='1*')
        
        #Boxcar FIR filter (refine with ctx_fpga_fir)
        self.add_parameter('fir_engine', label='FIR filter type',
                           get_cmd=lambda : self._get('fir_engine'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('fir_engine', x), initial_value='boxcar')
        self.add_parameter('fir_integration', label='FIR integration',
                           get_cmd=lambda : self._get('fir_integration'), vals=valids.Strings(),
                           set_cmd=lambda x : self._set('fir_integration', x), initial_value='none')
        self.add_parameter('fir_post_filtering', label='FIR post filtering enable', 
                           get_cmd=lambda : self._get('fir_post_filtering'), vals=valids.Bool(),
                           set_cmd=lambda x : self._set('fir_post_filtering', x), initial_value=False)
        
        #TODO: MAKE THESE HIGHER LEVEL PARAMETERS
        self.add_parameter('tv_decimation', label='Decimation downsampling factor on TV mode', 
                           get_cmd=lambda : self._get('tv_decimation'), vals=valids.Ints(),
                           set_cmd=lambda x : self._set('tv_decimation', x), initial_value=4)
        self.add_parameter('tv_averages', label='Number of TV averages', 
                           get_cmd=lambda : self._get('tv_averages'), vals=valids.Ints(),
                           set_cmd=lambda x : self._set('tv_averages', x), initial_value=1024)

        self.add_parameter('tv_use_seq_start', label='Use the sequence start trigger in cases of multiple segments',
                           get_cmd=lambda : self._get('tv_use_seq_start'), vals=valids.Bool(),
                           set_cmd=lambda x : self._set('tv_use_seq_start', x), initial_value=False)

        self.add_parameter('tv_two_channel_mode', label='Enable 2-channel TV mode',
                           get_cmd=lambda : self._get('tv_two_channel_mode'), vals=valids.Bool(),
                           set_cmd=lambda x : self._set('tv_two_channel_mode', x), initial_value=False)

        self._set_app(app_name)

        ''' program a chebychev low-pass filter with a given bandwidth and gain '''
        bandwidth=0.1
        gain=1.0
        bandwidths = [0.001, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 
                      0.2, 0.22, 0.24, 0.26, 0.28, 0.3, 0.32, 0.34, 0.36, 0.38, 0.4]
        bandwidth = min(bandwidths, key=lambda x: abs(x - bandwidth))
        # exclude parameters that are not present in the current mode
        self._set('fir_engine', 'library')
        self._set('fir_library_file', r'C:/QTLab/custom_plugins/FPGA/filters/chebLP_ASYM40_FilterLib001.txt')
        self._set('fir_filter', 'lp fs={0:g} 40tap cheb(g=2.5)'.format(bandwidth))
        self._set('fir_gain1', gain)
        self._set('fir_gain2', gain)

        self._ch_states = (True, False)
        self._num_segs = 1
        self._num_reps = 1
        self._trigger_edge = 1

    def _set_fir(self, gain=1.0, bandwidth=0.1):
        ''' program a chebychev low-pass filter with a given bandwidth and gain '''
        # bandwidth=0.1
        # gain=1.0
        bandwidths = [0.001, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 
                      0.2, 0.22, 0.24, 0.26, 0.28, 0.3, 0.32, 0.34, 0.36, 0.38, 0.4]
        bandwidth = min(bandwidths, key=lambda x: abs(x - bandwidth))
        # exclude parameters that are not present in the current mode
        self._set('fir_engine', 'library')
        self._set('fir_library_file', r'C:/QTLab/custom_plugins/FPGA/filters/chebLP_ASYM40_FilterLib001.txt')
        self._set('fir_filter', 'lp fs={0:g} 40tap cheb(g=2.5)'.format(bandwidth))
        self._set('fir_gain1', gain)
        self._set('fir_gain2', gain)

    def _set_app(self, appname):
        result = self._proxy.set_app(self._remote_name, appname)
        if appname == 'TVMODEV02':
            self._call('set_app', 'TVMODEV02')

            self._set('mem_hold', False),
            self._set('ddc_adc1', 'ADC1')
            self._set('ddc_if1', '25MHz') ### Eric changed to 10 MHz
            self._set('ddc_adc2', 'ADC2') 
            self._set('ddc_if2', '25MHz') ### Eric changed to 10 MHz
            # default math: measure complex voltage
            self._set('math_f1', '1(a*b)')
            self._set('math_a1', 'I1 + iQ1')
            self._set('math_b1', '1*')
            self._set('math_f2', '1(a*b)')
            self._set('math_a2', 'I2 + iQ2')
            self._set('math_b2', '1*')
            # boxcar FIR filter (refine with ctx_fpga_fir)
            self._set('fir_engine', 'boxcar')
            self._set('fir_integration', 'none')
            self._set('fir_post_filtering', False)
            # tv mode: 248 samples, 40ns per sample, <~ 10us per trace
            self._set('tv_decimation', 4) 
            self._set('tv_samples', 4096)
            self._set('tv_averages', 1)
            # tv mode: one segment, one channel
            self._set('tv_segments', 1)
            self._set('tv_use_seq_start', False)
        return result
    
    def _get(self, pname, **kwargs):
        """Query value of parameter `pname`. kwargs are ignored."""
        return self._proxy.ins_get(self._remote_name, pname, kwargs)
    
    def _set(self, pname, *args, **kwargs):
        """Set value of parameter `pname` to `value`. kwargs are ignored."""
        return self._proxy.ins_set(self._remote_name, pname, args, kwargs)
    
    def _call(self, pname, *args, **kwargs):
        result =  self._proxy.ins_call(self._remote_name, pname, args, kwargs)
        # return result
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
    def ChannelStates(self):
        return self._ch_states
    @ChannelStates.setter
    def ChannelStates(self, ch_states):
        assert len(ch_states) == 2, "There are 2 channel states that must be specified."
        assert ch_states[0] != False, "This instrument only supports either CH1 or CH1&CH2 modes."

        self._set('tv_two_channel_mode', ch_states[1])
        self._ch_states = ch_states

    @property
    def AvailableChannels(self):
        return 2

    @property
    def SampleRate(self):
        return self._call('get_sample_rate') / self.tv_decimation() #Decimation can't be zero :P
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        return  #Does nothing...

    @property
    def NumSamples(self):
        return self._get('tv_samples')
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self._set('tv_samples', num_samples)

    @property
    def NumSegments(self):
        return self._num_segs
    @NumSegments.setter
    def NumSegments(self, num_segs):
        self._num_segs = num_segs

    @property
    def NumRepetitions(self):
        return self._num_reps
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps):
        self._num_reps = num_reps

    @property
    def TriggerInputEdge(self):
        return self._trigger_edge
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self._trigger_edge = 1  #Always setting to positive edge...
        #self._trigger_edge = pol   #TODO: Check if input trigger polarity can be set on this instrument

    #TODO: WRITE A DDC PROPERTY - look up ddc_if2 and ddc_adc1 as well...
    # @property
    # def DdcIfFrequency(self):
    #     return self._get('ddc_adc1')
    # @DdcIfFrequency.setter
    # def DdcIfFrequency(self, freqHertz):
    #     self._set('ddc_adc1', freqHertz)

    
    # @property
    # def TriggerInputEdge(self):
    #     return 1    #Always positive edge
    # @TriggerInputEdge.setter
    # def TriggerInputEdge(self, pol):
    #     self._trigger_edge = pol

    def _start(self, **kwargs):
        self._set('trigger_src_shot',0) #Sample Trigger
        self._set('trigger_src_ddc',0)  #DDC Trigger (it means something)

        if self.NumSegments > 1:
            #Set SEQ Trigger Mode
            self._set('tv_use_seq_start',True)
            self._set('trigger_src_seq_start', 3)    #Using User Pin 4 for SEQ Trigger
        else:
            self._set('tv_use_seq_start',False)
            self._set('trigger_src_seq_start', 0)

        total_frames = self._cur_reps*self.NumSegments
        self._set('tv_segments', total_frames)
        self._call('stop')
        self._call('mem_clear')

    def _acquire(self):
        #channels, segments, samples
        return self._call('get_data_blocking')

    def _stop(self, final_data, **kwargs):
        cur_processor = kwargs.get('data_processor', None)
        channels, segments, samples = final_data.shape
        
        if channels == 1:
            ch1_data = final_data[0].reshape(self._cur_reps, self.NumSegments, self.NumSamples)
            data_pkt = {
                'parameters' : ['repetition', 'segment', 'sample'],
                'data' : { 'ch1_I' : np.real(ch1_data), 'ch1_Q' : np.imag(ch1_data) },
                'misc' : {'SampleRates' : [self.SampleRate]*2}
            }
        else:
            ch1_data = final_data[0].reshape(self._cur_reps, self.NumSegments, self.NumSamples)
            ch2_data = final_data[1].reshape(self._cur_reps, self.NumSegments, self.NumSamples)
            data_pkt = {
                'parameters' : ['repetition', 'segment', 'sample'],
                'data' : { 'ch1_I' : np.real(ch1_data), 'ch1_Q' : np.imag(ch1_data),
                           'ch2_I' : np.real(ch2_data), 'ch2_Q' : np.imag(ch2_data) },
                'misc' : {'SampleRates' : [self.SampleRate]*4}
            }
        
        if cur_processor is None:
            return data_pkt
        else:
            cur_processor.push_data(data_pkt)
            return None
    
    def get_data(self, **kwargs):
        max_memory = 2**19

        cur_processor = kwargs.get('data_processor', None)
        total_samples = self.NumSamples * self.NumSegments * self.NumRepetitions
        if total_samples > max_memory:
            max_rep = int(max_memory / (self.NumSamples * self.NumSegments))
            assert max_rep > 0, "Too many samples to capture in a single shot."
            
            cur_reps = 0
            # data_pkts = []
            while cur_reps < self.NumRepetitions:
                self._cur_reps = min(max_rep, self.NumRepetitions - cur_reps)
                cur_reps += self._cur_reps
                
                self._start(**kwargs)
                #channels, segments, samples
                final_data = self._acquire()
                self._stop(final_data, **kwargs)
            if cur_processor is None:
                assert False, "NumRepetitions exceeds memory. Multiple capture method has only been implemented for the case where a data_processor is supplied."
                # return data_pkt
            else:
                return cur_processor.get_all_data()
        else:
            self._cur_reps = self.NumRepetitions
            self._start(**kwargs)
            #channels, segments, samples
            final_data = self._acquire()
            data_pkt = self._stop(final_data, **kwargs)
            if cur_processor is None:
                return data_pkt
            else:
                return cur_processor.get_all_data()
