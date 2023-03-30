from sqdtoolz.HAL.HALbase import*

class GENsmu(HALbase):
    def __init__(self, hal_name, lab, instr_gen_smu):
        #Note that this must be a specific channel if using a multi-channel SMU!
        HALbase.__init__(self, hal_name)
        self._instr_smu = lab._get_instrument(instr_gen_smu)
        self._instr_id = instr_gen_smu
        lab._register_HAL(self)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict["instrument"])

    @property
    def Output(self):
        return self._instr_smu.Output
    @Output.setter
    def Output(self, val):
        assert isinstance(val, bool), "Output must be either a boolean True or False."
        self._instr_smu.Output = val

    @property
    def Value(self):
        #This property is useful when using rec_params - i.e. don't have to specify this HAL as a tuple!
        if self.Mode == 'SrcI_MeasV':
            return self.Voltage
        else:
            return self.Current
        
    @property
    def Voltage(self):
        return self._instr_smu.Voltage
    @Voltage.setter
    def Voltage(self, val):
        self._instr_smu.Voltage = val
        
    @property
    def Current(self):
        return self._instr_smu.Current
    @Current.setter
    def Current(self, val):
        self._instr_smu.Current = val
        
    @property
    def SenseVoltage(self):
        return self._instr_smu.SenseVoltage
        
    @property
    def SenseCurrent(self):
        return self._instr_smu.SenseCurrent
    
    @property
    def ComplianceCurrent(self):
        return self._instr_smu.ComplianceCurrent
    @ComplianceCurrent.setter
    def ComplianceCurrent(self, val):
        self._instr_smu.ComplianceCurrent = val
    
    @property
    def ComplianceVoltage(self):
        return self._instr_smu.ComplianceVoltage
    @ComplianceVoltage.setter
    def ComplianceVoltage(self, val):
        self._instr_smu.ComplianceVoltage = val
        
    @property
    def Mode(self):
        return self._instr_smu.Mode
    @Mode.setter
    def Mode(self, mode):
        assert mode == 'SrcI_MeasV' or mode == 'SrcV_MeasI', 'Mode must be \'SrcI_MeasV\' or \'SrcV_MeasI\''
        self._instr_smu.Mode = mode

    @property
    def RampRateVoltage(self):
        return self._instr_smu.RampRateVoltage
    @RampRateVoltage.setter
    def RampRateVoltage(self, val):
        self._instr_smu.RampRateVoltage = val

    @property
    def RampRateCurrent(self):
        return self._instr_smu.RampRateCurrent
    @RampRateCurrent.setter
    def RampRateCurrent(self, val):
        self._instr_smu.RampRateCurrent = val

    @property
    def ProbeType(self):
        return self._instr_smu.ProbeType
    @ProbeType.setter
    def ProbeType(self, val):
        self._instr_smu.ProbeType = val


    @property
    def SupportsSweeping(self):
        return self._instr_smu.SupportsSweeping

    @property
    def SweepSampleTime(self):
        return self._instr_smu.SweepSampleTime
    @SweepSampleTime.setter
    def SweepSampleTime(self, smpl_time_seconds):
        self._instr_smu.SweepSampleTime = smpl_time_seconds

    @property
    def SweepSamplePoints(self):
        return self._instr_smu.SweepSamplePoints
    @SweepSamplePoints.setter
    def SweepSamplePoints(self, smpl_pts):
        self._instr_smu.SweepSamplePoints = smpl_pts

    @property
    def SweepStartValue(self):
        return self._instr_smu.SweepStartValue
    @SweepStartValue.setter
    def SweepStartValue(self, val):
        self._instr_smu.SweepStartValue = val

    @property
    def SweepEndValue(self):
        return self._instr_smu.SweepEndValue
    @SweepEndValue.setter
    def SweepEndValue(self, val):
        self._instr_smu.SweepEndValue = val

    def get_data(self):
        return self._instr_smu.get_data()

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            #Ignoring ManualActivation
            'SupportsSweeping' : self.SupportsSweeping
            }
        self.pack_properties_to_dict(['Mode', 'Voltage', 'Current', 'RampRateVoltage', 'RampRateCurrent', 'ProbeType', 'Output', 'SenseVoltage', 'SenseCurrent', 'ComplianceVoltage', 'ComplianceCurrent'], ret_dict)
        if self.SupportsSweeping:
            self.pack_properties_to_dict(['SweepSampleTime', 'SweepSamplePoints', 'SweepStartValue', 'SweepEndValue'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a Voltage-Source with a configuration that is of type ' + dict_config['Type']
        self.Mode = dict_config['Mode']
        #Don't store SenseVoltage and SenseCurrent as they are only readonly properties!s
        #Only set the Source Property - shouldn't be allowed to set the measure-property!
        if self.Mode == 'SrcI_MeasV':
            self.Current = dict_config['Current']
        else:
            self.Voltage = dict_config['Voltage']
        self.RampRateVoltage = dict_config['RampRateVoltage']
        self.RampRateCurrent = dict_config['RampRateCurrent']
        self.ProbeType = dict_config['ProbeType']
        self.ComplianceVoltage = dict_config['ComplianceVoltage']
        self.ComplianceCurrent = dict_config['ComplianceCurrent']
        self.Output = dict_config['Output']
        self.ManualActivation = dict_config.get('ManualActivation', False)
        if self.SupportsSweeping:
            if 'SweepSampleTime' in dict_config:
                self.SweepSampleTime = dict_config['SweepSampleTime']
            if 'SweepSamplePoints' in dict_config:
                self.SweepSamplePoints = dict_config['SweepSamplePoints']
            if 'SweepStartValue' in dict_config:
                self.SweepStartValue = dict_config['SweepStartValue']
            if 'SweepEndValue' in dict_config:
                self.SweepEndValue = dict_config['SweepEndValue']
            

    def activate(self):
        self.Output = True
    
    def deactivate(self):
        self.Output = False
