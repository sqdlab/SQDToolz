# AWG Pulse Building

## Pulse Segments

Waveform segments are the smallest atomic building blocks of a waveform output from single (or sets of) AWG channels and should inherit from the WaveformSegment class. The classes are prefixed with WFS_ for clarity. These classes must implement the property: Duration which returns the length of the segment in seconds.

...

## AWG Waveform

The AWG waveform is constructed from individual channel objects provided by the AWG driver. The idea is that the waveforms and their associated markers are abstractly constructed in the HAL. During program execution, the AWG channels are automatically programmed.

### Markers

The markers are intrinsic to the channels and can be programmed in the following ways:

- None - No markers present
- Arbitrary - One provides a marker waveform in the form of a numpy array
- Segment List - The markers change to their on/off state (depending on the marker polarity) when reaching a given WaveformSegment
- Trigger - The markers can be controlled via the Trigger object the AWG Waveform objects may provide

Note that the last form is the only type that enables one to manipulate the markers as if they were Trigger pulses via the properties provided by its associated Trigger object. Otherwise, the when querying its Trigger object property, one simply obtains the associated trigger property given its current waveform (whether it is Arbitrary or a Segment List type).


## Driver code

The interface functions an AWG-compatible driver must implement the following functions in its main body:

```python
def program_channel(self, chan_id, wfm_data)
```

The program_channel function is used to pass on the entire waveform data that is to be output from a given channel. Note that the waveform data is simply a 1D numpy array that has the actual desired output voltage values. Thus, setting the amplitude of a given channel only sets the upper clipping limit in which it is in the best interest (in terms of output precision in the resolution) of the user to set the amplitude close to the upper limit of the maximum voltage value of the waveform. Note that it is typically not a good idea to keep changing said amplitude (that is, set it once for all upcoming waveforms) as the DAC used to set the gain is usually of lower resolution (like with the Tektronix AWG5204).

Each individual channel queried via the 

