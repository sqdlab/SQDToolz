from sqdtoolz.HAL.HALbase import*

class GENvoltSource(HALbase):
    def __init__(self, hal_name, lab, instr_gen_volt_src_channel):
        HALbase.__init__(self, hal_name)
        if lab._register_HAL(self):
            #
            self._instr_volt = lab._get_instrument(instr_gen_volt_src_channel)

    def __new__(cls, hal_name, lab, instr_gen_volt_src_channel):
        prev_exists = lab.get_HAL(hal_name)
        if prev_exists:
            assert isinstance(prev_exists, GENvoltSource), "A different HAL type already exists by this name."
            return prev_exists
        else:
            return super(GENvoltSource, cls).__new__(cls)

    @property
    def Output(self):
        return self._instr_volt.Output
    @Output.setter
    def Output(self, val):
        self._instr_volt.Output = val
        
    @property
    def Voltage(self):
        return self._instr_volt.Voltage
    @Voltage.setter
    def Voltage(self, val):
        self._instr_volt.Voltage = val
        
    @property
    def RampRate(self):
        return self._instr_volt.RampRate
    @RampRate.setter
    def RampRate(self, val):
        self._instr_volt.RampRate = val

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_volt.full_name,
            'type' : 'GENvoltSource'
            }
        self.pack_properties_to_dict(['Voltage', 'RampRate', 'Output'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['type'] == 'GENvoltSource', 'Cannot set configuration to a Voltage-Source with a configuration that is of type ' + dict_config['type']
        self.Voltage = dict_config['Voltage']
        self.RampRate = dict_config['RampRate']
        self.Output = dict_config['Output']
