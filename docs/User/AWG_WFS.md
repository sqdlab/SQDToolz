# AWG Waveform Segments

The waveform segments are defined in `HAL/WaveformSegments.py`. All waveform segment objects that can be added to a [AWG HAL](AWG_Pulse_Building.md) have a prefix `WFS_`. The currently available waveform segment types are listed on this page:

- [WFS_Constant](#wfs-constant)
- [WFS_Gaussian](#wfs-gaussian)
- [WFS_Cosine](#wfs-cosine)

## WFS Constant

`WFS_Constant` provides a simple constant-valued segment:

```python
#Define a constant segment that is 40ns at 0.7V
WFS_Constant("Wait", None, 40e-9, 0.7)
```

The default value for the last argument is zero. Note that the constant value is the same across all channels in the case of multi-channel waveforms. The `WFS_Constant` object consists of the properties:

- `Duration` - length of waveform
- `Value` - the constant value to output for the waveform.

## WFS Gaussian

`WFS_Gaussian` provides a nice Gaussian line-shape:

```python
#Define a Gaussian segment that is 40ns with an amplitude of 0.7V
WFS_Gaussian("Hill", None, 40e-9, 0.7)
#Define the same Gaussian segment with with 3 standard deviations either direction
WFS_Gaussian("Hill", None, 40e-9, 0.7, num_sd=3)
```

The Gaussian lineshape is constructed from a normalised Gaussian for the given standard deviation $\sigma$:

$$G(x)=\exp\left(-\frac{x^2}{\sigma^2}\right)$$

in which $x$ is taken from $-\sigma$ to $+\sigma$. Then the horizontal axis is scaled across the samples over the given duration. Then the waveform is vertically moved down such that the start and end points are zero. Finally, the vertical centre is scaled to match the prescribed amplitude.

The `WFS_Gaussian` object consists of the properties:

- `Duration` - length of waveform
- `Amplitude` - the height of the Gaussian waveform
- `NumStdDev` - number of standard deviations $\sigma$ taken on either side of the Gaussian

## WFS Cosine

`WFS_Cosine` provides a sinusoidal waveform. Note that it is recommended that one use a sinusoidal [waveform transformation](AWG_WFMTs.md) to produce a modulated sine wave on a given [waveform segment envelope](AWG_Pulse_Building.md) when defining waveform drives for cases like a qubit as all calibration parameters can be linked its more flexible properties and features (such as phase continuation across multiple waveform segments).

Nonetheless, `WFS_Cosine` provides a cosine defined by:

$$f(t)=A\cos(2\pi ft +\phi)$$

where the symbols and their associated `WFS_Cosine` properties are:

- $A$, `Amplitude` - amplitude of the sinusoid
- $f$, `Frequency` - frequency of the sinusoid
- $\phi$, `Phase` - phase of the sinusoid

and as usual the `Duration` property defines the length of the waveform segment.
