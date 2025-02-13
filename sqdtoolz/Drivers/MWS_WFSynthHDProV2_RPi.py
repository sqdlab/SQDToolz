from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
from sqdtoolz.Drivers.MWS_WFSynthHDProV2 import MWS_WFSynthHDProV2, MWS_WFSynthHDProV2_Channel
import re

class MWS_WFSynthHDProV2_RPi_Device(MWS_WFSynthHDProV2):
    """
    Driver for the Windfreak SynthHD PRO v2.
    """
    def __init__(self, name, dev_id, parent:Instrument, **kwargs):
        self.dev_id = dev_id
        self._parent = parent
        super().__init__(name, '', init_instrument_only=True)
        

    #NEED THESE BECAUSE QCODES INSERTS \n etc...
    def _get_cmd(self, cmd):
        return self._parent.ask(f'USB:ASK{self.dev_id}? {cmd}')
    def _set_cmd(self, cmd, val):
        self._parent.write(f'USB:WRITE{self.dev_id} {cmd}')

class MWS_WFSynthHDProV2_RPi(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=30)
        
        a = self.ask(f'USB:DEVICES?')
        a = a[a.find('['):]

        #TODO: Check this! Steven found this off ChatGPT; it may have edge-case issues if [] or () fall within the names?!
        pattern = r'\[([^\]]+)\]\s*\(([^)]+)\)'
        matches = re.findall(pattern, a)
        dict_devices = {key: value for key, value in matches}
        
        self.devices = {}
        for dev in dict_devices:
            cur_channel = MWS_WFSynthHDProV2_RPi_Device('WF_'+dev, dev, self)
            self.add_submodule('WF_'+dev, cur_channel)
            self.devices[dev] = cur_channel
        
        # for m in self.devices:
        #     print(f'WF_{m}: {self.devices[m].serial()}')

    #NEED THESE BECAUSE QCODES INSERTS \n etc...
    def _get_cmd(self, cmd):

        return 0
        self._stdin.write('READ:' + cmd + '\n')
        return self.read_line(self._stdout)
    def _set_cmd(self, cmd, val):
        return
        self._stdin.write('WRITE:' + cmd + '\n')
        self.read_line(self._stdout)
        self._stdout.flush()



# test = MWS_WFSynthHDProV2_RPi('bnob', 'TCPIP::192.168.1.37::4000::SOCKET')
