# Waveform Transformations

Conceptually, waveforms in the higher-level Experiment objects should just think about the physical waveform to send across the given signal line pertaining to the device (like some qubit line or a readout line). Thus, the details on how the waveform is realised (such as using a particular baseband frequency for multi-channel IQ modulation or single-channel double-upconversion) should be abstracted from the given implementation. The classes derived from `WaveformTransformation` realise this abstraction by providing a transformation on the input waveform segments to yield the required output waveform on the AWG output(s).

The `WaveformTransformation` are automatically registered onto a `Laboratory` object on creation and are readily accessed by name via the WFMT function. The transformation object is mapped onto a `WaveformSegmentBase` object within a waveform collection. For example, consider two calibrated transformations for two AM-frequencies. One can modulate individual segments with either of the two frequencies by mapping said `WaveformTransformation` objects onto said individual segments. The mapping is done by setting the waveform transformation argument in the given waveform segment:

``` python
#Assuming that lab is a Laboratory object and the transformation is called 'qubitIQ'
WFS_Constant(name, lab.WFMT('qubitIQ').apply(), time_len, value=0.0)
```

Note that the object itself is not passed but rather the return-value on calling the function apply. This enables one to pass on arguments specific to the segment in the transformation. For example, an amplitude modulated pulse may require the setting of phase values. This can be done by passing keyword arguments to the function apply. Note that this implies that a given set of similar transformation classes must all share the same keyword arguments. For example, one may write a Rabi experiment class which requires an envelope to be modulated by some frequency. To specify the phase at a given waveform segment, the keyword arguments must be agreed upon and recognised by all relevant amplitude modulating transformations that may be passed onto this waveform.
