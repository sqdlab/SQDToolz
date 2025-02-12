from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals

class MWS_SGS100A_Channel(InstrumentChannel):
    #TODO: Do an IDN Check to ensure it is the SGS100A instead of the SMB100A - i.e. throw an assertion error...
    def __init__(self, parent:Instrument, name:str) -> None:
        super().__init__(parent, name)
        self._mode = 'Continuous'   #Can be: Continuous, PulseModulated
        
        self.add_parameter(name='power', label='Output Power', unit='dBm',
                           get_cmd='SOUR:POW' + '?',
                           set_cmd='SOUR:POW' + ' {:.2f}',
                           get_parser=float,
                           vals=vals.Numbers(-120, 25))
        self.add_parameter('frequency', label='Output Frequency', unit='Hz',
                            get_cmd='SOUR:FREQ' + '?',
                            set_cmd='SOUR:FREQ' + ' {:.2f}',
                            get_parser=float,
                            vals=vals.Numbers(1e6, 12.75e9))
        #This is the reference phase taken when synchronising with a reference clock...
        self.add_parameter('phase', label='Output Phase', unit='deg',
                            get_cmd='SOUR:PHAS' + '?',
                            set_cmd='SOUR:PHAS' + ' {:.2f}',
                            get_parser=float,
                            vals=vals.Numbers(-360, 360))
        self.add_parameter('output',
                            get_cmd=':OUTP:STAT?',
                            set_cmd=':OUTP:STAT {}',
                            set_parser=int,
                            val_mapping={'ON':  1, 'OFF': 0})
        self.add_parameter('pulsemod_state',
                            get_cmd=':SOUR:PULM:STAT?',
                            set_cmd=':SOUR:PULM:STAT {}',
                            set_parser=int,
                            val_mapping={'ON':  1, 'OFF': 0})
        self.add_parameter('pulsemod_source',
                            get_cmd='SOUR:PULM:SOUR?',
                            set_cmd='SOUR:PULM:SOUR {}',
                            vals=vals.Enum('INT', 'EXT'))

    @property
    def Output(self):
        return self.output() == 'ON'
    @Output.setter
    def Output(self, boolVal):
        if boolVal:
            self.output('ON')
        else:
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
    def PhaseModAmplitude(self):
        return 0
    @PhaseModAmplitude.setter
    def PhaseModAmplitude(self, val):
        pass

    @property
    def FrequencyModAmplitude(self):
        return 0
    @FrequencyModAmplitude.setter
    def FrequencyModAmplitude(self, val):
        pass

    @property
    def AmplitudeModDepth(self):
        return 0
    @AmplitudeModDepth.setter
    def AmplitudeModDepth(self, val):
        pass

    @property
    def TriggerInputEdge(self):
        return 1
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, val):
        #TODO: Figure out whether the gated polarity can be set...
        pass

    @property
    def Mode(self):
        return self._mode
    @Mode.setter
    def Mode(self, new_mode):
        assert new_mode in ['Continuous', 'PulseModulated', 'PhaseModulated', 'FrequencyModulated', 'AmplitudeModulated'], "MW source output mode must either be Continuous, PulseModulated, FrequencyModulated, AmplitudeModulated or PhaseModulated."
        self._mode = new_mode
        if new_mode == 'Continuous':
            self.pulsemod_state('OFF')
        elif new_mode == 'PulseModulated':
            self.pulsemod_state('ON')
            self.pulsemod_source('EXT')
        elif new_mode == 'PhaseModulated':
            assert False, "The SGS100A does not support external phase modulation."
        elif new_mode == 'AmplitudeModulated':
            assert False, "The SGS100A does not support external amplitude modulation."
        elif new_mode == 'FrequencyModulated':
            assert False, "The SGS100A does not support external frequency modulation."
    
    def query_hardware_errors(self):
        return self._parent.query_hardware_errors()

class MWS_SGS100A(VisaInstrument):
    """
    This is the qcodes driver for the Rohde & Schwarz SGS100A signal generator

    Status: beta-version.

    .. todo::

        - Add all parameters that are in the manual
        - Add test suite
        - See if there can be a common driver for RS mw sources from which
          different models inherit

    This driver will most likely work for multiple Rohde & Schwarz sources.
    it would be a good idea to group all similar RS drivers together in one
    module.

    Tested working with

    - RS_SGS100A
    - RS_SMB100A

    This driver does not contain all commands available for the RS_SGS100A but
    only the ones most commonly used.
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        leIdn = self.ask('*IDN?').split(',')
        assert len(leIdn) >= 2 and leIdn[1].lower() == 'sgs100a', f"This MW source \'{name}\' on {address} is NOT a SGS100A. Use the appropriate driver!"

        self.add_parameter('ref_osc_source',
                           label='Reference oscillator source',
                           get_cmd='SOUR:ROSC:SOUR?',
                           set_cmd='SOUR:ROSC:SOUR {}',
                           vals=vals.Enum('INT', 'EXT'))
        # Frequency mw_source outputs when used as a reference
        self.add_parameter('ref_osc_output_freq',
                           label='Reference oscillator output frequency',
                           get_cmd='SOUR:ROSC:OUTP:FREQ?',
                           set_cmd='SOUR:ROSC:OUTP:FREQ {}',
                           vals=vals.Enum('10MHz', '100MHz', '1000MHz'))
        # Frequency of the external reference mw_source uses
        self.add_parameter('ref_osc_external_freq',
                           label='Reference oscillator external frequency',
                           get_cmd='SOUR:ROSC:EXT:FREQ?',
                           set_cmd='SOUR:ROSC:EXT:FREQ {}',
                           vals=vals.Enum('10MHz', '100MHz', '1000MHz'))
        self.add_parameter('trigger_impedance',
                            get_cmd='SOUR:PULM:TRIG:EXT:IMP?',
                            set_cmd='SOUR:PULM:TRIG:EXT:IMP {}',
                            vals=vals.Enum('G50', 'G10K'))
                           
        self.add_parameter('alc',
                           get_cmd='POW:ALC?',
                           set_cmd='POW:ALC {}',
                           vals=vals.Enum('ON', 'OFF', 'AUTO'))

        # Output channels added to both the module for snapshots and internal output sources for use in queries
        self._source_outputs = {}
        for ch_name in ['RFOUT']:
            cur_channel = MWS_SGS100A_Channel(self, ch_name)
            self.add_submodule(ch_name, cur_channel)
            self._source_outputs[ch_name] = cur_channel

    def get_output(self, identifier):
        return self._source_outputs[identifier]

    def get_all_outputs(self):
        return [(x,self._source_outputs[x]) for x in self._source_outputs]

    def query_hardware_errors(self):
        leErrs = self.ask('SYST:SERR?')
        errCode = int(leErrs.split(',')[0])
        if errCode == 0:
            return ""
        elif errCode == -300:
            return "Chk. REF Clock."
        else:
            return leErrs

