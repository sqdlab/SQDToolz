import serial

"""
Classes for Device Management
"""
class Device() :
    """
    Class that contains all functions to interface with a device
    over a serial port
    """
    def __init__(self, comPort) :
        self._ser = self.setup_serial(comPort)
    
    def setup_serial(self, com = "/dev/ttyACM0") :
        """
        """
        ser = serial.Serial(com, 9600)
        return ser

    def handle_command(self, cmdType, command) :
        """
        """
        if cmdType == "READ" :
            return self.read_command(command)
        elif cmdType == "WRITE" :
            return self.write_command(command)
        else :
            return "Invalid CMD Type"
        

    def write_command(self, command) :
        """

        """
        return self._ser.write(bytes(command, 'utf-8'))

    def read_command(self, command) :
        """

        """
        self._ser.write(bytes(command, 'utf-8'))
        return self._ser.readline()
        


"""
Helper functions
"""
def handle_input(devices) :
    """
    """
    DEVICE_NUM = 0
    COMMAND_TYPE = 1
    COMMAND = 2
    #print("INPUT CMD")
    command = input()
    #print("CMD RECV")
    command = command.split(":")
    #print(command)

    cmdResult = devices[command[DEVICE_NUM]].handle_command(command[COMMAND_TYPE],command[COMMAND])
    #print("cmdResult: ", cmdResult)
    return cmdResult
    

def parse_ports(portList) :
    """
    """
    portList = portList.split(":")
    return setup_devices(portList)

def setup_devices(portList) :
    """
    """
    devices = dict()
    i = 1
    for port in portList :
        devices[f"M{0}".format(i)] = (Device(port))
        i += 1
    return devices



"""
Program
"""
if __name__ == "__main__" :
    print("Please enter list of ports")
    portList = input()
    devices = parse_ports(portList)
    print(devices)
    while (1) :
        print(handle_input(devices))

