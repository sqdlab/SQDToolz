import RPi.GPIO as GPIO
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
    def __init__(self, pins = None) :
        """
        Class constructor
        @param pins: list of GPIO pins to setup, None if not initialising any
        """

        # Setup how pins are referenced
        GPIO.setmode(GPIO.BCM)
        print("PINS ARE: ", pins)
        # Setup Pins
        if pins != None :
            for pin in pins :
                print("SETTING UP PIN: ", pin)
                self.setup_pin(int(pin))

    
    def handle_command(self, cmdType, command) :
        """
        """
        if cmdType == "READ" :
            return self.read_command(command)
        elif cmdType == "WRITE" :
            return self.write_command(command)
        else :
            return "Invalid CMD Type"
        
    def setup_pin(self, pin) :
        GPIO.setup(pin, GPIO.OUT)

    def write_command(self, command) :
        """
        Method to set output of GPIO pin
        """
        command = command.split(",")
        print("SPLIT COMMAND IS: ", command)
        return GPIO.output(int(command[0]), int(command[1]))

    def read_command(self, command) :
        """

        """
        print("READ COMMAND IS: ", command)
        return GPIO.input(int(command))
        


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
    try :
        print("Please enter pins to setup")
        pins = input().split(",")
        device = Device(pins)
        print(device)
        while (1) :
            print(handle_input(device))
    except Exception as e:
        print(e)
        GPIO.cleanup()
