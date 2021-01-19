# Writing instrument Drivers

In general the instrument drivers must be compatible with Qcodes and they are to live in the <em>Drivers</em> folder. However, DDG, AWG and ACQ modules must provide additional functionality to interface with the <em>sqdtoolz</em> framework.

## Trigger pulses

Most instruments have digital output pulses that can be used as synchronisation triggers. Some are fixed pulses that are sent when outputting some waveform (like with AWGs) in other cases the pulses may be tuned to the user's specification (e.g. AWG markers or DDG outputs). These trigger pulses can be used as a trigger source for the AWG or ACQ instrument types. Instruments that support a digital output that can act as a trigger source must have functions that return a trigger pulse compatible (for example, a sync output or a programmable delay or marker channel) object which implements the following properties:

- TrigEnable [True/False] - to physically set the output to be turned on/off
- TrigPulseDelay [Float] - time duration to wait before setting the trigger voltage away from the idle baseline
- TrigPulseLength [Float] - time duration of the trigger pulse when it sets the voltage away from the idle baseline
- TrigPolarity [0/1] - if one, the idle baseline is low and trigger is high (positive polarity). If zero, the idle baseline is high and the trigger is low (negative polarity).


## Writing DDG drivers


