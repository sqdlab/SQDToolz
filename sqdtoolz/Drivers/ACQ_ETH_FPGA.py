import numpy as np
from qcodes import Instrument, InstrumentChannel, VisaInstrument
import qcodes.utils.validators as valids

from sqdtoolz.HAL.Processors.ProcessorFPGA import ProcessorFPGA
from sqdtoolz.HAL.Processors.FPGA.FPGA_DDC import FPGA_DDC
from sqdtoolz.HAL.Processors.FPGA.FPGA_FIR import FPGA_FIR
from sqdtoolz.HAL.Processors.FPGA.FPGA_Decimation import FPGA_Decimation
from sqdtoolz.HAL.Processors.FPGA.FPGA_Mean import FPGA_Mean
from sqdtoolz.HAL.Processors.FPGA.FPGA_Integrate import FPGA_Integrate

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

        self._set_default(app_name)

        self._ch_states = (True, False)
        self._num_segs = 1
        self._num_reps = 1
        self._trigger_edge = 1
        self._num_samples = 1
        self._last_dsp_state = None

    def _set_default(self,  app_name = 'TVMODEV02'):
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
        return 100e6
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        assert frequency_hertz == 100e6, "ETH FPGA Card only supports 100MSPS sample rate."

    @property
    def NumSamples(self):
        return self._num_samples
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self._num_samples = num_samples

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
        cap_samples = kwargs.get('cap_samples')
        channels, segments, samples = final_data.shape
        
        leSampleRate = self._call('get_sample_rate') / self.tv_decimation()

        if channels == 1:
            ch1_data = final_data[0].reshape(self._cur_reps, self.NumSegments, cap_samples)
            data_pkt = {
                'parameters' : ['repetition', 'segment', 'sample'],
                'data' : { 'ch1_I' : np.real(ch1_data), 'ch1_Q' : np.imag(ch1_data) },
                'misc' : {'SampleRates' : [leSampleRate]*2}
            }
        else:
            ch1_data = final_data[0].reshape(self._cur_reps, self.NumSegments, cap_samples)
            ch2_data = final_data[1].reshape(self._cur_reps, self.NumSegments, cap_samples)
            data_pkt = {
                'parameters' : ['repetition', 'segment', 'sample'],
                'data' : { 'ch1_I' : np.real(ch1_data), 'ch1_Q' : np.imag(ch1_data),
                           'ch2_I' : np.real(ch2_data), 'ch2_Q' : np.imag(ch2_data) },
                'misc' : {'SampleRates' : [leSampleRate]*4}
            }
        
        if cur_processor is None or isinstance(cur_processor, ProcessorFPGA):
            return data_pkt
        else:
            cur_processor.push_data(data_pkt)
            return None
    
    def get_data(self, **kwargs):
        max_memory = 2**19

        cur_processor = kwargs.get('data_processor', None)

        hw_avg = False
        hw_int = False
        if isinstance(cur_processor, ProcessorFPGA) and not cur_processor.compare_pipeline_state(self._last_dsp_state):
            ddc_done = False
            fir_done = False
            deci_done = False
            avg_done = False
            int_done = False
            for m, cur_node in enumerate(cur_processor.pipeline):
                if isinstance(cur_node, FPGA_DDC):
                    assert not ddc_done, "Cannot run multiple DDC stages on the ETH FPGA card."
                    assert not fir_done, "Cannot run DDC after FIR stage on the ETH FPGA card."
                    assert not deci_done, "Cannot run DDC after Decimation stage on the ETH FPGA card."
                    assert not avg_done, "Cannot run DDC after Averaging stage on the ETH FPGA card."
                    assert not int_done, "Cannot run DDC after Integration stage on the ETH FPGA card."
                    ddc_specs = cur_node.get_params(sample_rate = [100e6]*2, only_params=True)
                    assert len(ddc_specs) > 0, "Cannot run DDC without any frequencies"
                    assert len(ddc_specs[0]) <= 1, "ETH FPGA can only demodulate one tone per channel."
                    if len(ddc_specs[0]) == 1:
                        assert ddc_specs[0][0] == 25e6 or ddc_specs[0][0] == 10e6, "ETH FPGA can only demodulate 10MHz or 25MHz tones."
                        #Program 1st channel DDC
                        self._set('ddc_adc1', 'ADC1')
                        self._set('ddc_if1', f'{int(ddc_specs[0][0]/1e6)}MHz')
                    if len(ddc_specs) == 2:
                        assert len(ddc_specs[1]) == 1, "ETH FPGA can only demodulate one tone per channel."
                        assert ddc_specs[1][0] == 25e6 or ddc_specs[1][0] == 10e6, "ETH FPGA can only demodulate 10MHz or 25MHz tones."
                        self._set('ddc_adc2', 'ADC2')
                        self._set('ddc_if2', f'{int(ddc_specs[1][0]/1e6)}MHz')
                    ddc_done = True
                elif isinstance(cur_node, FPGA_FIR):
                    assert not fir_done, "Cannot run multiple FIR stages on the ETH FPGA card."
                    assert not deci_done, "Cannot run FIR after Decimation stage on the ETH FPGA card."
                    assert not avg_done, "Cannot run FIR after Averaging stage on the ETH FPGA card."
                    assert not int_done, "Cannot run FIR after Integration stage on the ETH FPGA card."
                    fir_specs = cur_node.get_params(sample_rate = [100e6]*2)
                    assert len(fir_specs) > 0, "FIR list invalid"
                    assert len(fir_specs[0]) <= 1, "ETH FPGA can only filter one tone per channel."
                    if len(fir_specs[0]) == 1:
                        num_taps = fir_specs[0][0].size
                        assert num_taps == 7 or num_taps == 29 or num_taps == 40, "FIR filter taps must be either 7, 29 or 4"
                        self._call('set_fir_coeffs', fir_specs[0][0].tolist())
                    if len(fir_specs) == 2:
                        assert len(fir_specs[1]) == 1, "ETH FPGA can only filter one tone per channel."
                        num_taps2 = fir_specs[0][1].size
                        assert num_taps2 == 7 or num_taps2 == 29 or num_taps2 == 40, "FIR filter taps must be either 7, 29 or 4"
                        if len(fir_specs[0]) == 1:
                            assert num_taps == num_taps2, "The ETH FPGA must use the same FIR filter on both channels."
                            assert np.sum(np.abs(fir_specs[0][0] - fir_specs[0][1])) < 1e-9, "The ETH FPGA must use the same FIR filter coefficients on both channels."
                        else:
                            self._call('set_fir_coeffs', fir_specs[0][1].tolist())
                    fir_done = True
                elif isinstance(cur_node, FPGA_Decimation):
                    assert not deci_done, "Cannot run Decimation FIR stages on the ETH FPGA card."
                    assert not avg_done, "Cannot run Decimation after Averaging stage on the ETH FPGA card."
                    assert not int_done, "Cannot run Decimation after Integration stage on the ETH FPGA card."
                    param, fac = cur_node.get_params()
                    assert param == 'sample', "The ETH FPGA only supports decimation samples."
                    assert fac <= 128 and fac >= 1, "The ETH FPGA only supports decimation of up to 128 points."
                    self._set('tv_decimation', fac)
                    deci_done = True
                elif isinstance(cur_node, FPGA_Mean):
                    assert not avg_done, "Cannot run multiple averaging stages on the ETH FPGA card."
                    param = cur_node.get_params()
                    assert param == 'repetition', "Currently the ETH FPGA card only supports averaging across repetitions."
                    self._set('tv_averages', self.NumRepetitions)
                    hw_avg = True
                    avg_done = True
                elif isinstance(cur_node, FPGA_Integrate):
                    assert not int_done, "Cannot run multiple integration stages on the ETH FPGA card."
                    param = cur_node.get_params()
                    assert param == 'sample', "Currently the ETH FPGA card only supports integration across samples."
                    hw_int = True
                    int_done = True

            if not ddc_done:
                self._set('ddc_adc1', 'ADC1')
                self._set('ddc_if1', 'DC')
                self._set('ddc_adc2', 'ADC2')
                self._set('ddc_if2', 'DC')
            if not fir_specs:
                self._call('set_fir_coeffs', [])
            if not deci_done:
                self._set('tv_decimation', 1)
            if not avg_done:
                self._set('tv_averages',1)
            self._last_dsp_state = cur_processor.get_pipeline_state()
            time.sleep(1)

        #The ETH FPGA Card expects the tv_samples to be the number AFTER decimation.
        actual_samples = self.NumSamples
        deci_fac = self._get('tv_decimation')
        cap_samples = int(self.NumSamples / deci_fac)
        self._set('tv_samples', cap_samples)
        kwargs['cap_samples'] = cap_samples
        #
        if hw_avg:
            actual_reps = 1
        else:
            actual_reps = self.NumRepetitions

        total_samples_captured = cap_samples * self.NumSegments * actual_reps
        if total_samples_captured > max_memory:
            assert isinstance(cur_processor, ProcessorFPGA), "Exceeded ETH FPGA memory - check the FPGA processing and ACQ capture parameters."
            max_rep = int(max_memory / (cap_samples * self.NumSegments))
            assert max_rep > 0, "Too many samples to capture in a single shot."
            
            cur_reps = 0
            # data_pkts = []
            while cur_reps < actual_reps:
                self._cur_reps = min(max_rep, actual_reps - cur_reps)
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
            self._cur_reps = actual_reps
            self._start(**kwargs)
            #channels, segments, samples
            final_data = self._acquire()
            data_pkt = self._stop(final_data, **kwargs)
            if cur_processor is None or isinstance(cur_processor, ProcessorFPGA):
                #Contract out the repetition index if hardware averaging...
                if hw_avg:
                    data_pkt['parameters'].pop(0)
                    for cur_ch in data_pkt['data']:
                        data_pkt['data'][cur_ch] = data_pkt['data'][cur_ch][0]
                #TODO: SUPPORT HARDWARE INTEGRATION. Apparently it is present. c.f. mod_fir in the QT Lab stuff.
                if hw_int:
                    data_pkt['parameters'].pop(-1)
                    for cur_ch in data_pkt['data']:
                        data_pkt['data'][cur_ch] = np.sum(data_pkt['data'][cur_ch], axis=-1)
                return data_pkt
            else:
                return cur_processor.get_all_data()
