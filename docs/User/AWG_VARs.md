# Sweeping AWG waveform parameters

The article discusses how one may use VAR objects sweep parameters in AWG waveforms. Note that, as discussed in the [sweeping article](Exp_Sweep.md), one requires a [`Variable` object](Var_Defns.md), which attaches itself to some parameter, to sweep a given parameter.

Consider a simple waveform example adapted from the an [earlier article](AWG_Pulse_Building.md), where one assumes that `lab` has is a valid `Laboratory` object:

```python
lab.load_instrument('tekAWG')
lab.load_instrument('keysightAWG')

...

WFMT_ModulationIQ('IQmod', lab, 100e6)

WaveformAWG("Wfm1", lab, [('tekAWG', 'CH1'), ('keysightAWG', 'CH3')], 1e9)
lab.HAL("Wfm1").add_waveform_segment(WFS_Constant("Wait", None, 40e-6, 0.0))
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Drive", lab.WFMT('IQmod').apply(), 20e-9, 0.1))
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("Flip", lab.WFMT('IQmod').apply(phase=np.pi), 20e-9, 0.1))
lab.HAL("Wfm1").add_waveform_segment(WFS_Constant("Read", None, 4e-6, 0.0))

lab.HAL("Wfm1").get_output_channel(0).marker(1).set_markers_to_segments(["Read"])
```

### Sweeping waveform segment parameters

Now a `WFS_Gaussian` has the property `Amplitude`. To sweep this parameter in the `"Drive"` segment, one may create the VAR:

```python
VariableProperty("driveAmpl", lab, lab.HAL("Wfm1").get_waveform_segment("Drive"), 'Amplitude')
```

The idea is the waveform segment object is the SQDToolz object passed onto `VariableProperty`, while the property `'Amplitude'` is passed on as the final argument. Similarly, one may sweep the length of the waveform segment via the universal property `'Duration'` (noting the [considerations](AWG_Pulse_Building.md#flexible-time-segments-in-waveforms-of-fixed-time-length) on waveform length):

```python
VariableProperty("driveTime", lab, lab.HAL("Wfm1").get_waveform_segment("Drive"), 'Duration')
```

### Sweeping waveform modulation parameters

Notice the [WFMT](AWG_WFMTs.md) used in `"Drive"` and `"Flip"` is a [`WFMT_ModulationIQ`](AWG_WFMTs.md#modulationiq). This modulation parameter has the attributes `phase` and `phase_offset`. To sweep these parameters in an experiment, one needs to obtain the WFMT SQDToolz object:

```python
VariableProperty('drive_phase', lab, lab.HAL("Wfm1").get_waveform_segment('Flip').get_WFMT(), 'phase_offset')
```

The `get_WFMT()` function fetches the WFMT child object that lives within the waveform segment object. As usual, the desired attribute, in this case `phase_offset`, is passed as the final argument in `VariableProperty`.

