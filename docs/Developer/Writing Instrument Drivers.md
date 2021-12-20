# Writing instrument Drivers

In general the instrument drivers must be compatible with Qcodes and they are to live in the <em>Drivers</em> folder. However, DDG, AWG and ACQ modules must provide additional functionality to interface with the <em>sqdtoolz</em> framework.

## Trigger pulses

Most instruments have digital output pulses that can be used as synchronisation triggers. Some are fixed pulses that are sent when outputting some waveform (like with AWGs) in other cases the pulses may be tuned to the user's specification (e.g. AWG markers or DDG outputs). These trigger pulses can be used as a trigger source for the AWG or ACQ instrument types. Instruments may support a digital output that can act as a trigger source - for example:

- Clock outputs from a DDG
- Marker outputs from an AWG
- General instrument SYNC outputs (typically not reconfigurable)

Such instruments should implement the outputs by instantiating an object that inherits from InstrumentChannel (in QCoDeS) and using the add_submodule function. These channel objects must be trigger pulse compatible by implementing the following properties:

- TrigEnable [True/False] - to physically set the output to be turned on/off
- TrigPulseDelay [Float] - time duration to wait before setting the trigger voltage away from the idle baseline
- TrigPulseLength [Float] - time duration of the trigger pulse when it sets the voltage away from the idle baseline
- TrigPolarity [0/1] - if one, the idle baseline is low and trigger is high (positive polarity). If zero, the idle baseline is high and the trigger is low (negative polarity).

In doing so, these channel objects can be used to instantiate a Trigger object. The Trigger object is a wrapper that can be used to safely set the pulse characteristics from higher level API.

## Writing DDG drivers

The DDG driver must implement the following functions in order to be compatible with the DDG module in the HAL:

- get_trigger_output(self, identifier)
- get_all_trigger_sources(self)

The functions return a Trigger object (given the name of that output trigger channel) or the entire list of available Trigger objects (the objects are easily distinguished by noting that the Trigger object holds the name of the Trigger output channel). From the Trigger object one may safely manipulate the trigger pulse characteristics (e.g. delay, length, polarity etc.). Note that it is advisable to return a copied list of trigger objects when implementing the second function (that is, if the list of Trigger objects are stored internally in the driver class). Thus, internally every output channel:

- Instantiate a channel object via a class inheriting InstrumentChannel (to ensure that the H/W parameters are stored in the QCoDeS instrument snapshots).
- Use add_submodule to add it to the main Instrument object
- Instantiate a Trigger object for each channel by passing the instrument channel object (passed before into the add_submodule function).

