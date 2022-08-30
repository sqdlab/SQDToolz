from sqdtoolz.Drivers.SW_BJT_RPi import SW_BJT_RPi


switch = SW_BJT_RPi("switch", "192.168.0.115", "pi", "Experiment", pins = {"P0" : 19, "P1" : 16, "P2" : 26, "P4" : 20, "P5" : 21})
switch.Position = "P0"
print("")
switch.Position = "P1"
switch.Position = "P5"
switch.Position = "P1"
switch.Position = "P5"
switch.Position = "P1"
switch.Position = "P5"
switch.Position = "P1"
switch.Position = "P5"
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