from sqdtoolz.HAL.HALbase import*

class ACQdso(HALbase):
    def __init__(self, hal_name, lab, instr_dso, **kwargs):
        HALbase.__init__(self, hal_name)
        self._instr_id = instr_dso
        self._instr_dso = lab._get_instrument(instr_dso)
        self.data_processor = None

        leInputs = self._instr_dso.get_all_outputs()
        self._dso_chan_list = []
        for ch_index, cur_instr_chan in enumerate(leInputs):
            self._dso_chan_list.append(ACQdsoChannel(*cur_instr_chan, ch_index))
        
        config_dict = kwargs.get('dict_config', None)
        if isinstance(config_dict, dict):
            self._set_current_config(config_dict, lab)
        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        awg_channel_tuples = []
        return cls(config_dict["Name"], lab,
                    config_dict["instrument"],
                    dict_config = config_dict)

    
    @property
    def IsACQhal(self):
        return True

    @property
    def SampleRate(self):
        return self._instr_dso.SampleRate
    @SampleRate.setter
    def SampleRate(self, sample_rate):
        self._instr_dso.SampleRate = sample_rate

    @property
    def NumSamples(self):
        return self._instr_dso.NumSamples
    @NumSamples.setter
    def NumSamples(self, num_points):
        self._instr_dso.NumSamples = num_points

    @property
    def ACQTriggerChannel(self):
        return self._instr_dso.ACQTriggerChannel
    @ACQTriggerChannel.setter
    def ACQTriggerChannel(self, ch_id):
        self._instr_dso.ACQTriggerChannel = ch_id

    @property
    def ACQTriggerSlope(self):
        return self._instr_dso.ACQTriggerSlope
    @ACQTriggerSlope.setter
    def ACQTriggerSlope(self, slope_type):
        assert slope_type in ['POS', 'NEG', 'BOTH'], "ACQTriggerSlope must be given as POS, NEG or BOTH."
        self._instr_dso.ACQTriggerSlope = slope_type

    @property
    def ACQTriggerVoltageLevel(self):
        return self._instr_dso.ACQTriggerVoltageLevel
    @ACQTriggerVoltageLevel.setter
    def ACQTriggerVoltageLevel(self, volt_level):
        self._instr_dso.ACQTriggerVoltageLevel = volt_level
    
    def set_data_processor(self, proc_obj):
        self.data_processor = proc_obj

    def channel(self, index):
        return self._dso_chan_list[index]

    def get_output_channels(self):
        return self._awg_chan_list[:]

    def get_data(self):
        ret_data = self._instr_dso.get_data(data_processor = self.data_processor)
        return ret_data

    def _get_current_config(self):
        if self.data_processor:
            proc_name = self.data_processor.Name
        else:
            proc_name = ''
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            'Processor' : proc_name,
            'Channels' : [x._get_current_config() for x in self._dso_chan_list]
            }
        self.pack_properties_to_dict(['SampleRate', 'NumSamples', 'ACQTriggerChannel', 'ACQTriggerSlope', 'ACQTriggerVoltageLevel'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a AWG with a configuration that is of type ' + dict_config['Type']
        assert self._instr_id == dict_config['instrument'], "Instrument names do not match for this input channel (order changed somehow?)."

        self.NumSamples = dict_config['NumSamples']
        self.SampleRate = dict_config['SampleRate']
        self.ACQTriggerChannel = dict_config['ACQTriggerChannel']
        self.ACQTriggerSlope = dict_config['ACQTriggerSlope']
        self.ACQTriggerVoltageLevel = dict_config['ACQTriggerVoltageLevel']
        if dict_config['Processor'] != '':
            self.data_processor = lab.PROC(dict_config['Processor'])
        
        for ind, cur_ch_output in enumerate(dict_config['Channels']):
            self._dso_chan_list[ind]._set_current_config(cur_ch_output, self._instr_dso)
        

class ACQdsoChannel(LockableProperties):
    def __init__(self, chan_name, cur_instr_chan, ch_index):
        self._channel_name = chan_name
        self._instr_dso_chan = cur_instr_chan

    @property
    def Name(self):
        return self._channel_name

    @property
    def VoltageRange(self):
        return self._instr_dso_chan.VoltageRange
    @VoltageRange.setter
    def VoltageRange(self, volt_range):
        self._instr_dso_chan.VoltageRange = volt_range
    
    @property
    def VoltageOffset(self):
        return self._instr_dso_chan.VoltageOffset
    @VoltageOffset.setter
    def VoltageOffset(self, volt_offset):
        self._instr_dso_chan.VoltageOffset = volt_offset
    
    @property
    def InputCoupling(self):
        return self._instr_dso_chan.InputCoupling
    @InputCoupling.setter
    def InputCoupling(self, coupling):
        self._instr_dso_chan.InputCoupling = coupling

    @property
    def Enabled(self):
        return self._instr_dso_chan.Enabled
    @Enabled.setter
    def Enabled(self, enabled):
        self._instr_dso_chan.Enabled = enabled

    def _get_current_config(self):
        retDict = {
            'Name' : self.Name,
            'Channel' : self._channel_name,
            'VoltageRange' : self.VoltageRange,
            'VoltageOffset' : self.VoltageOffset,
            'InputCoupling' : self.InputCoupling,
            'Enabled' : self.Enabled
            }
        return retDict
    
    def _set_current_config(self, dict_config, instr_dso_obj):
        self._channel_name = dict_config['Name']
        self._instr_dso_chan = instr_dso_obj.get_output(dict_config['Channel'])
        self.VoltageRange = dict_config['VoltageRange']
        self.VoltageOffset = dict_config['VoltageOffset']
        self.InputCoupling = dict_config['InputCoupling']
        self.Enabled = dict_config['Enabled']
