from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
from functools import partial

class MWS_WFSynthHDProV2_Channel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, chan_ind) -> None:
        super().__init__(parent, name)
        self._parent = parent
        self._chan_ind = chan_ind
        self._mode = 'Continuous'   #Can be: Continuous, PulseModulated
        
        self.add_parameter(name='power', label='Output Power', unit='dBm',
                           get_cmd=partial(self._get_cmd, 'W?'),
                           set_cmd=partial(self._set_cmd_trunc_power, 'W'),
                           get_parser=float,
                           vals=vals.Numbers(-60, 20))
        #Note that the instrument gives frequency in MHz...
        self.add_parameter('frequency', label='Output Frequency', unit='Hz',
                            get_cmd=partial(self._get_cmd, 'f?'),
                            set_cmd=partial(self._set_cmd_trunc_freq),
                            get_parser=lambda x: float(x)*1.0e6,
                            set_parser=lambda x: float(x)/1.0e6,
                            vals=vals.Numbers(10e6, 24e9))
        #There is no phase-correction setting on this unit...
        self.add_parameter('phase', label='Output Phase', unit='deg',
                            get_cmd=lambda: 0,
                            set_cmd=lambda x: x,
                            get_parser=float,
                            vals=vals.Numbers(-360, 360))
        self.add_parameter('output',
                            get_cmd=partial(self._get_cmd, 'r?'),
                            set_cmd=partial(self._set_cmd, 'r'),
                            set_parser=int,
                            val_mapping={'ON':  1, 'OFF': 0})

        self.add_parameter('trigger_input',
                           label='Reference oscillator source',
                           get_cmd=partial(self._get_cmd, 'w?'),
                           set_cmd=partial(self._set_cmd, 'w'),
                           val_mapping={
                               'None':0,
                               'FreqSweepFull':1,
                               'FreqSweepSingle':2,
                               'StopAll':3,
                               'ModulationPulse':4,
                               'RemoveInterrupts':5,
                               'ModulationAM':8,
                               'ModulationFM':9
                           })
        #From the documentation:
        #The SynthHD PLL can be powered down for absolute minimum noise on the output connector. This command enables
        #and disables the PLL and VCO to save energy and can take 20mS to boot up.
        self.add_parameter('pll_status',
                           label='Reference oscillator source',
                           get_cmd=partial(self._get_cmd, 'E?'),
                           set_cmd=partial(self._set_cmd, 'E'),
                           val_mapping={
                               'ON':1,
                               'OFF':0
                           })
        
        
        self.add_parameter('REF_Source',
                            get_cmd=partial(self._get_cmd, 'x?'),
                            set_cmd=partial(self._set_cmd, 'x'),
                            set_parser=int,
                            val_mapping={'INT':  1, 'EXT': 0})

    def _get_cmd(self, cmd):
        #Perform channel-select
        self._parent._set_cmd(f'C{self._chan_ind}','')
        #Query command
        return self._parent._get_cmd(f'{cmd}')
    def _set_cmd(self, cmd, val):
        #Perform channel-select
        self._parent._set_cmd(f'C{self._chan_ind}','')
        #Perform command
        self._parent._set_cmd(f'{cmd}{val}','')
    def _set_cmd_trunc_freq(self, val):
        #Perform channel-select
        self._parent._set_cmd(f'C{self._chan_ind}', '')
        #Perform command
        self._parent._set_cmd('f' + ('%013.7f'%val),'')
    def _set_cmd_trunc_power(self, cmd, val):
        #Perform channel-select
        self._parent._set_cmd(f'C{self._chan_ind}','')
        #Perform command
        self._parent._set_cmd(cmd + ('%06.3f'%val),'')

    @property
    def Output(self):
        return self.output() == 'ON'
    @Output.setter
    def Output(self, boolVal):
        if boolVal:
            self.pll_status('ON')
            self.output('ON')
        else:
            self.pll_status('OFF')
            self.output('OFF')
    
    @property
    def Power(self):
        return self.power()
    @Power.setter
    def Power(self, val):
        self.power(val)
        
    @property
    def Frequency(self):
        return self.frequency()
    @Frequency.setter
    def Frequency(self, val):
        self.frequency(val)
        
    @property
    def Phase(self):
        return self.phase()
    @Phase.setter
    def Phase(self, val):
        self.phase(val)

    @property
    def TriggerInputEdge(self):
        return 1
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, val):
        #TODO: Figure out whether the gated polarity can be set...
        pass

    #!!!!!!!!!!!!!!!!!!!!!
    #!!!!!!!!!NOTE!!!!!!!!
    #The modulation is locked to both channels - so it's not a channel-dependent parameter and will do it for both
    #channels. Also, pulse modulation looks awful on this device (i.e. it seems to miss pulses etc...) - so just
    #use continuous mode for now.
    #TODO: Investigate why this is the case later with manufacturer or the manual.
    #!!!!!!!!!!!!!!!!!!!!!
    @property
    def Mode(self):
        return self._mode
    @Mode.setter
    def Mode(self, new_mode):
        assert new_mode == 'Continuous' or new_mode == 'PulseModulated', "MW source output mode must either be Continuous or PulseModulated."
        self._mode = new_mode
        if new_mode == 'Continuous':
            self.trigger_input('None')
        elif new_mode == 'PulseModulated':
            self.trigger_input('ModulationPulse')

class MWS_WFSynthHDProV2(VisaInstrument):
    """
    Driver for the Windfreak SynthHD PRO v2.
    """
    def __init__(self, name, address, **kwargs):
        init_instrument_only = kwargs.pop('init_instrument_only', False)
        if init_instrument_only:
            Instrument.__init__(self, name, **kwargs)
        else:
            super().__init__(name, address, **kwargs)

        # Output channels added to both the module for snapshots and internal output sources for use in queries
        self._source_outputs = {}
        self._chan_names = ['RFoutA','RFoutB']
        for ch_ind, ch_name in enumerate(self._chan_names):
            cur_channel = MWS_WFSynthHDProV2_Channel(self, ch_name, ch_ind)
            self.add_submodule(ch_name, cur_channel)
            self._source_outputs[ch_name] = cur_channel

        self.add_parameter('EXT_REF_frequency', label='External REF Frequency', unit='Hz',
                            get_cmd=partial(self._get_cmd, '*?'),
                            set_cmd=self._set_cmd_ref_freq,
                            get_parser=lambda x: float(x)*1.0e6,
                            set_parser=lambda x: float(x)/1.0e6,
                            vals=vals.Numbers(10e6, 100e6))
        self.EXT_REF_frequency()

    def get_output(self, identifier):
        return self._source_outputs[identifier]

    def get_all_outputs(self):
        return [(x,self._source_outputs[x]) for x in self._source_outputs]

    def get_idn(self):
        #Otherwise, it will send *IDN and cahnge the sample clock!
        return {'vendor': 'Windfreak', 'model': 'HDProV2', 'serial': None, 'firmware': None}

    def _set_cmd_ref_freq(self, val):
        self._set_cmd('*' + ('%07.3f'%val), '')

    #NEED THESE BECAUSE QCODES INSERTS \n etc...
    def _get_cmd(self, cmd):
        return self.ask(f'{cmd}')
    def _set_cmd(self, cmd, val):
        self.write(f'{cmd}{val}')
