from sqdtoolz.Drivers.MWS_WFSynthHDProV2 import MWS_WFSynthHDProV2, MWS_WFSynthHDProV2_Channel
import paramiko

class MWS_WFSynthHDProV2_RPi(MWS_WFSynthHDProV2):
    """
    Driver for the Windfreak SynthHD PRO v2.
    """
    def __init__(self, name, address, username, password, com_port = None, dev_serial_num = None, **kwargs):
        kwargs['init_instrument_only'] = True
        port = kwargs.get('port', 22)

        assert ((com_port is not None) or (dev_serial_num is not None)), "No Method of Connection Provided"
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try :
            self._ssh.connect(address, port, username, password)
        except :
            assert False, f"Unable to connect to RPi at {address}"

        self._stdin, self._stdout, self._stderr = self._ssh.exec_command("python3 test_wind_new.py\n")
        available_ports = self.read_line(self._stdout) # Get list of all ports from /dev/ to iterate through
        available_ports = available_ports.replace('[','').replace(']','').replace("'","").replace(" ","").split(',')
        available_ports = [port for port in available_ports if "ttyACM" in port]
        res = self.read_line(self._stdout)
        if ((com_port is not None) and (com_port.strip("/dev/") in available_ports)) :
            # We have a com port which will be prioritised over serial number
            self._stdin.write(com_port + '\n')
        else :
            # We have a serial number and must loop
            for port in available_ports :
                if self.check_serial(dev_serial_num, port, address) :
                    self._stdin.write(com_port + '\n')
                    continue
        res = self.read_line(self._stdout)
        self._stdout.flush()
        self._stdin.flush()
        #WRITE A THING TO QUERY SERIAL NUMBER 
        #Loop through TTYACM
        #
        
        #KILL PROGRAM

        #Restart Program
        # self._stdin, self._stdout, self._stderr = self._ssh.exec_command("python3 test_wind.py\n")
        # res = self.read_line(self._stdout)
        # self._stdin.write(com_port + '\n')
        # res = self.read_line(self._stdout)
        # self._stdout.flush()
        # self._stdin.flush()
        #res = self._get_cmd('*?')

        super().__init__(name, address, **kwargs)

    def check_serial(self, serial_number, com_port, address) :
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try :
            self._ssh.connect(address, port, username, password)
        except :
            assert False, f"Unable to connect to RPi at {address}"

        self._stdin, self._stdout, self._stderr = self._ssh.exec_command("python3 test_wind_new.py\n")
        available_ports = self.read_line(self._stdout) # Get list of all ports from /dev/ to iterate through
        res = self.read_line(self._stdout)
        if (com_port is not None and com_port in available_ports) :
            # We have a com port which will be prioritised over serial number
            self._stdin.write(com_port + '\n')

        res = self.read_line(self._stdout)
        self._stdout.flush()
        self._stdin.flush()
        self._stdin.write('READ:' + '-' + '\n')
        actual_serial_num = self.read_line(self._stdout)
        if (serial_number == int(actual_serial_num)) :
            return True
        else :
            return False

    def read_line(self, channel):
        if (not channel.channel.eof_received):
            return channel.readline()
        else :
            return None

    #NEED THESE BECAUSE QCODES INSERTS \n etc...
    def _get_cmd(self, cmd):
        self._stdin.write('READ:' + cmd + '\n')
        return self.read_line(self._stdout)
    def _set_cmd(self, cmd, val):
        self._stdin.write('WRITE:' + cmd + '\n')
        self.read_line(self._stdout)
        self._stdout.flush()
