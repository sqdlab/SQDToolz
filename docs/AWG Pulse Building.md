# AWG Pulse Building

## Pulse Segments

Waveform segments are the smallest atomic building blocks of a waveform output from single (or sets of) AWG channels and should inherit from the WaveformSegment class. The classes are prefixed with WFS_ for clarity. These classes must implement the property: Duration which returns the length of the segment in seconds.


