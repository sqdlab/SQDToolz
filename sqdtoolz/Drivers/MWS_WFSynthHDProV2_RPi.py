from sqdtoolz.Drivers.MWS_WFSynthHDProV2 import MWS_WFSynthHDProV2, MWS_WFSynthHDProV2_Channel
import paramiko

class MWS_WFSynthHDProV2_RPi(MWS_WFSynthHDProV2):
    """
    Driver for the Windfreak SynthHD PRO v2.
    """
    def __init__(self, name, address, username, password, com_port, **kwargs):
        kwargs['init_instrument_only'] = True
        port = kwargs.get('port', 22)

        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try :
            self._ssh.connect(address, port, username, password)
        except :
            assert False, f"Unable to connect to RPi at {address}"

        self._stdin, self._stdout, self._stderr = self._ssh.exec_command("python3 test_wind.py\n")
        res = self.read_line(self._stdout)
        self._stdin.write(com_port + '\n')
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

        res = self._get_cmd('M0:READ:*?')

        super().__init__(name, address, **kwargs)

    def read_line(self, channel):
        if (not channel.channel.eof_received):
            return channel.readline()

    #NEED THESE BECAUSE QCODES INSERTS \n etc...
    def _get_cmd(self, cmd):
        self._stdin.write('M0:READ:' + cmd + '\n')
        return self.read_line(self._stdout)
    def _set_cmd(self, cmd, val):
        self._stdin.write('M0:WRITE:' + cmd + '\n')
        self.read_line(self._stdout)
        self._stdout.flush()
