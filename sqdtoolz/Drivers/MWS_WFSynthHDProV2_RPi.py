from qcodes import Instrument, InstrumentChannel, VisaInstrument, validators as vals
from sqdtoolz.Drivers.MWS_WFSynthHDProV2 import MWS_WFSynthHDProV2, MWS_WFSynthHDProV2_Channel
import re

#TODO have "set up devices" recieve the correct arrangement from the config yaml, or ensure another class is passing it to it elsewhere.

class MWS_WFSynthHDProV2_RPi_Device(MWS_WFSynthHDProV2):
    """
    Driver for the Windfreak SynthHD PRO v2.
    """
    def __init__(self, name, dev_id, parent:Instrument, **kwargs):
        self.dev_id = dev_id
        self._parent = parent
        self._address = ''
        self._terminator = ''
        self.timeout = self._parent.timeout
        super().__init__(name, '', init_instrument_only=True)
        

    #NEED THESE BECAUSE QCODES INSERTS \n etc...
    def _get_cmd(self, cmd):
        return self._parent.ask(f'USB:ASK{self.dev_id}? {cmd}')
    def _set_cmd(self, cmd, val):
        self._parent.write(f'USB:WRITE{self.dev_id} {cmd}')

class MWS_WFSynthHDProV2_RPi(VisaInstrument):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, terminator='\n', timeout=30)
        
        #TODO: Get this from the yaml instead
        self.expected_serial_dict = { 
            '1': '1182',
            '2': '1214',
            '3': '880'
        }
        
        self._set_up_devices()


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

    def _set_up_devices(self):
        a = self.ask(f'USB:DEVICES?')
        a = a[a.find('['):]

        #TODO: Regex to pull current devices and aliases off the RPi. Taken from ChatGPT and not tested thoroughly.
        #
        #           !!! Warning: it may have edge-case issues if [] or () fall within the names?!
        #
        pattern = r'\[([^\]]+)\]\s*\(([^)]+)\)'
        matches = re.findall(pattern, a)
        dict_devices = {key: value for key, value in matches}
        
        self.devices = {}
        self.devices_serial = {}
        for dev in dict_devices:
            cur_channel = MWS_WFSynthHDProV2_RPi_Device('WF_'+dev, dev, self)
            self.add_submodule('WF_'+dev, cur_channel)
            self.devices[dev] = cur_channel
        
        self.ensure_device_match()
     
        # for m in self.devices:
        #     print(f'WF_{m}: {self.devices[m].serial()}')
    
    def _update_device_serials(self):
        #used to match the device number with the serial
        for dev in self.devices:
            self.devices_serial[dev] = self.ask(f'USB:ASK{dev}? -')

    def _swap_alias(self, alias_old, alias_new):
        self.write(f'USB:ALIAS{alias_old} {alias_new}')
        self._update_device_serials()


    def ensure_device_match(self):
        self._update_device_serials()
        # Assert that both dictionaries have the same number of keys
        if len(self.expected_serial_dict) != len(self.devices_serial):
            raise ValueError("The number of devices in self.expected_serial_dict and self.devices_serial do not match.")
        
        # Iterate over the self.self.expected_serial_dict and check if the corresponding serials match
        for alias, expected_serial in self.expected_serial_dict.items():
            if alias not in self.devices_serial:
                print(self.expected_serial_dict)
                print(self.devices_serial)
                raise KeyError(f"Alias '{alias}' not found in self.devices_serial.")
            
            actual_serial = self.devices_serial[alias]
            
            # If the serials do not match, we swap aliases by passing the incorrect alias and correct alias
            if actual_serial != expected_serial:
                # Here, we're assuming 'alias' is the incorrect one and `expected_serial` is where it should be
                incorrect_alias = alias
                # We find the alias that corresponds to the `expected_serial` and swap
                correct_alias = next((key for key, value in self.devices_serial.items() if value == expected_serial), None)
                
                if correct_alias is None:
                    raise ValueError(f"No device found with the expected serial {expected_serial}. Cannot swap aliases.")

                # Call swap_alias to perform the alias swap
                self._swap_alias(incorrect_alias, correct_alias)
                
                # Recheck if the serials now match after the swap
                if self.devices_serial[incorrect_alias] != expected_serial:
                    raise ValueError(f"Serial mismatch for alias '{incorrect_alias}': expected {expected_serial}, found {self.devices_serial[incorrect_alias]}.")
        self._update_device_serials()

        



# test = MWS_WFSynthHDProV2_RPi('bnob', 'TCPIP::192.168.1.37::4000::SOCKET')
