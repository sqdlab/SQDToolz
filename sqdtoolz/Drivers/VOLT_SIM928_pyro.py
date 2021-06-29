import Pyro4

Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.PICKLE_PROTOCOL_VERSION = 2
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle','json', 'marshal', 'serpent'])

from qcodes import Instrument, InstrumentChannel

class SIM_928_pyro(Instrument):
    
    def __init__(self, uri_location=r'Z:/DataAnalysis/Notebooks/qcodes/SIM_928_Bluefors_rack.txt', slots=[1,2,3], **kwargs):
        super().__init__(**kwargs)
        with open(uri_location, 'r') as fh:
            uri = fh.read()
        self.sim = Pyro4.Proxy(uri)

        for ch_ind in slots:
            leName = f'CH{ch_ind}'
            cur_module = SIM928_channel(self, ch_ind, leName)
            self.add_submodule(leName, cur_module)    #Name is christened inside the channel object...

class SIM928_channel(InstrumentChannel):

    def __init__(self, parent, ch_ind, name):
        super().__init__(parent, name)
        self.ch_ind = ch_ind
        self.sim = parent.sim
        self.delay = 50e-3 # hardcoded in FPGA Rack1 PC

    @property
    def Output(self):
        return True
    @Output.setter
    def Output(self, val):
        pass
        
    @property
    def Voltage(self):
        return float(self.sim.get_voltage(self.ch_ind))
    @Voltage.setter
    def Voltage(self, val):
        self.sim.set_voltage(self.ch_ind, float(val))
        
    @property
    def RampRate(self):
        step, self.delay = self.sim.get_ramp_step_and_delay()
        return step/self.delay
    @RampRate.setter
    def RampRate(self, val):
        self.sim.set_ramp_step_and_delay(val*self.delay, self.delay)