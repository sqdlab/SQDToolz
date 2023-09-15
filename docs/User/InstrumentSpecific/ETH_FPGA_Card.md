# ETH FPGA (Driver:ACQ_ETH_FPGA)

The ETH FPGA card has:
- 2 input ports each sampling an incoming voltage signal every 10ns.thus,it has fixed sampling rate of 10MSPS.
- four frequencies of 25MHz, 25MHz fast, 10MH, and 0MHz available at the mixer stage, for on chip down conversion.
- FIR filter, that has only a finite number of non-zero elements in the impulse response
- a math block to apply a mathematical transformation on the signals, which is currently not being used.
- a decimator, that has a smallest d-factor of 1. 
- on chip averaging.
- no integeration function.

Note: Currently only one of the inputs is being used, the other input is connected to a sample clock. 

To connect to fpga, the driver currently uses Pyro name server. follow the given steps to connect to the fpga. 
- Connect to Z-Drive
- QTLAB FPGA Server 
- Hit: S enter
- Run: %gui

# Default mode

YAML entry:

  fpga1:
    driver: sqdtoolz.Drivers.ACQ_ETH_FPGA
    type: ETHFPGA
    init:
      uri: 'Z:/DataAnalysis/Notebooks/qcodes/FPGA_Rack1_URI.txt'

Set the path correctly as there is no physical addrress to refer to in the YAML. 

The AWG can be used to check the working of and to reprogram the fpga, the wiring for which is shown below

![My Diagram3](FPGA_Test_Circuit.drawio.svg)

During measurements, the FPGA needs to be wired as below:

![My Diagram3](FPGA_Circuit_Connection.drawio.svg)

If the fpga throws as error, log in to the XP PC and reset the fpga using following commands in the QTLab gui:
- fpga.reload()
- fpga.reset()





