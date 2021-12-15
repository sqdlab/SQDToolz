# AWG Waveform Transformations

The application of waveform transformations is highlighted in the [AWG HAL section](AWG_Pulse_Building.md). Note that the waveform transformations are defined in `sqdtoolz/HAL/WaveformTransformations.py` with each object prefixed with `WFMT_`.

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
WFMT_ModulationIQ('IQmod', lab, 100e6)
...
#Reset phase of IQ moduation to 0.5 radians
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive A", lab.WFMT('IQmod').apply(phase=0.5), 20e-9, 0.1))
#Continue the phase onwards from the previous segments
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive B", lab.WFMT('IQmod').apply(), 20e-9, 0.1))
#Continue the phase onwards from the previous segments but add 0.1 radians
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive C", lab.WFMT('IQmod').apply(phase_offset=0.1), 20e-9, 0.1))
```

Note that by default *ɸ* is set to zero at the beginning of the entire waveform sequence and accumulates with time. If one wishes to start from a zero phase at the beginning of a particular segment, then the `phase=0` argument must be supplied to the `apply()` function.
