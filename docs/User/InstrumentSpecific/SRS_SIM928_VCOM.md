# SRS SIM928 voltage module (using RS232-Ethernet adapter) (Driver: VOLT_SIM928_VCOM)

The SIM928 module takes up 1 slot in the SIM900 rack main frame. It has:
- One voltage output channel spanning ±20V (limited to 20mA output current)
- The module can be operated without code via the buttoned interface
- This driver connects to the serial version of the SIM900 mainframe using a *USR IOT Serial Device Server* adaptor (specifically the *USR-RCP232-302* model)

## Installation

Connect the RS232-Ethernet module to its 5V supply, Ethernet cable and the appropriate serial COM patch cable (otherwise, it won't communicate with the SIM900 mainframe). To use the server, a local software daemon must run on the local PC to create the virtual COM port:

- Find and install the software [*USR-VCOM_V3.7.2.529_Setup.exe*](https://www.pusr.com/support/downloads/usr-vcom-virtual-serial-software.html)
- Run the software *USR-VCOM*
- Click *Smart VCOM*
- Let it scan for the module (it should pick up the module's IP) and then click next
- It may crash - just restart the program
- Make sure it says "Connected" under "Net State" and then copy the COM ID (e.g. "COM4") into the YAML shown in the next section.

## Digital pulse modulation

YAML entry:

```yaml
  sim_rack928:
    type: sqdtoolz.Drivers.VOLT_SIM928_VCOM.VOLT_SIM928_VCOM
    address: 'COM4'
    enable_forced_reconnect: true
    init:
      gpib_slot: 2
```

Just set the COM port address correctly. The GPIO slot ID should match that of the binary toggle micro-switches on the back of the SIM900 mainframe.
