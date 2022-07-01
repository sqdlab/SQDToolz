import serial
import time
import os

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
        retData = self._ser.readline().decode('utf-8').rstrip()
        #time.sleep(0.2)
        while (self._ser.in_waiting) :
            retData = self._ser.readline().decode('utf-8').rstrip()
            print(retData)
        return retData
        


"""
Helper functions
"""
def handle_input(devices) :
    """
    """
    #DEVICE_NUM = 0
    COMMAND_TYPE = 1 - 1
    COMMAND = 2 - 1
    #print("INPUT CMD")
    command = input()
    #print("CMD RECV")
    command = command.split(":")
    #print(command)

    cmdResult = devices.handle_command(command[COMMAND_TYPE],command[COMMAND])
    #print("cmdResult: ", cmdResult)
    return cmdResult

"""
Program
"""
if __name__ == "__main__" :
    print(os.listdir("/dev/"))
    print("Please enter port")
    port = input()
    device = Device(port)
    print(device)
    while (1) :
        print(handle_input(device))
