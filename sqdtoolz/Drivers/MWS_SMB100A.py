from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals

class MWS_SMB100A_Channel(InstrumentChannel):
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
                            vals=vals.Numbers(1e6, 20e9))
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
        #
        self.add_parameter('phasemod_state',
                            get_cmd=':SOUR:PM:STAT?',
                            set_cmd=':SOUR:PM:STAT {}',
                            set_parser=int,
                            val_mapping={'ON':  1, 'OFF': 0})
        self.add_parameter('phasemod_mode',
                            get_cmd='SOUR:PM:MODE?',
                            set_cmd='SOUR:PM:MODE {}',
                            vals=vals.Enum('HDEViation', 'NORMal', 'LNOise'),
                            initial_value='NORMal')
        self.add_parameter('phasemod_source',
                            get_cmd='SOUR:PM:SOUR?',
                            set_cmd='SOUR:PM:SOUR {}',
                            vals=vals.Enum('INT', 'EXT'))
        self.add_parameter('phasemod_amplitude',
                            get_cmd='SOUR:PM:EXTernal:DEViation?',
                            set_cmd='SOUR:PM:EXTernal:DEViation {}',
                            get_parser=float,
                            vals=vals.Numbers(0, 20),
                            initial_value=5)
        self.add_parameter('phasemod_ext_coupling',
                            get_cmd='SOUR:PM:EXTernal:COUPling?',
                            set_cmd='SOUR:PM:EXTernal:COUPling {}',
                            vals=vals.Enum('AC', 'DC'),
                            initial_value='AC')
        #
        self.add_parameter('freqmod_state',
                            get_cmd=':SOUR:FM:STAT?',
                            set_cmd=':SOUR:FM:STAT {}',
                            set_parser=int,
                            val_mapping={'ON':  1, 'OFF': 0})
        self.add_parameter('freqmod_mode',
                            get_cmd='SOUR:FM:MODE?',
                            set_cmd='SOUR:FM:MODE {}',
                            vals=vals.Enum('HDEViation', 'NORMal', 'LNOise'),
                            initial_value='NORMal')
        self.add_parameter('freqmod_source',
                            get_cmd='SOUR:FM:SOUR?',
                            set_cmd='SOUR:FM:SOUR {}',
                            vals=vals.Enum('INT', 'EXT'))
        self.add_parameter('freqmod_amplitude',
                            get_cmd='SOUR:FM:EXTernal:DEViation?',
                            set_cmd='SOUR:FM:EXTernal:DEViation {}',
                            get_parser=float,
                            vals=vals.Numbers(0, 128e6),    #TODO: This value is dependent on the carrier frequency! Make function check this against datasheet...
                            initial_value=1e6)
        self.add_parameter('freqmod_ext_coupling',
                            get_cmd='SOUR:FM:EXTernal:COUPling?',
                            set_cmd='SOUR:FM:EXTernal:COUPling {}',
                            vals=vals.Enum('AC', 'DC'),
                            initial_value='AC')
        #
        self.add_parameter('amplmod_state',
                            get_cmd=':SOUR:AM:STAT?',
                            set_cmd=':SOUR:AM:STAT {}',
                            set_parser=int,
                            val_mapping={'ON':  1, 'OFF': 0})
        self.add_parameter('amplmod_source',
                            get_cmd='SOUR:AM:SOUR?',
                            set_cmd='SOUR:AM:SOUR {}',
                            vals=vals.Enum('INT', 'EXT'))
        self.add_parameter('amplmod_depth',
                            get_cmd='SOUR:AM:DEPTh:LINear?',
                            set_cmd='SOUR:AM:DEPTh:LINear {}',
                            get_parser=float,
                            vals=vals.Numbers(0, 100),
                            initial_value=50)
        self.add_parameter('amplmod_ext_coupling',
                            get_cmd='SOUR:AM:EXTernal:COUPling?',
                            set_cmd='SOUR:AM:EXTernal:COUPling {}',
                            vals=vals.Enum('AC', 'DC'),
                            initial_value='AC')

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
        return self.phasemod_amplitude()
    @PhaseModAmplitude.setter
    def PhaseModAmplitude(self, val):
        self.phasemod_amplitude(val)    

    @property
    def FrequencyModAmplitude(self):
        return self.freqmod_amplitude()
    @FrequencyModAmplitude.setter
    def FrequencyModAmplitude(self, val):
        self.freqmod_amplitude(val)

    @property
    def AmplitudeModDepth(self):
        return self.amplmod_depth()
    @AmplitudeModDepth.setter
    def AmplitudeModDepth(self, val):
        self.amplmod_depth(val)    

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
            self.amplmod_state('OFF')
            self.freqmod_state('OFF')
            self.phasemod_state('OFF')
        elif new_mode == 'PulseModulated':
            self.pulsemod_state('ON')
            self.amplmod_state('OFF')
            self.freqmod_state('OFF')
            self.phasemod_state('OFF')
            self.pulsemod_source('EXT')
        elif new_mode == 'PhaseModulated':
            self.pulsemod_state('OFF')
            self.amplmod_state('OFF')
            self.freqmod_state('OFF')
            self.phasemod_state('ON')
            self.phasemod_source('EXT')
        elif new_mode == 'FrequencyModulated':
            self.pulsemod_state('OFF')
            self.amplmod_state('OFF')
            self.freqmod_state('ON')
            self.phasemod_state('OFF')
            self.freqmod_source('EXT')
        elif new_mode == 'AmplitudeModulated':
            self.pulsemod_state('OFF')
            self.amplmod_state('ON')
            self.freqmod_state('OFF')
            self.phasemod_state('OFF')
            self.amplmod_source('EXT')

class MWS_SMB100A(VisaInstrument):
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
        assert len(leIdn) >= 2 and leIdn[1].lower() == 'smb100a', f"This MW source \'{name}\' on {address} is NOT a SMB100A. Use the appropriate driver!"

        self.add_parameter('ref_osc_source',
                           label='Reference oscillator source',
                           get_cmd='SOUR:ROSC:SOUR?',
                           set_cmd='SOUR:ROSC:SOUR {}',
                           vals=vals.Enum('INT', 'EXT'))
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
            cur_channel = MWS_SMB100A_Channel(self, ch_name)
            self.add_submodule(ch_name, cur_channel)
            self._source_outputs[ch_name] = cur_channel

    def get_output(self, identifier):
        return self._source_outputs[identifier]

    def get_all_outputs(self):
        return [(x,self._source_outputs[x]) for x in self._source_outputs]

