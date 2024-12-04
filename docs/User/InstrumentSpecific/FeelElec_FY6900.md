# FeelElec FY6900 (Driver: FGEN_FY6900)

The [FeelElec FY6900](https://cdn.manomano.com/files/pdf/26095634.pdf) Function/Arbitrary Waveform generator with two channels. It supports:
- Amplitude: 0-20Vpp
- Frequency: 0.01Hz-100MHz
- Offset: -12V to 12V
- Duty Cycle: 0.01-99.99%

It communicates via USB (it's a basic USB-COM driver).

The unit can be setup in two modes:
- [Function generator mode](#function-generator-mode)

## Function generator mode

YAML entry:

```yaml
  fgen:
    type: sqdtoolz.Drivers.FGEN_FY6900.FGEN_FY6900
    address: '/dev/ttyUSB0'
    enable_forced_reconnect: true
```

Just set the appropriate COM port ID (e.g. `'COM4'` for the `address`). Just use the HAL `GENfuncGen` to control this unit. Note that the output channels are enumerated as `'CH1'` and `'CH2'`.
