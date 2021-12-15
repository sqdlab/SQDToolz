# AWG Pulse Building

## A simple example

Consider the following timing-diagram (drawn not to scale) in which one uses two AWG channels to produce the required charge-line waveform via IQ modulation (the two IQ outputs are fed directly into an IQ mixer). In addition, a marker associated with one of the channels from the AWG is used to trigger a microwave source during readout:

![My Diagram](AWG_Pulse_Building_example1.drawio.svg)

The following code demonstrates a possible implementation of the above waveform (assuming that `lab` has is a valid `Laboratory` object):

```python
#Loading instruments from the YAML
lab.load_instrument('tekAWG')
lab.load_instrument('keysightAWG')

...

#(A) - Define the modulation waveform transformation
WFMT_ModulationIQ('IQmod', lab, 100e6)

#(B) - Defining the main instrument HAL for the AWG
WaveformAWG("Wfm1", lab, [('tekAWG', 'CH1'), ('keysightAWG', 'CH3')], 1e9)

#(C) - Add a basic wait
lab.HAL("Wfm1").add_waveform_segment(WFS_Constant("Wait", None, 40e-6, 0.0))
#(D) - Add a sinusoidal IQ drive 
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive", lab.WFMT('IQmod').apply(), 20e-9, 0.1))
#Add a readout waveform (similar to the wait)
lab.HAL("Wfm1").add_waveform_segment(WFS_Constant("Read", None, 4e-6, 0.0))

#(E) - Set the second marker on the tekAWG to turn ON during the Read segment only
lab.HAL("Wfm1").get_output_channel(0).marker(1).set_markers_to_segments(["Read"])
```

The waveform HAL is uniquely named as `"Wfm1"`. The actual waveform is built by adding waveform segments. Note a common syntax for waveform segment objects (the objects with the prefix `WFS_`) all start with a name which must be unique within the waveform. The code has a few notable other features:
- (A) - A waveform-transformation, when passed onto a waveform segment, transforms the final segment waveform. In this case, the `WFMT_ModulationIQ` automatically maps the envelope waveform onto the two channels with I and Q sinusoidal waveforms.
- (B) - Defines the actual Waveform AWG HAL with the sample-rate set to 1GSPS. Note that it takes in a list of instrument and channel-name tuples. Here it forms the overall charge-line waveform using CH1 from a Tektronix AWG and CH3 from a Keysight AWG. The engine takes care of the underlying details!
- (C) - Using a `WFS_Constant` type, a basic 40μs is done by outputting zero on both channels.
- (D) - The IQ drive is done with a Gaussian envelope defined by `WFS_Gaussian`. The drive-envelope is 20ns long and 0.1V in amplitude. The application of the actual IQ modulation is given by the command `lab.WFMT("IQmod").apply()` which accesses the previously defined transformation `"IQmod"` to apply the 100MHz drive.
- (E) - The Tektronix AWG is defined to be the first channel; so index 0. The associated marker is to be the second marker; so index 1. The marker output is tied to a list of segments; in this case, just the `"Read"` segment.

Note that is all that must be done to define a waveform. To activate this particular waveform in an experiment, add the HAL object `"Wfm1"` to the list of HALs in the associated `ExperimentConfiguration` object used in a given `Experiment`. When running the experiment, **all AWG programming and sequencing is automatically done by the engine and thus, requires no further user input**. The engine will also only automatically reprogram the AWGs if the waveform has changed. This is especially useful the case where a waveform parameter is being swept in an experiment. One may define a sweeping variable in the usual manner (see notes on the `Experiment` and `Variable` classes for further details):

```python
VariableProperty("driveAmpl", lab, lab.HAL("Wfm1").get_waveform_segment("Drive"), 'Amplitude')
lab.VAR('testAmpl').Value = 0.3
```
Note that the `WFS_Gaussian` object has an `Amplitude` property that is being tied to the variable `"driveAmpl"`. Another useful property common to all waveform segment classes is `Duration`.


## Flexible time-segments in waveforms of fixed time-length


## Fancier markers

In the above example, the marker for a particular channel was set to be ON during a particular segment. However, markers can be defined to be ON over several different modes via its interface functions:

- `set_markers_to_none()` - disables markers on this marker channel
- `set_markers_to_segments([...])` - the marker is set to ON during the segments (names given as strings) in the list.
- `set_markers_to_trigger()` - marker now behaves like a single Trigger pulse. It is only in this mode that the properties `TrigPulseLength` (length of the digital pulse) and `TrigPulseDelay` (initial delay until the digital pulse) are utilised by the engine.
- `set_markers_to_arbitrary([...])` - given a list of 0s and 1s, the marker is set to be 0 or 1 during said samples. Care must be taken as the list of samples must match the number of samples in the overall waveform.

Note that the first two functions should satisfy 99% of use cases with the third function used in the odd case where the marker is just a trigger pulse that does not care about the individual waveform segments. The last function is given as a last-resort and one should first reconsider the design of the waveform segments.

Finally, the property `TrigPolarity` sets the polarity (positive: 1, negative: or 0). If negative polarity, then the output marker waveform is inverted (so ON is zero and OFF is one).

## Fancier waveform transformations
