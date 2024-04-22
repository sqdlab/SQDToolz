# Delft IVVI Rack

This driver pertains to the [Delft IVVI DAC Rack](https://qtwork.tudelft.nl/~schouten/ivvi/index-ivvi.htm). The modules work as follows:

- The S2f module has jumper wires inside. Open it and map the desired DAC channels to AV1 and AV2 (suggested to use DAC1 and DAC2 for convenience).
- When setting the DAC outputs, they appear directly on the outputs of S2f and can be measured/monitored.
- The AV1 and AV2 outputs should connect to the S3b module (voltage/current source) to give an isolated voltage source output. In the case of S3b, AV1/AV2 correspond to the course and fine (x0.01) controls.
- Make sure to connect S3b to the second slot from the left (i.e. a [slot A module](https://qtwork.tudelft.nl/~schouten/ivvi/ivvidac2-basic.gif))
