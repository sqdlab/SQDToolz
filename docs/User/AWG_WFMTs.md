# AWG Waveform Transformations

The application of waveform transformations is highlighted in the [AWG HAL section](AWG_Pulse_Building.md). Note that the waveform transformations are defined in `sqdtoolz/HAL/WaveformTransformations.py` with each object prefixed with `WFMT_`. All waveform transformation objects must register onto a `Laboratory` object passed on creation. Thus, given a `Laboratory` object `lab`, a given waveform transformation can be accessed via the `WFMT(...)` function:

```python
#Get the waveform transformation registered under the name QubitDrive
wfmt = lab.WFMT("QubitDrive")
```

The different waveform transformations available in SQDToolz are highlighted in this page:

- [ModulationIQ](#modulationiq)

## ModulationIQ

`WFMT_ModulationIQ` applies to a two-channel waveform in which the first and second channels represent the I and Q channels of an IQ-modulated waveform:

<img src="https://render.githubusercontent.com/render/math?math=I(t)=A\cos(2\pi f t%2B\phi)%2BI_{dc}">

<img src="https://render.githubusercontent.com/render/math?math=Q(t)=aA\cos(2\pi f t %2B \phi %2B \varphi)%2BQ_{dc}">

Note that the modulation signals given above are multiplied onto the envelopes specified by the main pulse segment. The symbols and their associated `WFMT_ModulationIQ` properties are:

- *f*, `IQFrequency` - IQ modulation frequency
- <img src="https://render.githubusercontent.com/render/math?math=I_{dc},Q_{dc}">, `IQdcOffset` - DC offsets on the I and Q channels as specified by a tuple. This accounts for nonlinearities in the output channels as found from, for example, a mixer LO leakage calibration.
- *a*, `IQAmplitudeFactor` - IQ amplitude calibration factor. This accounts for the differences in the signal attenuation between the I and Q channels as found from, for example, a mixer sideband calibration.
- *φ*, `IQPhaseOffset` - IQ phase offset calibration. This accounts for the differences in the line lengths between the I and Q channels as found from, for example, a mixer sideband calibration.
- *A*, `IQAmplitude` - IQ modulation amplitude. It is usually just set to unity as the envelope specified in the pulse segment provides a nice method to control the amplitude.

Note that the IQ modulation phase *ɸ* is controlled automatically by the engine. It can be however, controlled in the pulse segment definitions via `phase` and `phase_offset` arguments supplied to the `apply()` function:


```python
#Object creation requires a unique name, the Laboratory object and the initial modulation frequency.
WFMT_ModulationIQ('IQmod', lab, 100e6)
...
#Reset phase of IQ moduation to 0.5 radians
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive A", lab.WFMT('IQmod').apply(phase=0.5), 20e-9, 0.1))
#Continue the phase onwards from the previous segments
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive B", lab.WFMT('IQmod').apply(), 20e-9, 0.1))
#Continue the phase onwards from the previous segments but add 0.1 radians
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive C", lab.WFMT('IQmod').apply(phase_offset=0.1), 20e-9, 0.1))
```

Note that by default *ɸ* is set to zero at the beginning of the entire waveform sequence and accumulates with time. Thus, if one uses `apply()`, the phase will be taken relative to time from the beginning. Phase can be dynamically manipulated via arguments given to `apply()` (note that only one of these can be used per segment):

- `phase` - if one wishes to start from a zero phase at the beginning of a particular segment, then the `phase=0` argument must be supplied to the `apply()` function. Similarly, one may reset the phase to any value. For example, `phase=0.1` will take the phase to be `0.1` at the beginning of that segment and all subsequent applications of this `WFMT` will take the phase to be such that it will be `0.1` if tracing back to the beginning of this segment.
- `phase_offset` - this has a similar behaviour to `phase`, but it **adds** the value to be current phase at the beginning of the segment with the supplied offset. Thus, if the phase were accumulating to `0.5` at the segment, using `apply(phase_offset=0.1)` will set the phase to be `0.6` and all subsequent applications of this `WFMT` will ensure that the phase is `0.6` if tracing back to the beginning of this segment.
- `phase_segment` - this **adds** a phase value to the current segment only without affecting the global phase accumulation. For example, `apply(phase_segment=np.pi/2)` would be applicable when running Y-Gates.

These function of these arguments are better illustrated in the figure below:

![My Diagram](WFMT_IQ_phases.drawio.svg)

Notice how `apply()` creates the waveform given the phase of zero set from the beginning. Using `phase=np.pi` sets the phase on that segment to pi and all subsequent segments will use this new phase as the starting point (as shown by the dashed lines). Using `phase_offset=np.pi` resets the global phase point, but the phase that is set is added onto the phase that was currently present. Finally, `phase_segment=np.pi` adds pi (onto the current phase) only to the current segment. Subsequent segments will have the phase as continued from the beginning of said segment. That is, `phase` and `phase_offset` changes the phase of the current and subsequent segments, while `phase_segment` only offsets the current segment.
