from sqdtoolz.HAL.HALbase import*

class ACQvna(HALbase):
    def __init__(self, hal_name, lab, instr_vna):
        #NOTE: the driver is presumed to be a single-pole many-throw switch (i.e. only one circuit route at a time).
        HALbase.__init__(self, hal_name)
        if lab._register_HAL(self):
            self._instr_id = instr_vna
            self._instr_vna = lab._get_instrument(instr_vna)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def SweepMode(self):
        return self._instr_vna.SweepMode
    @SweepMode.setter
    def SweepMode(self, val):
        assert val in self._instr_vna.SupportedSweepModes, f"The VNA does not support {val} mode"
        self._instr_vna.SweepMode = val
    @property
    def FrequencyStart(self):
        return self._instr_vna.FrequencyStart
    @FrequencyStart.setter
    def FrequencyStart(self, val):
        self._instr_vna.FrequencyStart = val
    @property
    def FrequencyEnd(self):
        return self._instr_vna.FrequencyEnd
    @FrequencyEnd.setter
    def FrequencyEnd(self, val):
        self._instr_vna.FrequencyEnd = val
    @property
    def FrequencyCentre(self):
        return self._instr_vna.FrequencyCentre
    @FrequencyCentre.setter
    def FrequencyCentre(self, val):
        self._instr_vna.FrequencyCentre = val
    @property
    def FrequencySpan(self):
        return self._instr_vna.FrequencySpan
    @FrequencySpan.setter
    def FrequencySpan(self, val):
        self._instr_vna.FrequencySpan = val
    @property
    def Power(self):
        return self._instr_vna.Power
    @Power.setter
    def Power(self, val):
        self._instr_vna.Power = val
    @property
    def SweepPoints(self):
        return self._instr_vna.SweepPoints
    @SweepPoints.setter
    def SweepPoints(self, val):
        self._instr_vna.SweepPoints = val
    @property
    def AveragesNum(self):
        return self._instr_vna.AveragesNum
    @AveragesNum.setter
    def AveragesNum(self, val):
        self._instr_vna.AveragesNum = val
    @property
    def AveragesEnable(self):
        return self._instr_vna.AveragesEnable
    @AveragesEnable.setter
    def AveragesEnable(self, val):
        self._instr_vna.AveragesEnable = val
    @property
    def Bandwidth(self):
        return self._instr_vna.Bandwidth
    @Bandwidth.setter
    def Bandwidth(self, val):
        self._instr_vna.Bandwidth = val
    @property
    def NumRepetitions(self):
        return self._instr_vna.NumRepetitions
    @NumRepetitions.setter
    def NumRepetitions(self, val):
        self._instr_vna.NumRepetitions = val
    @property
    def FrequencySingle(self):
        return self._instr_vna.FrequencySingle
    @FrequencySingle.setter
    def FrequencySingle(self, val):
        self._instr_vna.FrequencySingle = val
    @property
    def PowerStart(self):
        return self._instr_vna.PowerStart
    @PowerStart.setter
    def PowerStart(self, val):
        self._instr_vna.PowerStart = val
    @property
    def PowerEnd(self):
        return self._instr_vna.PowerEnd
    @PowerEnd.setter
    def PowerEnd(self, val):
        self._instr_vna.PowerEnd = val

    def set_measurement_parameters(self, ports_meas_src_tuples):
        self._instr_vna.setup_measurements(ports_meas_src_tuples)

    def setup_segmented_sweep(self, segment_freqs):
        '''
        Sets up segmented sweeping on the frequency axis if supported by the VNA. The idea is that one can specify frequency segments upon
        which the VNA sweeps said frequencies to return the measured s-parameters.

        Inputs:
            - segment_freqs - Frequency intervals given as a list of tuples (start_frequency, end_frequency, num_points) in which the boundaries
                              are inclusive.
        '''
        assert 'Segmented' in self._instr_vna.SupportedSweepModes
        self._instr_vna.setup_segmented(segment_freqs)

    def get_data(self):
        return self._instr_vna.get_data()

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            }
        #Not adding in FrequencyCentre and FrequencySpan to avoid strange contradictions...
        self.pack_properties_to_dict(['SweepMode', 'FrequencyStart', 'FrequencyEnd', 'Power', 'SweepPoints', 'AveragesNum', 'AveragesEnable',
                                      'Bandwidth', 'NumRepetitions', 'FrequencySingle', 'PowerStart', 'PowerEnd'], ret_dict)
        ret_dict['FrequencySegments'] = self._instr_vna.get_frequency_segments()
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a VNA with a configuration that is of type ' + dict_config['Type']
        self.Position = dict_config['Position']
        for cur_prop in ['SweepMode', 'FrequencyStart', 'FrequencyEnd', 'Power', 'SweepPoints', 'AveragesNum', 'AveragesEnable',
                         'Bandwidth', 'NumRepetitions', 'FrequencySingle', 'PowerStart', 'PowerEnd']:
            setattr(self, cur_prop, dict_config[cur_prop])
        cur_mode = dict_config['SweepMode']     #Current mode may not have necessarily have set as 'Segmented' mode requires the calling of setup_segmented_sweep to set the segments first...
        self.setup_segmented_sweep(dict_config['FrequencySegments'])
        self.SweepMode = cur_mode
