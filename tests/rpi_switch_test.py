from sqdtoolz.Drivers.SW_BJT_RPi import SW_BJT_RPi


switch = SW_BJT_RPi("switch", "TCPIP::192.168.1.6::4000::SOCKET", pins = {"P0" : 10, "P1" : 3, "P2" : 5, "P3" : 7, "P4" : 11})
switch.Position = "P0"
print("")
switch.Position = "P1"
switch.Position = "P2"
switch.Position = "P3"
switch.Position = "P4"
switch.Position = "P0"
switch.Position = "P1"
switch.Position = "P2"
switch.Position = "P3"
switch.Position = "P4"
switch.Position = "P1"
switch.Position = "P2"
switch.Position = "P3"
switch.Position = "P4"
switch.Position = "P0"
print("")
switch.Position = "P2"
print("")
switch.Position = "P4"
print("")
switch.Position = "P5"
print("")
switch.Position = "P0"
# Code = hardware, P1 = 1, P4 = 5, P2 = 2, P3 = 4