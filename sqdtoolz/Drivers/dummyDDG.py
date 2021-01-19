from numpy import pi
from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals

class DummyDDGchannel(InstrumentChannel):
    '''
    DG645 per-output settings
    '''
    def __init__(self, parent:Instrument, name:str, channel:int) -> None:
        super().__init__(parent, name)
        self.channel = channel

        self.add_parameter('connection', label='Connected device',
                           docstring='What is connected to this output?', 
                           get_cmd=lambda: getattr(self, '_connection', ''),
                           set_cmd=lambda v: setattr(self, '_connection', v),
                           set_parser=str)
        self.add_parameter('amplitude', label='Amplitude', unit='V', 
                           get_cmd='LAMP?{}'.format(channel), 
                           set_cmd='LAMP {},{}'.format(channel, '{:f}'), 
                           get_parser=float, vals=vals.Numbers(0.5, 5.))
        self.add_parameter('offset', label='Offset', unit='V', 
                           get_cmd='LOFF?{}'.format(channel),
                           set_cmd='LOFF {},{}'.format(channel, '{:f}'),
                           get_parser=float, vals=vals.Numbers(-2., 2.))
        self.add_parameter('TrigPolarity', label='Pulse Polarity', 
                           docstring='Polarity of the output. Use with care.',
                           get_cmd='LPOL?{}'.format(channel),
                           set_cmd='LPOL {},{}'.format(channel, '{:d}'),
                           val_mapping={'NEG': 0, 'POS': 1})
        self.add_parameter(
            'prescale_factor', label='Prescale Factor', 
            docstring='Channel output is enabled on every nth trigger. '
                        'Requires advanced triggering to be enabled.',
            get_cmd='PRES?{}'.format(channel), 
            set_cmd='PRES {},{}'.format(channel, '{:d}'),
            get_parser=int, vals=vals.Numbers(0, (1<<16)-1))
        if channel:
            self.add_parameter(
                'prescale_phase', label='Prescale Phase', 
                docstring='Channel output is delayed by m triggers. '
                          'm must be smaller than the prescale_factor. '
                          'Requires advanced triggering to be enabled.',
                get_cmd='PHAS?{}'.format(channel), 
                set_cmd='PHAS {},{}'.format(channel, '{:d}'),
                get_parser=int, vals=vals.Numbers(0, (1<<16)-1))
            self.add_parameter(
                'TrigPulseLength', label='Trigger Pulse Duration', unit='s',
                get_cmd='DLAY?{}'.format(2*channel+1),
                set_cmd='DLAY {},{},{}'.format(2*channel+1, 2*channel, '{:g}'),
                get_parser=self._parse_duration, vals=vals.Numbers(0., 2000.))
            self.add_parameter(
                'TrigPulseDelay', label='Delay', unit='s',
                docstring='Reference times of pulse starting times '
                            'other than T0 are unsupported.', 
                get_cmd='DLAY?{}'.format(2*channel),
                set_cmd='DLAY {},0,{}'.format(2*channel, '{:g}'),
                get_parser=self._parse_delay, vals=vals.Numbers(0., 2000.))
        else:
            #This is for the T0 output
            self.add_parameter(
                'duration', label='Duration', unit='s',
                get_cmd='DLAY?{}'.format(2*channel+1), 
                get_parser=self._parse_duration)

    def _parse_delay(self, raw):
        ref, delay = raw.split(',')
        if int(ref) != 0:
            raise ValueError('Reference times other than T0 are unsupported.')
        return float(delay)

    def _parse_duration(self, raw):
        ref, delay = raw.split(',')
        if int(ref) == 2*self.channel:
            pass
        elif int(ref) == 0:
            delay -= self.delay.get()
        else:
            raise ValueError('Reference times other than T0 or the starting '
                             'times of the channel are unsupported.')
        return float(delay)

    @property
    def TrigEnable(self):
        return True     #Not implementing any output enable/disable...

    


  
class DummyDDG(VisaInstrument):
    '''
    qcodes driver for the Stanford Research Systems DG645 digital delay generator
    '''
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        self.add_parameter('error', label='Error Code',
                           get_cmd='LERR?', get_parser=int)
        self.add_parameter('advanced_trigger', label='Advanced Trigger Mode', 
                           get_cmd='ADVT?', get_parser=lambda v: bool(int(v)),
                           set_cmd='ADVT {:d}', vals=vals.Bool())
        self.add_parameter(
            'trigger_source', label='Trigger Source', 
            get_cmd='TSRC?', get_parser=int, 
            set_cmd='TSRC {:d}',  
            val_mapping={'Internal':0,
                         'External rising edge':1,
                         'External falling edge':2,
                         'Single shot external rising edge':3,
                         'Single shot external falling edge':4,
                         'Single shot':5,
                         'Line':6})
        self.add_parameter('trigger_level', label='Trigger Level', unit='V',
                           get_cmd='TLVL?', get_parser=float,
                           set_cmd='TLVL {:f}', vals=vals.Numbers(-3.5, 3.5))
        self.add_parameter(
            name='trigger_holdoff', label='Trigger Holdoff', unit='s', 
            docstring='Minimum time between triggers. Advanced triggering must '
                       'be enabled for this parameter to have an effect.',
            get_cmd='HOLD?', get_parser=float,
            set_cmd='HOLD {:f}')
        self.add_parameter(
            'trigger_inhibit', label='Trigger Inhibit', 
            docstring='Outputs inhibited when the external inhibit input is high.', 
            get_cmd='INHB?', get_parser=int,
            set_cmd='INHB {}', 
            val_mapping={'off':0, 
                         'triggers':1, 
                         'AB':2, 
                         'AB, CD':3, 
                         'AB, CD, EF':4, 
                         'AB, CD, EF, GH':5})
        self.add_parameter(
            'trigger_prescale_factor', label='Trigger Prescale Factor', 
            docstring='Channel output is enabled on every nth trigger. '
                      'Requires advanced triggering to be enabled.', 
            get_cmd='PRES?0', get_parser=int, 
            set_cmd='PRES 0,{:d}', vals=vals.Numbers(1, (1<<30)-1)
        )
        # Burst mode parameters
        self.add_parameter('burst_mode', label='Burst Mode', 
                           get_cmd='BURM?', get_parser=lambda v: bool(int(v)), 
                           set_cmd='BURM {}', vals=vals.Bool())
        self.add_parameter('burst_delay', label='Burst Delay', unit='s',
                           get_cmd='BURD?', get_parser=float,
                           set_cmd='BURD {:.12f}', vals=vals.Numbers(0, 2000))
        self.add_parameter('burst_count', label='Burst Count', 
                           get_cmd='BURC?', get_parser=int,
                           set_cmd='BURC {:d}', vals=vals.Numbers(1, 4294967295))
        self.add_parameter('burst_period', label='Burst Period', 
                           get_cmd='BURP?', get_parser=float,
                           set_cmd='BURP {:.8f}', vals=vals.Numbers(1e-7, 42.9))
        # Output channels
        for ch_id, ch_name in [(0, 'T0'), (1, 'AB'), (2, 'CD'), (3, 'EF'), (4, 'GH')]:
            self.add_submodule(ch_name, DummyDDGchannel(self, ch_name, ch_id))
        # Show IDN
        self.connect_message()
