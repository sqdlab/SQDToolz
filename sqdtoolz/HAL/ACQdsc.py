from sqdtoolz.HAL.HALbase import*

class ACQdsc(): #oscilloscope driver
    def __init__(self, hal_name, lab, instr_scp):
        #the local name (HAL name) in the current script for current experiment is taken note of
        HALbase.__init__(self, hal_name)

        # the nickname (or instrument ID) in the yaml file
        self._instr_id = instr_scp

        #verify the isntrument is correctly loaded and return the driver object of the instrument
        self._instr_scp = lab._get_instrument(instr_scp)

        #register the instrument as HAL using the name hal_name
        lab._register_HAL(self)
        self._lab = lab
        self._trigger_HAL = None
        self._trigger_HAL_address = []
        self.data_processor = None

    @classmethod 
    def fromConfigDict(cls, config_dict, lab): #what is the function of this 
        return cls(config_dict["Name"], lab, config_dict["instrument"])    
    
    @property
    def IsACQhal(self):
        return True
    def wfm_plot(self):
        self._instr_scp.wfm_plot()
