from sqdtoolz.HAL.HALbase import*

class ACQsa(HALbase):
    def __init__(self, hal_name, lab, instr_sa):
        #NOTE: the driver is presumed to be a single-pole many-throw switch (i.e. only one circuit route at a time).
        HALbase.__init__(self, hal_name)
        self._instr_id = instr_sa
        self._instr_sa = lab._get_instrument(instr_sa)
        lab._register_HAL(self)
        self._lab = lab
        self.data_processor = None

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def IsACQhal(self):
        return True

    @property
    def FrequencyStart(self):
        return self._instr_sa.FrequencyStart
    @FrequencyStart.setter
    def FrequencyStart(self, val):
        self._instr_sa.FrequencyStart = val
    @property
    def FrequencyEnd(self):
        return self._instr_sa.FrequencyEnd
    @FrequencyEnd.setter
    def FrequencyEnd(self, val):
        self._instr_sa.FrequencyEnd = val
    @property
    def FrequencyCentre(self):
        return self._instr_sa.FrequencyCentre
    @FrequencyCentre.setter
    def FrequencyCentre(self, val):
        self._instr_sa.FrequencyCentre = val
    @property
    def FrequencySpan(self):
        return self._instr_sa.FrequencySpan
    @FrequencySpan.setter
    def FrequencySpan(self, val):
        self._instr_sa.FrequencySpan = val

    @property
    def Bandwidth(self):
        return self._instr_sa.Bandwidth
    @Bandwidth.setter
    def Bandwidth(self, val):
        self._instr_sa.Bandwidth = val
    @property
    def SweepPoints(self):
        return self._instr_sa.SweepPoints
    @SweepPoints.setter
    def SweepPoints(self, val):
        self._instr_sa.SweepPoints = val

    @property
    def AveragesEnable(self):
        return self._instr_sa.AveragesEnable
    @AveragesEnable.setter
    def AveragesEnable(self, val):
        self._instr_sa.AveragesEnable = val
    @property
    def AveragesNum(self):
        return self._instr_sa.AveragesNum
    @AveragesNum.setter
    def AveragesNum(self, val):
        self._instr_sa.AveragesNum = val

    def set_data_processor(self, proc_obj):
        self.data_processor = proc_obj

    def get_data(self):
        return self._instr_sa.get_data(data_processor = self.data_processor)

    def _get_current_config(self):
        if self.data_processor:
            proc_name = self.data_processor.Name
        else:
            proc_name = ''
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            'Processor' : proc_name
            }
        #Not adding in FrequencyCentre and FrequencySpan to avoid strange contradictions...
        self.pack_properties_to_dict(['FrequencyStart', 'FrequencyEnd', 'SweepPoints', 'AveragesNum', 'AveragesEnable', 'Bandwidth'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a VNA with a configuration that is of type ' + dict_config['Type']
        for cur_prop in ['FrequencyStart', 'FrequencyEnd', 'SweepPoints', 'AveragesNum', 'AveragesEnable', 'Bandwidth']:
            setattr(self, cur_prop, dict_config[cur_prop])
        if dict_config['Processor'] != '':
            self.data_processor = lab.PROC(dict_config['Processor'])
