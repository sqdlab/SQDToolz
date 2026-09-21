# List of ZI experiments
A list of all current experiments for ZI hardware. The source code for these experiments can be found in `sqdtoolz/Experiments/Experimental/`.
> **Note:** this list should be considered a work in progress, as experiments are still under development.

### Table of contents
This table of contents is given in roughly the order experiments would be needed for tuneup and experimentation on a new qubit chip.
- **[Resonator spectroscopy](#expzires):** `ExpZIRes`
    - [Resonator power sweep](#expzirespowersweep): `ExpZIResPowerSweep` 
    - [Resonator flux sweep](#expziresfluxsweep): `ExpZIResFluxSweep`
- **[Qubit spectroscopy](#expziqubitspec):** `ExpZIQubitSpec`
    - [Qubit spectroscopy flux sweep](#expziqubitfluxsweep): `ExpZIQubitFluxSweep`
    - [Qubit spectroscopy power sweep](#expziqubitpowersweep): `ExpZIQubitPowerSweep`
- **[Time domain](#expzirabiramseyt1):** `ExpZIRabiRamseyT1`
    - [Amplitude Rabi](#expzirabi): `ExpZIRabi`
    - [Lifetime $T_1$](#expzit1):  `ExpZIT1`
    - [Ramsey $T_2^*$](#expziramsey): `ExpZIRamsey`
- **[Dispersive shift](#expzidispersive)** $\chi$: `ExpZIDispersive`
- **[DRAG scaling](#expzidragscaling):** `ExpZIDragScaling`
- **Readout, TWPA and active reset:**
    - [IQ blobs](#expziblobs): `ExpZIBlobs`
    - [Active reset tuneup](#expziactiveresettuneup): `ExpZIActiveResetTuneup`
    - [TWPA optimisation](#expzitwpatuneup): `ExpZITWPATuneup`
    - [Lifetime $T_1$ (single shot)](#expzit1singleshot): `ExpZIT1SingleShot`
    - [Resonator frequency for optimised readout fidelity](#expziresoptimal): `ExpZIResOptimal`
    - [Readout amplitude + frequency sweep for optimised single-shot fidelity](#expziresoptimalampsweepss): `ExpZIResOptimalAmpSweepSS`
- **[Single qubit $X$ gate calibration](#expzicalibx):** `ExpZICalibX`
- **[Single-qubit randomised benchmarking](#expzirandomisedbenchmarking):** `ExpZIRandomisedBenchmarking`
- **[Single-qubit gate-set benchmarking (ETH-style)](#expzibenchmarketh):** `ExpZIBenchmarkETH`
- ***ef* characterisation**
  - **[Chevrons](#expzichevrons):** `ExpZIChevrons`
  - **Time domain:** `ExpZIRabiRamseyT1`
- **[QASM implementation](#expziqasm):** `ExpZIQASM`
    - [QASM data viewer](#expziqasmdataviewer): `ExpZIQASMDataViewer`
- **Two-qubit gate tuneup:**
    - [Flux-pulse chevrons on a fixed coupler](#expzichevrons2qfixedcoupler): `ExpZIChevrons2QFixedCoupler`
    - [Fixed-coupler CZ tuneup (amplitude + length)](#expzifixedcouplertuneup): `ExpZIFixedCouplerTuneup`
    - [CZ phase compensation](#expziphasecompensation2q): `ExpZIPhaseCompensation2Q`
    - [Bell-state fidelity](#expzibellstatefidelity): `ExpZIBellStateFidelity`
- **[Cryoscope (flux-pulse distortion calibration)](#expzicryoscope):** `ExpZICryoscope`
- **[Automated daily tuneup routine](#expzidailytuneup):** `ExpZIDailyTuneup`

Other documented experiments include:
- **Automated single qubit tuneup:** `ExpZISingleQubitTuneup` ([see the dedicated documentation](ZI_SingleQubitTuneup.md))
- **Running ZI workflows in SQDToolz:** `ExpZIqubit` (see [the dedicated documentation](ZI_ExpZIqubit.md))


## Experiments

### ExpZIRes

`class ExpZIRes(ExpZIqubit)`

#### Description

`ExpZIRes` runs a resonator spectroscopy experiment on a single qubit's readout
resonator using the Zurich Instruments LabOne Q `resonator_spectroscopy`
experiment. It sweeps readout frequency, acquires the I/Q response, and fits
the resulting lineshape to extract the resonator's centre frequency (and,
depending on the chosen fit type, its width, amplitude, offset, or internal/
external quality factors). Fitted parameters can optionally be written back
onto the qubit object and/or into user-supplied parameter objects.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and (optionally) write fitted parameters back to it. |
| `qubit_id` | `str` | The ID of the single qubit whose resonator is being measured. Must be a plain string, not a list. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `update_qubit_params` | `bool`, default `True` | If `True`, writes the fitted result(s) back onto the qubit object retrieved from `hal_QPU` (e.g. `ReadoutFrequency`, and for `fit_type='Full'` also `ReadoutQi`, `ReadoutQc`, `ReadoutQl`). |
| `dont_show_plot` | `bool`, default `False` | If `True`, the fitted plot is saved and closed rather than displayed. |
| `iq_indices` | `list`, default `[0, 1]` | Column indices in the retrieved data array corresponding to the I and Q components respectively. |
| `is_trough` | `bool`, default `False` | Whether the resonance appears as a dip (`True`) rather than a peak (`False`) in the response. Must be `True` if `fit_type='Fano'`. |
| `fit_type` | `str`, default `'Default'` | Which fitting routine to use: `'Default'`, `'Fano'`, or `'Full'` (see [Analysis](#analysis-fitting-and-outputs) below). |
| `param_freq` | parameter object, default `None` | If provided, its `.Value` is set to the fitted centre/resonant frequency. |
| `param_width` | parameter object, default `None` | If provided, its `.Value` is set to the fitted linewidth (`'Default'`/`'Fano'` fits only). |
| `param_amplitude` | parameter object, default `None` | If provided, its `.Value` is set to the fitted amplitude (`'Default'`/`'Fano'` fits only). |
| `param_offset` | parameter object, default `None` | If provided, its `.Value` is set to the fitted vertical offset (`'Default'`/`'Fano'` fits only). |
| `param_fano` | parameter object, default `None` | If provided, its `.Value` is set to the fitted Fano asymmetry factor (`fit_type='Fano'` only). |
| `dont_plot` | `bool`, default `False` | If `True`, suppresses fitting-related plot generation entirely. |
| `plot_x_units` | `str`, default `'Hz'` | Units used for the frequency axis on the fitted plot. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIRes import ExpZIRes

exp = ExpZIRes('resSpec', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q0',
  frequencies=np.linspace(4.0e9, 4.2e9, 1001), is_trough=True
  fit_type = "Full", update=True)
lab.run_single(exp, disable_ZI_logging=True)
```

#### Analysis, Fitting and Outputs

After the sweep completes, `_post_process` retrieves the dataset for the
qubit, confirms it is 1D, and computes:

- `data_x` — swept frequency values
- `data_i`, `data_q` — the I and Q components (selected via `iq_indices`)
- `data_y` — the IQ magnitude, `sqrt(I² + Q²)`

The fit performed depends on `fit_type`:

- **`'Default'`** — Fits a Lorentzian (`DFitPeakLorentzian`) to the squared IQ
  magnitude vs. frequency, treating the resonance as a dip if `is_trough` is
  `True`. Extracts `centre`, `width`, `amplitude`, and `offset`. If
  `update_qubit_params` is `True`, the qubit's `ReadoutFrequency` is set to
  the fitted centre.

- **`'Fano'`** — Fits a Fano resonance lineshape (`DFitFanoResonance`) to the
  squared IQ magnitude vs. frequency (dip only). Extracts `xMinimum` (used as
  the resonant frequency), `width`, `amplitude`, `offset`, and `FanoFac`
  (asymmetry parameter). If `update_qubit_params` is `True`, the qubit's
  `ReadoutFrequency` is set to `xMinimum`.

- **`'Full'`** — Performs a full circle fit on the complex I/Q data
  (`ResonatorPowerSweep.single_circlefit`) to extract the resonant frequency
  and internal/coupled/loaded quality factors. The probe power (in dBm)
  passed to the fit is computed from the qubit's `ReadoutLineAttenuation_dB`,
  `ReadoutPower`, and `ReadoutAmplitude` if attenuation is set on the qubit,
  otherwise a default of `-100 dBm` is used. If the fit succeeds and
  `update_qubit_params` is `True`, the qubit's `ReadoutFrequency`,
  `ReadoutQi`, `ReadoutQc`, and `ReadoutQl` are updated; if the fit fails, a
  warning is printed and the qubit is left unchanged.

For any fit type, if `param_freq`/`param_width`/`param_amplitude`/
`param_offset`/`param_fano` were supplied, their `.Value` is set to the
corresponding fitted quantity where applicable.

##### Outputs

- **Plot**: Unless `dont_plot` is `True`, a fitted plot is generated and
  saved to `fitted_plot.png` in the experiment's file path. It is displayed
  interactively unless `dont_show_plot` is `True`, in which case it is closed
  after saving.
- **Fit data**: The raw fitted-curve data is saved to `fitted_data.npy` in
  the experiment's file path (stored as a dict, e.g. `{'squared_amplitude': ...}`
  for `'Default'`/`'Fano'`, or `{'real': ..., 'imag': ...}` for `'Full'`).
- **Fallback**: If no fit result is produced (e.g. `'Full'` fit fails and
  returns no dictionary), and `dont_plot` is `False`, a simple plot of
  `|S21|` vs. frequency is shown without any fit overlay.

___

### ExpZIResPowerSweep

`class ExpZIResPowerSweep(ExpZIqubit)`

#### Description

`ExpZIResPowerSweep` performs a 2D resonator spectroscopy power sweep on a
single qubit's readout resonator, using the Zurich Instruments LabOne Q
`resonator_spectroscopy` experiment. For each readout amplitude in a swept
range, the full resonator frequency response is measured. The IQ magnitude
is background-subtracted and plotted as a colour map of frequency vs.
readout amplitude, with a Lorentzian fit to each amplitude slice overlaid to
trace how the resonance frequency shifts with readout power (e.g. to
identify the onset of nonlinear/bifurcation behaviour).

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and its `ReadoutAmplitude` property. |
| `qubit_id` | `str` | The ID of the single qubit whose resonator is being measured. Must be a plain string, not a list. |
| `frequencies` | array-like | The readout frequencies to sweep at each readout amplitude. Passed through to the underlying `resonator_spectroscopy` experiment. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `amplitude_range` | array-like, default `np.linspace(0.001, 1, 20)` | The readout amplitude values to sweep, applied to the qubit's `ReadoutAmplitude` property. |
| `dont_show_plot` | `bool`, default `False` | If `True`, the fitted plot is saved and closed rather than displayed. |
| `is_trough` | `bool`, default `True` | Whether the resonance appears as a dip (`True`) rather than a peak (`False`) in each amplitude slice, used by the per-slice Lorentzian fit. |
| `dont_plot` | `bool`, default `False` | If `True`, suppresses generation of the colour-map plot entirely. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIResPowerSweep import ExpZIResPowerSweep

exp = ExpZIResPowerSweep('res_power_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q0', 
  frequencies=np.linspace(4.0e9, 4.2e9, 1001))
lab.run_single(exp, disable_ZI_logging=True)
```

#### Analysis, Fitting and Outputs

##### Sweep

`_run` sweeps the qubit's `ReadoutAmplitude` property over `amplitude_range`
(via a `VariablePropertyTransient`) as the outer loop, with the underlying
`resonator_spectroscopy` experiment sweeping `frequencies` as the inner loop
— producing a 2D dataset of IQ response vs. (amplitude, frequency).

##### Fitting

`_post_process` retrieves the dataset and computes the IQ magnitude,
`sqrt(I² + Q²)`, as a 2D array indexed by amplitude and frequency. For each
amplitude slice, a Lorentzian (`DFitPeakLorentzian`) is fit to the magnitude
vs. frequency trace (treated as a dip if `is_trough` is `True`), and the
fitted centre frequency is recorded. This produces `res_freqs`, an array of
one fitted resonance frequency per swept amplitude value, stored internally
as `fitted_data['raw_fit_freqs']`. No qubit parameters are updated and no
`.npy` file of the fit data is written by this class.

##### Plot

Unless `dont_plot` is `True`, a colour-map plot is generated via the static
`plot_fitted_results` method and saved to `fitted_plot.png` in the
experiment's file path. It is displayed interactively unless
`dont_show_plot` is `True`, in which case it is closed after saving.

##### `plot_fitted_results(ax, hal_QPU, qubit_id, freq_vals, ampl_vals, ampl, fitted_data)`

Static helper used to render the power-sweep result onto a given axis:

- Subtracts the per-amplitude mean (background) from the IQ magnitude array
  so the resonance feature stands out against a flat background.
- Renders the background-subtracted magnitude as a colour map
  (`ax.pcolor`) with frequency on the x-axis and readout amplitude on the
  y-axis.
- Overlays the per-amplitude fitted centre frequencies
  (`fitted_data['raw_fit_freqs']`) as white markers, tracing the resonance
  frequency as a function of readout amplitude.
- Sets the axis title to the qubit ID and the qubit's current
  `ReadoutPower` (in dBm), and labels the axes as frequency (Hz) and
  readout amplitude.

___

### ExpZIResFluxSweep

`class ExpZIResFluxSweep(ExpZIqubit)`

#### Description

`ExpZIResFluxSweep` performs a 2D resonator spectroscopy flux sweep on a
single qubit's readout resonator, using the Zurich Instruments LabOne Q
`resonator_spectroscopy` experiment. For each DC flux bias in a swept range,
the full resonator frequency response is measured. A Lorentzian is fit to
each flux slice to trace the resonance frequency vs. flux, a smoothing
spline is fit through that trace, and the flux bias corresponding to the
frequency maximum (the flux "sweet spot", typically where the resonator is
first-order insensitive to flux noise) is located and reported.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and its `FluxDC` property. |
| `qubit_id` | `str` | The ID of the single qubit whose resonator is being measured. Must be a plain string, not a list. |
| `frequencies` | array-like | The readout frequencies to sweep at each flux bias. Passed through to the underlying `resonator_spectroscopy` experiment. |
| `flux_range` | array-like | The DC flux bias values to sweep, applied to the qubit's `FluxDC` property. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `update_qubit_params` | `bool`, default `True` | Stored on the object but currently not used to automatically write any fitted result back onto the qubit — see [`update_qubit()`](#update_qubit) below for the manual mechanism. |
| `dont_show_plot` | `bool`, default `False` | If `True`, the fitted plot is saved and closed rather than displayed. |
| `is_trough` | `bool`, default `True` | Whether the resonance appears as a dip (`True`) rather than a peak (`False`) in each flux slice, used by the per-slice Lorentzian fit. |
| `dont_plot` | `bool`, default `False` | If `True`, suppresses generation of the colour-map plot entirely. |
| `plot_x_units` | `str`, default `'Hz'` | Stored on the object but currently not applied to the generated plot. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`.

Note: `_run` asserts that no external `sweep_vars` are supplied — the
frequency and flux ranges must be fixed at construction time.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIResFluxSweep import ExpZIResFluxSweep

exp = ExpZIResFluxSweep('resFluxSweep', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q0', 
  frequencies=np.linspace(4.0e9, 4.2e9, 1001), 
  flux_range=np.linspace(-1, 1, 20))
lab.run_single(exp, disable_ZI_logging=True)
```

#### Analysis, Fitting and Outputs

##### Sweep

`_run` sweeps the qubit's `FluxDC` property over `flux_range` (via a
`VariablePropertyTransient`) as the outer loop, with the underlying
`resonator_spectroscopy` experiment sweeping `frequencies` as the inner loop
— producing a 2D dataset of IQ response vs. (flux, frequency).

##### Fitting

`_post_process` retrieves the dataset and computes the IQ magnitude,
`sqrt(I² + Q²)`, as a 2D array indexed by flux and frequency. For each flux
slice, a Lorentzian (`DFitPeakLorentzian`) is fit to the magnitude vs.
frequency trace (treated as a dip if `is_trough` is `True`), giving one
fitted resonance frequency per flux value (`raw_fit_freqs`).

A smoothing spline (`scipy.interpolate.UnivariateSpline`, smoothing factor
`0.5`) is then fit through the resonance-frequency-vs-flux trace (frequency
values are rescaled by a power-of-ten normalisation factor for numerical
stability, and the flux axis is reversed first if it runs in decreasing
order). `scipy.optimize.minimize_scalar` locates the flux value that
maximises the spline — the flux "sweet spot" — over the bounds of
`flux_range`.

##### Outputs

- **Fit data**: A dictionary is always saved to `fitted_data.npy` in the
  experiment's file path (regardless of `dont_plot`), containing:
  - `raw_fit_freqs` — the per-flux fitted resonance frequencies.
  - `smoothed_fit_freqs` — the smoothing spline evaluated at the original
    flux values.
  - `sweet_freq_flux` — a two-element array `[sweet_freq, opt_flux]` giving
    the frequency and flux bias at the located sweet spot.
- **Plot**: Unless `dont_plot` is `True`, a colour-map plot is generated via
  the static `plot_fitted_results` method and saved to `fitted_plot.png` in
  the experiment's file path. It is displayed interactively unless
  `dont_show_plot` is `True`, in which case it is closed after saving.
- **Internal state**: The located optimal flux value is stored on the
  instance (`self._opt_flux_val`) for later use by `update_qubit()`.

##### `plot_fitted_results(ax, qubit_id, freq_vals, flux_vals, ampl, fitted_data)`

Static helper used to render the flux-sweep result onto a given axis:

- Renders the raw IQ magnitude as a colour map (`ax.pcolor`) with frequency
  on the x-axis and flux on the y-axis.
- Overlays the smoothed spline fit as a white line and the raw per-flux
  fitted centre frequencies as white markers.
- Marks the located sweet spot with a red marker.
- Sets the axis title to the qubit ID and the sweet-spot frequency
  (in GHz) and flux (in V), and labels the axes as frequency (Hz) and
  flux (V).

##### `update_qubit()`

Public method to manually commit the fit result to the qubit object. Asserts
that an experiment has already been run (i.e. `self._opt_flux_val` is not
`None`), sets the qubit's `FluxDC` to the located sweet-spot flux value, and
then clears the stored value. This is **not** called automatically as part
of `_post_process` — it must be invoked explicitly after running the
experiment. A `TODO` in the source notes that narrowing `flux_range` down to
around the sweet spot on subsequent runs is a planned but not yet
implemented feature.

___

### ExpZIQubitSpec

`class ExpZIQubitSpec(ExpZIqubit)`

#### Description

`ExpZIQubitSpec` runs a qubit spectroscopy experiment on a single qubit
using the Zurich Instruments LabOne Q `qubit_spectroscopy` experiment. It
sweeps the qubit drive frequency, acquires the I/Q response, and fits the
resulting lineshape to a Lorentzian to extract the qubit's ground-to-excited
(GE) transition frequency, which can optionally be written back onto the
qubit object.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and (optionally) write the fitted frequency back to it. |
| `qubit_id` | `str` | The ID of the single qubit being measured. Must be a plain string, not a list. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `update_qubit_params` | `bool`, default `True` | If `True`, writes the fitted centre frequency back onto the qubit object's `DriveGE` property. |
| `dont_show_plot` | `bool`, default `False` | If `True`, the fitted plot is saved but not displayed. |
| `iq_indices` | `list`, default `[0, 1]` | Column indices in the retrieved data array corresponding to the I and Q components respectively. |
| `is_trough` | `bool`, default `False` | Whether the resonance appears as a dip (`True`) rather than a peak (`False`) in the response. |
| `dont_plot` | `bool`, default `False` | If `True`, suppresses plot generation during fitting. |
| `plot_x_units` | `str`, default `'Hz'` | Units used for the frequency axis on the fitted plot. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIQubitSpec import ExpZIQubitSpec

exp = ExpZIQubitSpec('qubitSpec', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q0', 
  frequencies=np.linspace(4.0e9, 4.2e9, 201), is_trough=True, update=True)
lab.run_single(exp, disable_ZI_logging=True)
```

#### Analysis, Fitting and Outputs

After the sweep completes, `_post_process` retrieves the dataset for the
qubit, confirms it is 1D, and computes:

- `data_x` — swept drive frequency values
- `data_y` — the IQ magnitude, `sqrt(I² + Q²)`, selected via `iq_indices`

A Lorentzian (`DFitPeakLorentzian`) is fit to the squared IQ magnitude vs.
frequency, treating the resonance as a dip if `is_trough` is `True`. The
fitted centre frequency, width, amplitude and offset are extracted from the
result. If `update_qubit_params` is `True`, the qubit's `DriveGE` property
is set to the fitted centre frequency. Unlike `ExpZIRes`, there are no
`param_*` arguments here to redirect individual fit results to external
parameter objects.

##### Outputs

- **Plot**: Unless `dont_plot` is `True`, the fitted plot is saved to
  `fitted_plot.png` in the experiment's file path, and shown interactively
  unless `dont_show_plot` is `True` (in which case it is neither displayed
  nor explicitly closed).
- **Fit data**: The fitted curve data is always saved to `fitted_data.npy`
  in the experiment's file path, stored as `{'squared_amplitude': ...}`.

 ___
  
### ExpZIQubitFluxSweep

`class ExpZIQubitFluxSweep`

#### Description

`ExpZIQubitFluxSweep` orchestrates a combined qubit + resonator spectroscopy
flux sweep across one or more qubits. Unlike the other `ExpZI*` classes, it
is **not** an `ExpZIqubit` subclass — it is a standalone driver that, at
each point in a shared DC flux sweep, runs a resonator spectroscopy
sub-experiment (`ExpZIRes`) and a qubit spectroscopy sub-experiment (base
`ExpZIqubit` with `qubit_spectroscopy`) for every requested qubit, then
assembles overview, per-qubit flux-spectroscopy, and (for multiple qubits)
comparison plots from the accumulated data.

The flux itself is only physically applied to a single qubit's flux line
(via `flux_var`), but the resonator/qubit spectroscopy of every qubit in
`qubit_ids` is re-measured at each flux point — e.g. to look at how a
neighbouring qubit's spectrum is affected by another qubit's flux bias
(crosstalk), alongside the flux-swept qubit's own spectroscopy.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name used to group the sweep's sub-experiments (`lab.group_open`/`group_close`). |
| `expt_config` | — | Experiment configuration object passed through to each sub-experiment. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and its properties. |
| `qubit_ids` | `str` or `list[str]` | The qubit(s) to measure at each flux point. A single string is automatically wrapped into a one-element list (along with `qubit_frequencies` and `res_frequencies`). |
| `qubit_frequencies` | array-like or `list[array-like]` | Drive frequencies to sweep for each qubit's qubit-spectroscopy measurement. Must have one entry per `qubit_ids` (after normalisation). |
| `res_frequencies` | array-like or `list[array-like]` | Readout frequencies to sweep for each qubit's resonator-spectroscopy measurement. Must have one entry per `qubit_ids`. |
| `flux_range` | array-like or `None` | The DC flux values to sweep. |
| `flux_var` | — | A flux-bias `VariableProperty` (e.g. `stz.VariableProperty('fluxLineQ0', lab, lab.HAL('Q0'), 'FluxDC')`) that is physically swept. Must control a `'FluxDC'` property, and must correspond to one of the qubits in `qubit_ids`. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `update_qubit_params` | `bool`, default `True` | Passed as `update=self._update_qubit` to each qubit-spectroscopy sub-experiment. Also controls whether each qubit's `ReadoutFrequency` is restored to its pre-sweep value once the whole sweep finishes. Note that the `ExpZIRes` resonator-spectroscopy sub-experiments are always run with their own `update_qubit_params=True` hardcoded, independent of this setting — see [`run()`](#runlab) step 5 for how the final readout frequency is reconciled. |
| `plot_fitted_res_freqs` | `bool`, default `True` | If `True`, `_plot_overview` overlays the per-flux fitted readout frequencies on the resonator-spectroscopy panel. |
| `dont_show_plot` | `bool`, default `False` | If `True`, each of this class's own summary figures (overview, flux spec, comparison) is closed immediately after saving instead of being left open for display. |
| `is_trough` | `bool`, default `True` | Passed to `ExpZIRes` as `is_trough` for the per-flux-point resonator fits. |
| `res_fit_type` | `str`, default `'Full'` | Passed to `ExpZIRes` as `fit_type`. Must be one of `'Default'`, `'Fano'`, or `'Full'`. |
| `dont_plot` | `bool`, default `False` | Passed to `ExpZIRes` as `dont_plot`, and used to compute `ZI_plot=not dont_plot` for the qubit-spectroscopy sub-experiment. **Does not** suppress this class's own overview/flux-spec/comparison plots, which are always generated. |
| `enable_ZI_log_messages` | `bool`, default `False` | Controls `disable_ZI_logging` passed to `lab.run_single()` for every sub-experiment. |
| `print_file_path` | `bool`, default `False` | If `True`, prints the output directory of the first qubit's data at the end of `run()`. |
| `measurement_averages` | `int`/`float`/`list`, default `None` | Number of repetitions to use per qubit. A single value is broadcast to all qubits; a list must match the length of `qubit_ids`. If set, applied via the acquisition HAL before each qubit's resonator-spectroscopy sub-experiment at each flux point. |
| `acquisition_hal` | `str`, default `'ZIacq'` | Name of the acquisition HAL used to set `NumRepetitions` when `measurement_averages` is supplied. |

#### Example snippet
Sweep flux and measure flux on a single qubit:
```python
from sqdtoolz.Experiments.Experimental.ExpZIQubitFluxSweep import ExpZIQubitFluxSweep
import sqdtoolz as stz

stz.VariableProperty(f'QfluxLine_Q1', lab, lab.HAL('Q1'), 'FluxDC')

exp = ExpZIQubitFluxSweep('qubitFluxSweep', lab.CONFIG('ZI'), 
  lab.HAL('QPU'), 'Q1', 
  qubit_frequencies=np.linspace(4.2e9, 4.6e9, 1001), 
  res_frequencies=np.linspace(6e9, 6.2e9, 1001),
  flux_range=np.linspace(-0.35, -0.22, 201), 
  flux_var=lab.VAR('QfluxLine_Q1'))
exp.run(lab)
```
Sweep flux on a single qubit (here, Q1), but measure qubit spectroscopy on two qubits Q0 and Q1:
```python
exp = ExpZIQubitFluxSweep('multiQubitFluxSweep', lab.CONFIG('ZI'), 
  lab.HAL('QPU'), ['Q0', 'Q1'], 
  qubit_frequencies=[np.linspace(3.8e9, 4.2e9, 301)]*2, 
  res_frequencies=[np.linspace(6e9, 6.2e9, 301), np.linspace(7e9, 7.2e9, 301)],  
  flux_range=np.linspace(-0.8, -0.5, 101), flux_var=lab.VAR('QfluxLine_Q1'))
exp.run(lab)
```

#### Methods

##### `run(lab)`

Executes the full flux sweep and generates all output plots.

1. Records each qubit's current `ReadoutFrequency` for potential restoration
   later.
2. Opens a `lab` experiment group named `name`.
3. If `flux_range` is not `None`, iterates over every flux value (applied
   via `flux_var`). At each flux point, for every `(qubit_id, res_freqs,
   qubit_freqs)` triple:
   - Optionally updates the acquisition HAL's `NumRepetitions` (if
     `measurement_averages` was supplied) and pushes the configuration.
   - Runs an `ExpZIRes` resonator-spectroscopy sub-experiment over
     `res_freqs` (always with `update_qubit_params=True`, so the qubit's
     `ReadoutFrequency` is updated at every flux point regardless of the
     outer `update_qubit_params` setting) and records the resulting
     `ReadoutFrequency`.
   - Runs a base `ExpZIqubit` qubit-spectroscopy sub-experiment over
     `[qubit_freqs]`.
   - Keeps a reference to the most recently run sub-experiment object for
     each qubit (earlier flux points' sub-experiment objects are
     overwritten).
4. Closes the `lab` experiment group.
5. If `update_qubit_params` is `False`, resets every qubit's
   `ReadoutFrequency` back to the value recorded in step 1.
6. For each qubit, reloads its accumulated qubit-spectroscopy and
   resonator-spectroscopy datasets (via `FileIODirectory` on the last
   sub-experiment's `{qid}.h5` file) and background-subtracts each (per-flux
   row mean subtracted from the IQ magnitude) to produce
   `amplQ_corrected`/`amplR_corrected` 2D arrays (flux × frequency).
7. Generates `_plot_overview` and `_plot_qubit_flux_spec` for each qubit,
   and (if more than one qubit was measured) `_plot_multi_qubit_comparison`.
8. If `print_file_path` is `True`, prints the output directory path.

#### Outputs

For each qubit: `Overview_{qid}.png` and `QubitFluxSpec_{qid}.png`. If more
than one qubit is swept: `QubitSpecComparison.png`. All are saved in the
output directory associated with the qubit's sub-experiments, and (unless
`dont_show_plot` is `True`) left open for interactive display. This class
does not save any `.npy` fit-data file itself — any such saving is delegated
to the underlying `ExpZIRes` sub-experiments it runs.

___

### ExpZIQubitPowerSweep

`class ExpZIQubitPowerSweep(ExpZIqubit)`

#### Description

`ExpZIQubitPowerSweep` performs a 2D qubit spectroscopy power sweep on a
single qubit, using the Zurich Instruments LabOne Q `qubit_spectroscopy`
experiment. For each drive power in a swept range, the full qubit drive
frequency response is measured. Peaks in each power slice are detected, the
most prominent ("primary") peak per slice is tracked across powers, and the
result is plotted as a background-subtracted colour map of frequency vs.
drive power — useful for seeing how the qubit transition (and any secondary
spectral features, e.g. other transitions or sidebands) shifts or splits
with drive power.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and its `DrivePower`/`ReadoutFrequency` properties. |
| `qubit_id` | `str` | The ID of the single qubit being measured. Must be a plain string, not a list. |
| `frequencies` | array-like | The drive frequencies to sweep at each drive power. Passed through to the underlying `qubit_spectroscopy` experiment. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `drive_power_range` | array-like, default `np.linspace(-30, 10, 9)` | The drive power values (dBm) to sweep, applied to the qubit's `DrivePower` property. |
| `num_plotted_peaks` | `int`, default `3` | Number of most-prominent secondary peaks to display per power slice. This is the active default filter, since `min_peak_prominence` defaults to `None` (see [Analysis](#analysis-fitting-and-outputs) below). |
| `min_peak_prominence` | `float`, default `None` | Minimum peak prominence a secondary peak must have to be displayed. If set to a non-`None` value, this takes precedence over `num_plotted_peaks`. |
| `dont_show_plot` | `bool`, default `False` | If `True`, the plot is saved and closed rather than displayed. |
| `is_trough` | `bool`, default `False` | Whether spectral features appear as dips (`True`) rather than peaks (`False`) in each power slice; the signal is inverted before peak detection when `True`. |
| `dont_plot` | `bool`, default `False` | If `True`, suppresses generation of the colour-map plot entirely. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIQubitPowerSweep import ExpZIQubitPowerSweep

exp = ExpZIQubitPowerSweep('qubitPowerSweep', lab.CONFIG('ZI'), lab.HAL('QPU'), 
  'Q3', frequencies=np.linspace(4.1e9, 4.6e9, 101))
lab.run_single(exp, disable_ZI_logging=True)
```


#### Analysis, Fitting and Outputs

##### Sweep

`_run` sweeps the qubit's `DrivePower` property over `drive_power_range`
(via a `VariablePropertyTransient`) as the outer loop, with the underlying
`qubit_spectroscopy` experiment sweeping `frequencies` as the inner loop —
producing a 2D dataset of IQ response vs. (power, frequency).

##### Peak detection

`_post_process` retrieves the dataset and computes the IQ magnitude,
`sqrt(I² + Q²)`, as a 2D array indexed by power and frequency. For each
power slice, `scipy.signal.find_peaks` (with `prominence=0`, `distance=5`)
is used to locate all local peaks (the signal is negated first if
`is_trough` is `True`, so dips are detected as peaks). For each slice:

- All detected peak frequencies and their properties (e.g. prominences) are
  recorded (`all_peak_freqs`, `all_peak_props`); slices with no detected
  peaks get an empty array and a `NaN` primary frequency.
- The peak with the highest prominence in that slice is recorded as the
  **primary peak** (`primary_peak_freqs`) — intended to track the main
  qubit transition across the power sweep.

No qubit parameters are updated and no `.npy` file of the fit/peak data is
written by this class.

##### Plot

Unless `dont_plot` is `True`, a colour-map plot is generated via the static
`plot_fitted_results` method and saved to `fitted_plot.png` in the
experiment's file path. It is displayed interactively unless
`dont_show_plot` is `True`, in which case it is closed after saving.

##### `plot_fitted_results(ax, hal_QPU, qubit_id, freq_vals, pwr_vals, ampl, fitted_data, min_prominence=None, top_n=3)`

Static helper used to render the power-sweep result onto a given axis:

- Subtracts the per-power mean (background) from the IQ magnitude array so
  spectral features stand out against a flat background, and renders the
  result as a colour map (`ax.pcolor`) with frequency on the x-axis and
  drive power on the y-axis.
- For each power slice, splits the detected peaks into the primary peak and
  "secondary" peaks (everything else), then filters the secondary peaks to
  display: peaks with prominence `>= min_prominence` are kept if
  `min_prominence` is given; otherwise only the `top_n` most prominent
  secondary peaks are kept. Surviving secondary peaks are overlaid as small
  white markers.
- Overlays the primary peak frequency for every power slice with a valid
  (non-`NaN`) detection as larger red markers, tracing the main transition
  across the power sweep.
- Sets the axis title to the qubit ID and its current `ReadoutFrequency`
  (in GHz), and labels the axes as frequency (Hz) and qubit drive power
  (dBm).

___

### ExpZIRabi

`class ExpZIRabi(ExpZIqubit)`

#### Description

`ExpZIRabi` runs an amplitude Rabi experiment on one or more qubits using
the Zurich Instruments LabOne Q `amplitude_rabi` experiment. It sweeps drive
pulse amplitude, fits the resulting Rabi oscillation to a sinusoid, and
(optionally) derives and writes back the calibrated π ("X") and π/2 ("X/2")
drive amplitudes for the qubit's ge or ef transition.

Unlike the single-qubit `ExpZI*` classes documented previously, `ExpZIRabi`
accepts a list of qubit IDs and processes each one in turn within
`_post_process`.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and (optionally) write fitted amplitudes back to it. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to run the Rabi experiment on. |

##### Keyword arguments

`ExpZIRabi` itself only handles one keyword argument; everything else is
consumed by the base `ExpZIqubit` constructor.

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, each qubit's fitted plot is saved and closed rather than displayed. |

The following are popped by `ExpZIqubit.__init__` itself (not by
`ExpZIRabi`), and directly affect `ExpZIRabi._post_process` since it reads
the resulting attributes:

| Argument | Type / Default | Attribute | Description |
|---|---|---|---|
| `update` | `bool`, default `False` | `self._update_params` | Passed to the ZI workflow's `update` option (if it has one), and read by `ExpZIRabi._post_process` to decide whether to write the fitted π/π-2 drive amplitudes back to the qubit object. |
| `use_cal_traces` | `bool`, default `True` | `self._normalise_data` | Passed to the ZI workflow's `use_cal_traces` option (if it has one), and read by `ExpZIRabi._post_process` to decide whether to normalise the raw IQ data into state population using calibration traces. |
| `transition` | `str`, default `'ge'` | `self._transition` | Passed to the ZI workflow's `transition` option (if it has one), and read by `ExpZIRabi._post_process` to select which qubit amplitude properties (`DriveGEAmplitudeX(on2)` vs. `DriveEFAmplitudeX(on2)`) get updated and which calibration states are used for normalisation. |
| `ZI_plot` | `bool`, default `False` | `self._plot_ZI` | Controls the ZI workflow's own `close_figures` option (independent of `ExpZIRabi`'s own plotting/`dont_show_plot`). |
| `show_pulse_sheet` | `bool`, default `False` | `self._show_pulse_sheet` | Stored on the object but not referenced anywhere in the provided `ExpZIqubit`/`ExpZIRabi` code (pulse-sheet generation is instead controlled by the run-time `print_pulse_sheet` kwarg passed to `_run`/`_estimate_experiment_params`). |

Any other keyword argument whose name matches an attribute on the ZI
workflow's options object (e.g. `cal_states`) is applied to that option
directly. Anything left over is forwarded as-is into the
`amplitude_rabi` `experiment_workflow` call — this is how workflow-specific
parameters such as the drive amplitude sweep values are supplied, since
`ExpZIRabi` does not expose a dedicated amplitude-sweep argument itself.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIRabi import ExpZIRabi

exp = ExpZIRabi('rabi', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q3'], 
  amplitudes=[np.linspace(0, 1, 25)], update=True, ZI_plot=True)
lab.run_single(exp)
```

#### Analysis, Fitting and Outputs

For each qubit in `qubit_ids`, `_post_process` retrieves that qubit's
dataset and drive-amplitude sweep values (`data_x`), then fits a sinusoid
(`DFitSinusoid`) to the Rabi oscillation:

- **If `self._normalise_data` is `True`:** the corresponding calibration
  dataset (`{qubit_id}_calib`) is retrieved, and `DataIQNormalise` computes
  an IQ-to-population transform from the two calibration states identified
  by `self._transition`. The raw IQ data is normalised into population
  values (`data_y`) via this transform (which also plots the calibration IQ
  blobs onto a secondary axis), and the sinusoid is fit to `data_y` vs.
  drive amplitude.
- **Otherwise:** `data_y` is simply the raw IQ magnitude,
  `sqrt(I² + Q²)`, and the sinusoid is fit directly to that.

The fit result is repackaged as `dpkt['fit_data'] = {'amplitude': <fitted
curve>, 'amplitude_raw': data_y}`.

##### Updating qubit parameters

If `self._update_params` is `True`:

- If normalising, the calibrated π and π/2 drive amplitudes are computed
  from the fitted sinusoid's `phase` and `frequency`:
  `amp_X = (2·⌈phase/2π⌉·π − phase) / (2π·frequency)` and
  `amp_Xon2 = amp_X − 0.25/frequency`. These (plus the transition label) are
  added into `dpkt['fit_data']`.
- If not normalising, the amplitudes are taken directly from the fitted
  oscillation period: `amp_X = 0.5/frequency`, `amp_Xon2 = 0.25/frequency`.
- The qubit's amplitude properties are then set accordingly: `DriveGEAmplitudeX`
  / `DriveGEAmplitudeXon2` if `self._transition == 'ge'`, otherwise
  `DriveEFAmplitudeX` / `DriveEFAmplitudeXon2`.

##### Outputs

For each qubit:

- **Plot**: A figure is always generated (regardless of any `dont_plot`-style
  flag, which this class does not expose) via the static
  `plot_fitted_results` method — a two-panel figure (Rabi fit + calibration
  scatter) if `self._normalise_data` is `True`, otherwise a single-panel
  figure. It is saved to `fitted_plot_{qubit_id}.png` in the experiment's
  file path, and displayed interactively unless `dont_show_plot` is `True`,
  in which case it is closed after saving.
- **Fit data**: Always saved to `fitted_data_{qubit_id}.npy` in the
  experiment's file path, containing the fitted curve, the raw/normalised
  data, and (if `self._update_params` and `self._normalise_data` are both
  `True`) the computed `amp_X`, `amp_Xon2`, and `transition`.

##### `plot_fitted_results(ax, data_x, data_y, fitted_results, data_normalised)`

Static helper used to render the Rabi fit onto a given axis:

- Labels the x-axis `'Amplitude'`, and the y-axis as `'Normalised
  e-Population'` or `'Normalised f-Population'` (based on
  `fitted_results.get('transition', 'ge')`) if `data_normalised` is `True`,
  or `'|IQ|'` otherwise.
- Plots the raw/normalised data as black `x` markers and the fitted
  sinusoid as a red line.
- If present in `fitted_results`, draws vertical blue reference lines at the
  π/2 (`amp_Xon2`) and π (`amp_X`) drive amplitudes, labelled accordingly.

  ___

### ExpZIRamsey

`class ExpZIRamsey(ExpZIqubit)`

#### Description

`ExpZIRamsey` runs a Ramsey experiment on one or more qubits using the
Zurich Instruments LabOne Q `ramsey` experiment. It sweeps free-evolution
wait time (with an artificial detuning applied per qubit), fits the
resulting decaying oscillation ("Ramsey fringe") to a sinusoid to extract
the fringe frequency and `T2*`, and — unlike `ExpZIRabi` — does **not**
update the qubit automatically. Instead it records the fit results and
requires an explicit call to `update_qubits()` afterwards to commit a
corrected drive frequency and `T2*` back to each qubit.

Like `ExpZIRabi`, it accepts a list of qubit IDs and processes each one in
turn within `_post_process`.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and (via `update_qubits()`) write corrected values back to it. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to run the Ramsey experiment on. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, each qubit's fitted plot is saved and closed rather than displayed. |
| `detunings` | array-like, **required** | The artificial detuning (Hz) applied per qubit during the Ramsey sequence, one entry per `qubit_ids`. The constructor asserts `'detunings' in kwargs` with a descriptive error message if omitted. It is accessed directly as `kwargs['detunings']` (not popped), so it is also forwarded into `ExpZIqubit`/the ZI workflow. |
| `update` | — | **Not settable.** The constructor asserts that `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False` before calling `ExpZIqubit.__init__`. Qubit updates are only ever applied via the separate `update_qubits()` method, never automatically in `_post_process`. |

The remaining kwargs behave exactly as in `ExpZIqubit` (see `ExpZIRabi`'s
[documentation](#expzirabi) for the full breakdown of `use_cal_traces`, `transition`,
`ZI_plot`, `show_pulse_sheet`, and how unmatched kwargs are forwarded into
the `ramsey` `experiment_workflow` call).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIRamsey import ExpZIRamsey

exp = ExpZIRamsey('ramsey_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'], 
  delays=[np.linspace(0, 6e-6, 100)], detunings=[1e6], update=False)
lab.run_single(exp)
#
exp.update_qubits()
```

#### Analysis, Fitting and Outputs

`_post_process` first clears `self._fit_vals`, then for each qubit in
`qubit_ids`:

- Retrieves the dataset and wait-time sweep values (`data_x`).
- Fits a (decaying) sinusoid (`DFitSinusoid`) to the Ramsey fringe:
  - **If `self._normalise_data` is `True`:** normalises the raw IQ data into
    state population using the qubit's calibration dataset
    (`{qubit_id}_calib`) and `DataIQNormalise`, exactly as in `ExpZIRabi`.
  - **Otherwise:** fits directly to the raw IQ magnitude,
    `sqrt(I² + Q²)`.
  - Note: the axis labels passed into this intermediate fitting call
    (`'Drive Amplitude'`/`'IQ Amplitude'`) are leftover/incorrect for a
    Ramsey (wait-time) sweep, but since this call uses `dontplot=True` they
    are never rendered — the actual displayed plot uses the correct labels
    from `plot_fitted_results` (see below).
- Repackages the fit as `dpkt['fit_data'] = {'amplitude': <fitted curve>,
  'amplitude_raw': data_y, 'T2*': 1/decay_rate, 'frequency': <fitted fringe
  frequency>, 'transition': self._transition}`.
- Generates and saves a plot (two-panel if normalising, single-panel
  otherwise) to `fitted_plot_{qubit_id}.png`, shown unless `dont_show_plot`
  is `True`.
- Saves `dpkt['fit_data']` to `fitted_data_{qubit_id}.npy`.
- Appends `{'qubit_obj': <qubit>, 'Detuning': detunings[i], 'GE_frequency_fit':
  <fitted frequency>, 'T2star': 1/decay_rate}` to `self._fit_vals` for later
  use by `update_qubits()`. The dictionary key is always named
  `'GE_frequency_fit'` regardless of `self._transition` — a `TODO` in the
  source notes this should be generalised for the `ef` transition.

##### `plot_fitted_results(ax, data_x, data_y, q, fitted_results, data_normalised)`

Static helper used to render the Ramsey fit onto a given axis:

- Y-axis labelled `'Normalised e-Population'`/`'Normalised f-Population'`
  (based on `fitted_results.get('transition', 'ge')`) if `data_normalised`
  is `True`, or `'|IQ|'` otherwise.
- X-axis (wait time) is automatically rescaled to a sensible SI prefix via
  `Miscellaneous.get_metric_multiplier`, and labelled `'Wait Times
  ({prefix}s)'`.
- Plots the raw/normalised data as black `x` markers and the fitted curve
  as a red line.
- Titles the axis with the qubit ID, transition, and fitted `T2*`
  (nicely unit-formatted via `Miscellaneous.get_units`).

##### `update_qubits(assume_detuned_above=True, t2_only=False)`

Public method that must be called explicitly after running the experiment
to commit the Ramsey fit results to each qubit (asserts `self._fit_vals` is
non-empty). It consumes `self._fit_vals` one entry at a time:

- **Unless `t2_only` is `True`**, corrects the qubit's drive frequency
  (`DriveGE` or `DriveEF`, based on `self._transition`) by adding
  `Detuning − GE_frequency_fit` (if `assume_detuned_above`) or `Detuning +
  GE_frequency_fit` (otherwise) — the sign ambiguity inherent in a Ramsey
  fringe fit means the caller must indicate which side of the transition the
  applied detuning was on. Note that after this, **both** `DriveGE` and
  `DriveEF` are re-assigned via `float(...)` unconditionally — this doesn't
  change the value of whichever property wasn't targeted, but it does invoke
  both properties' setters every call, which may have side effects if those
  setters do more than just store a value.
- Always updates `T2GE_star` or `T2EF_star` (based on `self._transition`)
  to the fitted `T2star`, regardless of `t2_only`.

`self._transition` is a single value shared across the whole experiment, so
it is applied uniformly when updating every qubit in `self._fit_vals`, not
selected per-qubit.

___

### ExpZIT1

`class ExpZIT1(ExpZIqubit)`

#### Description

`ExpZIT1` runs a qubit energy-relaxation (`T1`) experiment on one or more
qubits using the Zurich Instruments LabOne Q `lifetime_measurement`
experiment. It sweeps wait time after excitation, fits the resulting decay
to an exponential to extract `T1`, and — like `ExpZIRamsey` — does **not**
update the qubit automatically; an explicit call to `update_qubits()` is
required afterwards to commit the fitted `T1` back to each qubit.

It accepts a list of qubit IDs and processes each one in turn within
`_post_process`.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and (via `update_qubits()`) write the fitted `T1` back to it. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to run the T1 experiment on. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, each qubit's fitted plot is saved and closed rather than displayed. |
| `expect_rise` | `bool`, default `False` | Passed to `DFitExponential` as `rise` — whether to fit a rising rather than decaying exponential. Only takes effect when `self._normalise_data` is `False`; when normalising, the fit is always called with `rise=False` regardless of this setting. |
| `update` | — | **Not settable.** As in `ExpZIRamsey`, the constructor asserts that `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False`. Qubit updates only happen via the separate `update_qubits()` method. |

The remaining kwargs behave exactly as in `ExpZIqubit` — see `ExpZIRabi`'s
documentation for the full breakdown of `use_cal_traces`, `transition`,
`ZI_plot`, `show_pulse_sheet`, and how unmatched kwargs are forwarded into
the `lifetime_measurement` `experiment_workflow` call. Unlike `ExpZIRamsey`,
there is no `detunings` requirement here.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIT1 import ExpZIT1

exp = ExpZIT1('T1_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q1', 'Q2'], update=False)
lab.run_single(exp)
```

#### Analysis, Fitting and Outputs

`_post_process` first clears `self._fit_vals`, then for each qubit in
`qubit_ids`:

- Retrieves the dataset and wait-time sweep values (`data_x`).
- Fits an exponential (`DFitExponential`) to the decay:
  - **If `self._normalise_data` is `True`:** normalises the raw IQ data into
    state population using `ExpZIqubit.normalise_qubit_data` on the qubit's
    calibration dataset (`{qubit_id}_calib`), and fits with `rise=False`
    (always treated as a decay).
  - **Otherwise:** fits directly to the raw IQ magnitude,
    `sqrt(I² + Q²)`, with `rise=self._expect_rise`.
- Repackages the fit as `dpkt['fit_data'] = {'amplitude': <fitted curve>,
  'amplitude_raw': data_y, 'T1': <fitted decay time>, 'qubit_name':
  qubit_dataset, 'transition': self._transition}`.
- Generates and saves a plot (two-panel if normalising, single-panel
  otherwise) via `plot_fitted_results`, to `fitted_plot_{qubit_id}.png`,
  shown unless `dont_show_plot` is `True`. In the non-normalised branch, the
  axis title set inside `plot_fitted_results` is immediately overwritten by
  a second, differently-formatted title (`"{qubit_id} T1: ...s"` instead of
  `"{qubit_id}: {transition}-$T_1=$...s"`) set right after the call.
- Saves `dpkt['fit_data']` to `fitted_data_{qubit_id}.npy`.
- Appends `{'qubit_obj': <qubit>, 'T1': <fitted decay time>}` to
  `self._fit_vals` for later use by `update_qubits()`.

##### `plot_fitted_results(ax, data_x, data_y, fitted_results, data_normalised)`

Static helper used to render the T1 fit onto a given axis:

- Y-axis labelled `'Normalised e-Population'`/`'Normalised f-Population'`
  (based on `fitted_results.get('transition', 'ge')`) if `data_normalised`
  is `True`, or `'|IQ|'` otherwise.
- X-axis (wait time) is automatically rescaled to a sensible SI prefix via
  `Miscellaneous.get_metric_multiplier`, and labelled `'Wait Times
  ({prefix}s)'`.
- Plots the raw/normalised data as black `x` markers and the fitted curve
  as a red line.
- Titles the axis using `fitted_results['qubit_name']`, the transition, and
  the fitted `T1` (unit-formatted via `Miscellaneous.get_units`). Unlike
  `ExpZIRamsey`'s equivalent method, the qubit name is read from
  `fitted_results` rather than passed as a separate argument.

##### `update_qubits()`

Public method that must be called explicitly after running the experiment
to commit the fitted `T1` to each qubit (asserts `self._fit_vals` is
non-empty). It consumes `self._fit_vals` one entry at a time, setting
`T1GE` or `T1EF` (based on `self._transition`) to the fitted `T1`. Unlike
`ExpZIRamsey.update_qubits()`, there is no frequency correction to apply and
no `assume_detuned_above`/`t2_only` arguments — this method takes none.

___

### ExpZIRabiRamseyT1

`class ExpZIRabiRamseyT1`

#### Description

`ExpZIRabiRamseyT1` is an orchestration class (not an `ExpZIqubit` subclass) that
runs a standard single-qubit time-domain characterisation sequence — amplitude
Rabi, a fast and a slow Ramsey, and $T_1$ — back-to-back on a single qubit, for
either the `ge` or `ef` transition, and assembles the results into one summary
figure. It is the class referenced as "Time domain" for both the ground-state
characterisation and the *ef* characterisation sections of the [table of
contents](#table-of-contents).

Internally it runs [`ExpZIRabi`](#expzirabi) (twice — once uncalibrated to
obtain calibration traces, once calibrated), two [`ExpZIRamsey`](#expziramsey)
experiments (a "fast" one with a larger detuning to pin down the frequency
quickly, and a "slow" one with a smaller detuning for a more precise $T_2^*$),
and [`ExpZIT1`](#expzit1) — calling each sub-experiment's `update_qubits()` (or
passing `update=`) as it goes, so by the end of `run()` the qubit's drive
frequency, $T_2^*$, and $T_1$ (for the selected transition) have all been
updated in place.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name used to group the sub-experiments (`lab.group_open`/`group_close`). |
| `expt_config` | — | Experiment configuration object passed through to each sub-experiment. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object. |
| `qubit_id` | `str` | The single qubit to characterise. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `states` | `str`, default `'ge'` | Which transition to characterise: `'ge'` or `'ef'`. Also accepted positionally as the 5th argument. |
| `qubit_spec_LO_power` | `float`, default `-20` | Stored but not directly referenced in `run()` — retained for parity with related tuneup classes. |
| `qubit_time_domain_LO_power` | `float`, default `10` | Set on the qubit's `DrivePower` property before running the Rabi/Ramsey/T1 sequence. |
| `ef_guess` | `float`, default `qubit.DriveEF` | Stored but not directly referenced in `run()` (the *ef* drive frequency actually used comes from whatever is already set on the qubit / from the Ramsey fits). |
| `res_is_trough` | `bool`, default `True` | Stored but not referenced in `run()` (no resonator spectroscopy is performed by this class). |
| `individual_plots` | `bool`, default `False` | If `True`, each sub-experiment's own per-experiment plot is shown live (`dont_show_plot=not individual_plots` is passed through to each sub-experiment). |
| `update_params_live` | `bool`, default `True` | Passed as `update=` to the Rabi sub-experiments, and gates whether the fast-Ramsey/T1 results are committed via their `update_qubits()` calls (the slow-Ramsey update is always called, but only takes effect via its own semantics). |
| `enable_ZI_log_messages` | `bool`, default `False` | Controls `disable_ZI_logging` (inverted) passed to `lab.run_single()` for every sub-experiment. |
| `ramsey_assume_detuned_above` | `bool`, default `True` | Passed as `assume_detuned_above` to the slow Ramsey's `update_qubits()` call. |
| `rabi_amplitudes` | array-like | The Rabi drive-amplitude sweep. Mutually exclusive with `rabi_points`. |
| `rabi_points` | `int`, default `30` | Number of points for a `linspace(0, 1, ...)` Rabi amplitude sweep, used only if `rabi_amplitudes` is not supplied. |
| `ramsey_fast_detuning` | `float`, default `2e6` | Artificial detuning (Hz) for the fast Ramsey. |
| `ramsey_fast_times` / `ramsey_fast_max` / `ramsey_fast_points` | array-like / `float` (default `2e-6`) / `int` (default `40`) | Either supply the full `ramsey_fast_times` array, or let it be built as `linspace(0, ramsey_fast_max, ramsey_fast_points)`. |
| `ramsey_slow_detuning` | `float`, default `0.125e6` | Artificial detuning (Hz) for the slow Ramsey. |
| `ramsey_slow_times` / `ramsey_slow_max` / `ramsey_slow_points` | array-like / `float` (default `60e-6`) / `int` (default `60`) | Either supply the full `ramsey_slow_times` array, or let it be built as `linspace(0, ramsey_slow_max, ramsey_slow_points)`. |
| `t1_times` / `t1_max` / `t1_points` | array-like / `float` (default `100e-6`) / `int` (default `40`) | Either supply the full `t1_times` array, or let it be built as `linspace(0, t1_max, t1_points)`. |

Any remaining keyword arguments are stored but not forwarded to the
sub-experiments (unlike most other `ExpZI*` classes, `ExpZIRabiRamseyT1` does
not accept arbitrary passthrough kwargs into `ExpZIqubit`).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIRabiRamseyT1 import ExpZIRabiRamseyT1

exp = ExpZIRabiRamseyT1('ge_char_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q0', states='ge',
  rabi_points=25, ramsey_fast_detuning=3e6, ramsey_slow_detuning=0.1e6, t1_max=150e-6)
exp.run(lab)
```

#### Methods

##### `run(lab)`

1. Opens a `lab` experiment group named `name`.
2. Sets `DrivePower` to `qubit_time_domain_LO_power` and, for the selected
   transition, sets the $X$/$X/2$ amplitudes to `1.0`/`0.5` as a starting point.
3. Runs an uncalibrated `ExpZIRabi` (with `use_cal_traces=False`) followed by a
   calibrated `ExpZIRabi` over `rabi_amplitudes`, updating the qubit's
   amplitudes if `update_params_live` is `True`, and plots the fitted Rabi
   oscillation.
4. Runs the fast `ExpZIRamsey` over `ramsey_fast_times`/`ramsey_fast_detuning`,
   plots it, and calls `exp.update_qubits()` to correct the drive frequency.
5. Runs the slow `ExpZIRamsey` over `ramsey_slow_times`/`ramsey_slow_detuning`,
   plots it, and calls `exp.update_qubits(assume_detuned_above=
   ramsey_assume_detuned_above)` to further refine the drive frequency and set
   $T_2^*$.
6. Runs `ExpZIT1` over `t1_times`, plots it, and calls `exp.update_qubits()` to
   set $T_1$.
7. Closes the `lab` experiment group.

#### Outputs

A single 3-row summary figure (Rabi on the top row; fast and slow Ramsey side
by side on the middle row; $T_1$ on the bottom row) is saved as
`Overview_{states}.png` in the parent directory of the last sub-experiment's
output folder, and left open for interactive display (this class has no
`dont_show_plot` option of its own — only the individual sub-experiment plots
are gated by `individual_plots`). No `.npy` fit-data file is written by this
class itself; each sub-experiment's own `fitted_data_{qubit_id}.npy` is
produced as usual.

___

### ExpZIDispersive

`class ExpZIDispersive(ExpZIqubit)`

#### Description

`ExpZIDispersive` runs a dispersive-shift experiment on one or more qubits
using the Zurich Instruments LabOne Q `dispersive_shift` experiment. For
each qubit it compares resonator spectroscopy taken with the qubit prepared
in the ground state vs. the excited state, extracts the dispersive shift
`χ` (chi) between the two resonance frequencies, and (optionally) updates
the qubit's readout frequency, `ChiGE`, and an estimated thermal photon
number.

Only the ground/excited (`'ge'`) state comparison is currently implemented
— see [Known issues](#known-issues).

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and (optionally) write fitted results back to it. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to run the dispersive-shift experiment on. Also stored as `self._qubit_datasets`. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | Read via `kwargs.get` (not popped — see [Known issues](#known-issues)) but never actually used to gate plotting in this class. |
| `iq_indices` | `list`, default `[0, 1]` | Column indices in the retrieved data arrays corresponding to the I and Q components respectively. |
| `is_trough` | `bool`, default `False` | Only used in an internal assertion tying it to `fit_type='Fano'` — see [Known issues](#known-issues). |
| `fit_type` | `str`, default `'Circlefit'` | Which method to use to locate each state's resonance: `'Circlefit'` (fits the complex resonator response) or `'Minimum'` (takes the frequency of minimum `|S21|` directly, no fit). |
| `dont_plot` | `bool`, default `False` | If `True`, suppresses generation of the comparison plot entirely. |
| `plot_x_units` | `str`, default `'Hz'` | Stored on the object but not referenced anywhere else in the class. |
| `states` | `str`, default `'ge'` | Read via `kwargs.get` (not popped, so also forwarded on — likely intentionally, as a genuine `dispersive_shift` workflow parameter). Only `'ge'` is actually handled by `_post_process`. |
| `chi` | — , default `None` | Popped into `self._chi`, but this attribute is never read again anywhere in `_post_process` — `chi` there is a separate local variable computed from the fit. Appears to be an unwired/placeholder argument. |
| `calc_thermal_photons` | `bool`, default `False` | If `True`, attempts to estimate and update the qubit's thermal photon occupation — see [Known issues](#known-issues) regarding a bug in the failure path. |
| `update` | `bool`, default `True` (subclass) / `False` (base class) | Read via `kwargs.get` (not popped). Intended to control whether fitted results are written back to the qubit — see [Known issues](#known-issues) for why the *effective* default ends up being `False`, not `True`. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see `ExpZIRabi`'s documentation for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIDispersive import ExpZIDispersive

exp = ExpZIDispersive('dispersive_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'],
  fit_type='Circlefit', calc_thermal_photons=True, update=True)
lab.run_single(exp)
```


#### Analysis, Fitting and Outputs

`_post_process` only executes its body when `self._states == 'ge'`; for any
other value it silently does nothing (see
[Known issues](#known-issues)). For each qubit:

- Retrieves two separate 1D datasets, `{qubit}_g` and `{qubit}_e` (resonator
  spectroscopy taken with the qubit in the ground and excited state
  respectively), and computes I, Q, and IQ magnitude for both.
- Uses the qubit's `ReadoutLineAttenuation_dB` directly as the probe power
  (in dBm) passed to the fit — note this is simpler than `ExpZIRes`'s
  `'Full'` fit, which also factors in `ReadoutPower` and `ReadoutAmplitude`.
- Locates each state's resonance frequency according to `fit_type`:
  - **`'Circlefit'`**: fits both datasets via
    `ResonatorPowerSweep.single_circlefit` (with `pass_fits=True`). If both
    fits succeed, `chi = (fr_e − fr_g)/2` and `target_f = fr_e + chi`
    (a readout frequency offset from the excited-state resonance to
    maximise ground/excited state contrast). If either fit fails, `chi = 0`
    and `target_f = None`, and a failure message is printed.
  - **`'Minimum'`**: takes the frequency of minimum `|S21|` in each raw
    trace directly (no fit) and computes `chi`/`target_f` the same way.
- **If `calc_thermal_photons` is `True`**: attempts to compute the
  resonator linewidth `kappa = 1/(Ql·ω_r)` from the qubit's `ReadoutQl` and
  `ReadoutFrequency`, and reads the qubit's `T2GE` (which must have been
  measured previously, e.g. via `ExpZIRamsey`). It then numerically solves
  for an equilibrium thermal photon number `n_th` via `scipy.optimize.fsolve`
  on `1/T2 − 4·χ²·n/κ·(n+1) = 0`. See
  [Known issues](#known-issues) regarding what happens if the lookup fails.
- **If `self._update_params` is truthy**: sets the qubit's `ReadoutFrequency`
  to `target_f` (if not `None`), `ChiGE` to `chi` (if both fits succeeded),
  and — if thermal photons were calculated — `ReadoutKappa` and
  `ThermalPhotonNum`.
- **If `dont_plot` is `False`**: plots the ground- and excited-state
  `|S21|` traces (vs. frequency in GHz) with fitted curves and resonance
  markers overlaid where available, titled with the fitted `χ_ge` (in MHz)
  if nonzero. See [Known issues](#known-issues) regarding plot display and
  output filenames.

This class does not save any `.npy` fit-data file.

#### Known issues

A number of things in the current implementation are worth being aware of:

- **Only the `'ge'` state comparison is implemented.** The `#TODO: pass
  states` comment and the hard `if self._states == 'ge':` guard mean any
  other `states` value results in `_post_process` doing nothing at all,
  silently.
- **`dont_show_plot` is read but never used.** It's fetched via
  `kwargs.get('dont_show_plot', False)` (not popped) but `_post_process`
  calls `fig.show()` unconditionally and never calls `plt.close(fig)` —
  unlike every other `ExpZI*` class, this flag has no effect here.
- **The vestigial `Fano` check.** The constructor still contains
  `assert self._is_trough or (not self._is_trough and not
  self._fit_type=='Fano'), ...` copied over from `ExpZIRes`, but the later
  assertion restricts `fit_type` to `['Circlefit', 'Minimum']` — so the
  `'Fano'` branch of the first assert can never actually be reached with a
  valid `fit_type`. It's dead code.
- **`update`'s effective default is `False`, not `True`.** The subclass
  reads `update` via `kwargs.get('update', True)` (not popped) and stores it
  in `self._update_params`, but `super().__init__()` runs afterwards and
  `ExpZIqubit.__init__` does its own `kwargs.pop('update', False)`, which
  overwrites `self._update_params` again. Since the key is only removed by
  the base class, if the caller never explicitly passes `update=...`, the
  base class's `pop` finds nothing and falls back to *its* default of
  `False` — silently overriding the subclass's intended default of `True`.
  Passing `update=` explicitly works as expected either way.
- **Undefined-variable crash if thermal-photon lookup fails.** In the
  `calc_thermal_photons` block, `Ql`/`omega_r`/`kappa`/`T2` are only
  assigned inside a `try` block; if that `try` raises (caught by a bare
  `except`), a warning is printed, but the subsequent
  `nThermal_from_T2star`/`fsolve` calls are **not** skipped — they still
  execute and reference `T2`/`kappa`, which raises a `NameError` instead of
  failing gracefully.
- **Resonance-frequency labels assume both fits succeeded.** The plot's
  data-series labels (`f"g ({g_dpkt['fr']*1e-9:.4f} GHz)"` etc.) are built
  unconditionally, before the `if e_dpkt and g_dpkt:` check used later for
  the overlay curves — so if either circle fit fails, this line raises
  immediately rather than degrading gracefully.
- **The output plot filename doesn't vary per qubit.** Every qubit's
  comparison plot is saved to the same fixed filename,
  `dispersive_shift_ge.png`, in `self._file_path` — when `qubit_ids`
  contains more than one qubit, each iteration overwrites the previous
  qubit's saved plot, leaving only the last qubit's figure on disk.
- **`self._chi`** (from the `chi` kwarg) and **`self._xUnits`** (from
  `plot_x_units`) are stored but never read again anywhere in the class.

___

### ExpZIDragScaling

`class ExpZIDragScaling(ExpZIqubit)`

#### Description

`ExpZIDragScaling` calibrates the DRAG (Derivative Removal by Adiabatic Gate)
quadrature-scaling factor $\beta$ for a single qubit's $X$ drive pulse, using
the Zurich Instruments LabOne Q `drag_q_scaling` experiment. For a sweep of
$\beta$ values, it measures three sequences intended to converge on the same
excited-state population when the DRAG correction is right (labelled `xx`,
`xy`, `xmy` internally, following the underlying LabOne Q workflow's own
sequence naming), fits a straight line to each vs. $\beta$, and locates the
$\beta$ at which the three lines are closest together (minimum spread) as the
optimal scaling. Optionally updates the qubit's `DriveGEPulse` with the fitted
$\beta$.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and (optionally) write the fitted $\beta$ back to it. |
| `qubit_ids` | `list[str]` | Must contain exactly one qubit ID (the constructor asserts `len(qubit_ids)==1`). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `q_scalings` | `list[array-like]`, default `[np.linspace(0.00, 0.05, 51)]` | The DRAG quadrature-scaling ($\beta$) values to sweep, wrapped in a one-element list (one qubit only) and forwarded to the `drag_q_scaling` workflow. |
| `dont_show_plot` | `bool`, default `False` | If `True`, the fitted plot is saved and closed rather than displayed. |
| `update` | `bool`, default `True` | If `True`, sets the qubit's `DriveGEPulse` to `{'function': 'drag', 'beta': <fitted beta>, 'sigma': 0.25}` after fitting. Also forwarded to `ExpZIqubit.__init__` as `update=`. |
| `num_fit_points` | `int`, default `501` | Number of points in the fine `beta` grid used when evaluating each linear fit for the minimum-spread search. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs). Note this class always normalises to the `'ge'` transition inside
`_post_process`, regardless of `transition`.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIDragScaling import ExpZIDragScaling

exp = ExpZIDragScaling('drag_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'],
  q_scalings=[np.linspace(-0.1, 0.1, 41)], update=True)
lab.run_single(exp)
```

#### Analysis, Fitting and Outputs

For the single qubit in `qubit_ids`, `_post_process` retrieves three datasets
(`{qubit}_xx`, `{qubit}_xy`, `{qubit}_xmy`) and, for each:

- Computes `data_y` either as normalised excited-state population (via
  `ExpZIqubit.normalise_qubit_data` on the `{qubit}_calib` dataset, if
  `self._normalise_data` is `True`) or as raw IQ magnitude, `sqrt(I²+Q²)`.
- Fits a straight line (`np.polyfit`, degree 1) to `data_y` vs. `beta`
  (`q_scalings`), evaluated on a fine grid of `num_fit_points` points.

The three fitted lines (`xx_fit`, `xy_fit`, `xmy_fit`) are then compared at
every point of the fine grid: the spread (`max − min` across the three lines)
is computed, and the $\beta$ value minimising that spread is taken as the
optimal DRAG scaling. If `update` is `True`, the qubit's `DriveGEPulse` is set
to a DRAG pulse dict using this $\beta$ (with a fixed `sigma=0.25`).

##### Outputs

- **Plot**: A figure showing the three raw traces (scatter) and their linear
  fits, with the located optimum marked, is always generated via the static
  `plot_fitted_results` method and saved to `fitted_plot_{qubit_id}.png` in
  the experiment's file path. It is displayed interactively unless
  `dont_show_plot` is `True`, in which case it is closed after saving.
- **Fit data**: This class does not save a `.npy` fit-data file; the fitted
  traces are only kept on the instance (`self._data`).

##### `plot_fitted_results(ax, data_x, data, data_normalised=True, qubit_name=None)`

Static helper used to render the DRAG scaling fit onto a given axis: scatters
each of the `xx`/`xy`/`xmy` traces against $\beta$ with its corresponding
linear fit overlaid, marks the located optimum with a black circle, labels the
y-axis according to `data_normalised`, and titles the axis with the qubit name
and fitted $\beta$. Returns the fitted optimal $\beta$ value.

___

### ExpZIBlobs

`class ExpZIBlobs(ExpZIqubit)`

#### Description

`ExpZIBlobs` is a diagnostic experiment that measures single-shot IQ "blobs"
(readout calibration clouds) for one or more qubits using the Zurich
Instruments LabOne Q `iq_blobs` experiment, and reports single-shot readout
fidelity from the resulting clouds via `DataIQDiscriminate`. It is purely
diagnostic — the constructor forbids `update=True` — but exposes helper
methods to compute per-qubit fidelities, an SNR estimate, and (optionally) to
push readout correction (confusion) matrices onto the qubit objects.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and (optionally) write correction matrices back to it. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to measure IQ blobs for. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, each qubit's blob/assignment-matrix plot is saved and closed rather than displayed. |
| `states` | `str`, default `'ge'` | Read (not popped, so also forwarded to the ZI workflow). Determines which states `optimal_fidelity()`/`get_correction_matrices()` operate over. |
| `update` | — | **Not settable.** The constructor asserts `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False` — this is a diagnostic-only experiment. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs forwarded to the `iq_blobs` workflow call).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIBlobs import ExpZIBlobs

exp = ExpZIBlobs('blobs_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'], states='gef')
lab.run_single(exp)
print(exp.get_fidelities())
```

#### Analysis, Fitting and Outputs

`_post_process` retrieves each qubit's `{qubit}_calib` dataset and constructs
a `DataIQDiscriminate` object from it (via
`DataIQDiscriminate.fromZIcalibFileIOReader`), storing them in
`self._leDIQDs`. For each qubit, the static `plot_fitted_results` method
renders the IQ scatter and the resulting assignment (confusion) matrix onto a
two-panel figure, titled with the average single-shot fidelity, saved to
`fitted_plot_{qubit_id}.png`. No `.npy` fit-data file is saved by this class.

##### `get_fidelities(average=True)`

Returns each qubit's average single-shot fidelity (`average=True`, the
default) or the full per-state fidelity array (`average=False`), read from
the stored `DataIQDiscriminate` objects. Requires the experiment to have been
run first.

##### `optimal_fidelity()`

Computes an SNR (in dB) for each qubit directly from the raw `{qubit}_calib`
data (ground/excited cloud separation over the combined I/Q standard
deviation, converted to a power SNR), storing the result in
`self._iq_blob_data[qubit]`. Only supports `'ge'`-type states (asserts `'f'
not in self._states`).

##### `plot_fitted_results(leDIQD, extra_title='')` *(static)*

Renders a two-panel figure — the raw IQ scatter (`leDIQD.plot_points`) and the
assignment matrix (`leDIQD.plot_assignment_matrix`) — titled with the average
fidelity, and returns the `Figure` object.

##### `get_correction_matrices(update=False)`

Returns the inverse assignment-probability matrix for each qubit (usable as a
readout correction/confusion matrix), and if `update` is `True`, also writes
each one onto the corresponding qubit's `CorrectionMatrix[self._states]`
dictionary entry.

___

### ExpZIActiveResetTuneup

`class ExpZIActiveResetTuneup()`

#### Description

`ExpZIActiveResetTuneup` is an orchestration class (not an `ExpZIqubit`
subclass) that automates the tuneup steps needed to enable active reset on
one or more qubits: (optionally) calibrating the $X/2$ gate via repeated
[`ExpZICalibX`](#expzicalibx) runs, measuring passive-reset readout fidelity
via IQ blobs, computing optimal integration kernels from time traces, and
finally re-measuring IQ blobs with active reset enabled.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name used to group the sub-experiments (`lab.group_open`/`group_close`). |
| `expt_config` | — | Experiment configuration object passed through to each sub-experiment. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object. |
| `qubit_ids` | `list[str]` | The qubit(s) to tune up active reset for. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | Stored but not directly referenced in `run()` (plotting is delegated entirely to the sub-experiments it runs). |
| `update_qubit_params` | `bool`, default `True` | Stored but not directly referenced in `run()` — qubit properties (`ResetTime`, `IntegrationKernelType`) are instead set unconditionally as part of the routine. |
| `reset_time` | `float`, default `0.1e-6` | The `ResetTime` applied to each qubit once optimal integration weights have been computed, ahead of the final active-reset IQ-blobs measurement. |
| `Xcalib_gates` | `int`, default `50` | Number of gate repetitions (`num_gates`) used in each [`ExpZICalibX`](#expzicalibx) call during the $X/2$-gate calibration step. |
| `states` | `str`, default `'ge'` | The states measured by the passive- and active-reset IQ-blobs sub-experiments. |
| `reset_repititions` | `int`, default `3` | Number of active-reset repetitions (`active_reset_repetitions`) passed to the final IQ-blobs sub-experiment. |
| `skip_gate_calibration` | `bool`, default `False` | If `True`, skips the $X/2$-gate calibration step entirely and proceeds straight to the readout-fidelity/integration-weight steps. |

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIActiveResetTuneup import ExpZIActiveResetTuneup

exp = ExpZIActiveResetTuneup('activeReset_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'],
  reset_time=0.15e-6, reset_repititions=4)
exp.run(lab)
```

#### Methods

##### `run(lab)`

1. Opens a `lab` experiment group named `name`.
2. **Unless `skip_gate_calibration` is `True`** (and asserting the
   acquisition's `AveragingMode` is not `"DISCRIMINATION"`/`"RAW"`): for each
   qubit, sets `ResetTime` to `max(5·T1GE, 200 μs)` and
   `IntegrationKernelType='default'`, then runs [`ExpZICalibX`](#expzicalibx)
   twice back-to-back to check for a sign/parity flip between runs (comparing
   the fitted correction factor), calling `update_qubits(reverse_parity=...)`
   accordingly, and finally re-runs with `3×Xcalib_gates` for a refined
   calibration.
3. Runs an `ExpZIqubit`-based `iq_blobs` experiment (with `ZI_plot=False`) over
   all `qubit_ids` to obtain passive-reset fidelities
   (`self._qubit_fidelities`), warning if any qubit's fidelity is below `0.8`.
4. Temporarily sets `NumRepetitions` to `2**14` and, for each qubit (after
   asserting `|ReadoutLO − ReadoutFrequency| < 500e6`), runs an
   `ExpZIqubit`-based `time_traces` experiment with `update=True` to compute
   optimal integration weights, then sets `ResetTime=reset_time` and
   `IntegrationKernelType='optimal'`. Restores the original `NumRepetitions`
   afterwards.
5. Runs a final `ExpZIqubit`-based `iq_blobs` experiment with
   `active_reset=True`, `active_reset_repetitions=reset_repititions`, and
   `active_reset_states=states`, to measure active-reset fidelity.
6. Closes the `lab` experiment group.

#### Outputs

All plots and fit data are produced by the sub-experiments it runs
(`ExpZICalibX`'s fitted plots, and each `ExpZIqubit`-based sub-experiment's
own ZI-generated outputs); `ExpZIActiveResetTuneup` itself does not save any
additional plot or `.npy` file.

___

### ExpZITWPATuneup

`class ExpZITWPATuneup(ExpZIqubit)`

#### Description

`ExpZITWPATuneup` sweeps a TWPA (traveling-wave parametric amplifier) pump's
frequency and power and, for one or more qubits, uses the LabOne Q
`iq_blobs` experiment to measure ground/excited-state IQ-blob separation at
each pump setting. It converts that separation into an SNR (in dB) per
qubit, sums the per-qubit SNR across all requested qubits, and (optionally)
updates the TWPA's `Frequency` and `Power` to the pump setting that
maximised the combined SNR.

The state comparison is hardcoded to ground/excited (`'ge'`).

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object, passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used by `ExpZIqubit` to look up each qubit object. |
| `hal_twpa` | — | The TWPA pump HAL object. Its `Frequency` and `Power` properties are what gets swept (via `VariablePropertyTransient`), and — if enabled — overwritten with the pump setting found to maximise SNR. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to measure IQ-blob SNR on at each pump point. Also stored as `self._qubit_ids`. Per-qubit SNR (in dB) is summed across all listed qubits to find a single joint-optimum pump setting. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | Popped; stored as `self._dont_show_plot`. If `True`, suppresses all plotting in `_post_process` — see [Known issues](#known-issues) regarding the side effect this has on updating the TWPA. |
| `plot_all_qubits` | `bool`, default `True` | Popped; stored as `self._plot_all_qubits`. If `True` and the sweep is a genuine 2D frequency/power sweep, also plots an individual SNR heatmap per qubit in addition to the combined heatmap. Has no effect on a 1D sweep. |
| `update_qubit_params` | `bool`, default `True` | Popped; stored as `self._update_qubit`. If `True`, after post-processing, sets `hal_twpa.Frequency`/`hal_twpa.Power` to the values held in `self._optimum_twpa_point` — see [Known issues](#known-issues) for a crash case this can trigger. |
| `twpa_freq_range` | array-like, default 20 points linearly spaced across `hal_twpa.Frequency ± 5 MHz` | Popped; stored as `self._twpa_freq_range`. The pump frequency sweep points. |
| `twpa_power_range` | array-like, default 10 points linearly spaced across `hal_twpa.Power ± 2.5` | Popped; stored as `self._twpa_power_range`. The pump power sweep points. |

`states` is always passed to `ExpZIqubit.__init__` as `"ge"` and is not
accepted as a keyword argument here — see
[Known issues](#known-issues) regarding what happens if a caller supplies
one anyway. Any other remaining keyword arguments are passed through to
`ExpZIqubit.__init__` (see `ExpZIRabi`'s documentation for how `ExpZIqubit`
itself handles `use_cal_traces`, `transition`, `ZI_plot`,
`show_pulse_sheet`, and unmatched kwargs).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZITWPATuneup import ExpZITWPATuneup

exp = ExpZITWPATuneup('TWPA_TuneUp', lab.CONFIG('ZI'), lab.HAL('QPU'), lab.HAL('mw_twpa'),
  ['Q2', 'Q0', 'Q1', 'Q3', 'Q4'], twpa_power_range=np.linspace(17, 20, 10))
lab.run_single(exp)
```

#### Analysis, Fitting and Outputs

`_run` requires `sweep_vars` to be empty — the pump sweep is instead defined
entirely by `twpa_freq_range`/`twpa_power_range` at construction time. It
wraps `hal_twpa.Frequency`/`Power` in `VariablePropertyTransient` objects and
runs the underlying `ExpZIqubit`/`iq_blobs` experiment over frequency
(outer) then power (inner).

`_post_process` runs the following for each qubit:

- Retrieves the `{qubit}_calib` dataset (IQ-blob calibration data collected
  at each pump frequency/power point for the ground- and excited-state
  preparations).
- Computes the mean I/Q position of the ground-state and excited-state
  clouds (averaged over repetitions), and the cloud separation
  `d = |Δ(I, Q)|` between them.
- Computes a noise estimate `sigma` as the average of the ground- and
  excited-cloud standard deviations (from the summed I/Q variances).
- Computes a voltage SNR `d / (2·sigma)`, squares it to a power SNR, floors
  any non-positive values to avoid `log(0)`, and converts to `snr_db`.

It then sums `snr_db` across all requested qubits into `snr_db_total` and
locates the pump setting(s) at its maximum via `np.where`. Depending on the
shape of the sweep:

- **2D sweep** (both frequency and power have more than one point): plots a
  combined SNR heatmap (frequency vs. power) with the optimum point marked,
  and — if `plot_all_qubits` is `True` — a grid of per-qubit SNR heatmaps.
  Sets `self._optimum_twpa_point['Frequency']`/`['Power']` from the located
  maximum.
- **1D sweep** (only frequency or only power varies): intended to plot SNR
  vs. the swept parameter for the combined total and each qubit — see
  [Known issues](#known-issues), as this branch currently cannot complete
  without raising an exception.

Finally, if `update_qubit_params` was `True`, `hal_twpa.Frequency` and
`hal_twpa.Power` are set from `self._optimum_twpa_point`.

This class does not save any `.npy` fit-data file.

___

### ExpZIT1SingleShot

`class ExpZIT1SingleShot(ExpZIqubit)`

#### Description

`ExpZIT1SingleShot` runs a qubit energy-relaxation (`T1`) measurement in
single-shot/discriminated mode on one or more qubits, using the Zurich
Instruments LabOne Q `lifetime_measurement` experiment forced into
`AveragingOrder='SingleShot'`, `AcquisitionMode='DISCRIMINATION'`. Rather than
fitting an exponential to an averaged decay (as [`ExpZIT1`](#expzit1) does),
it computes the per-time-point population of each measured state ($g$, $e$,
$f$) directly from the single-shot outcome counts, and plots all three
population traces vs. wait time. It is purely diagnostic — the constructor
forbids `update=True`.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to run the single-shot $T_1$ experiment on. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, each qubit's population plot is saved and closed rather than displayed. |
| `expect_rise` | `bool`, default `False` | Popped and stored (`self._expect_rise`) but not currently used — a `# TODO: fit T1 to f state` comment in `_post_process` notes that fitting is not yet implemented for this class. |
| `update` | — | **Not settable.** As in `ExpZIT1`, the constructor asserts `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False`. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs forwarded to the `lifetime_measurement` workflow call).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIT1SingleShot import ExpZIT1SingleShot

exp = ExpZIT1SingleShot('T1_singleshot_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'],
  delays=[np.linspace(0, 100e-6, 40)])
lab.run_single(exp)
```

#### Analysis, Fitting and Outputs

For each qubit, `_post_process` retrieves the discriminated single-shot
dataset and, for every wait-time point, bins the per-shot outcome (`0`, `1`,
or `2`, corresponding to $g$/$e$/$f$) into a population fraction via
`np.bincount`. It then plots all three population traces ($g$, $e$, $f$) vs.
wait time (with the time axis auto-scaled to a sensible SI prefix), titled
according to `self._transition` (`'Initialising E'` for `'ge'`, `'Initialising
F'` for `'ef'`).

##### Outputs

- **Plot**: Always generated and saved to `fitted_plot_{qubit_id}.png` in the
  experiment's file path. Displayed interactively unless `dont_show_plot` is
  `True`, in which case it is closed after saving.
- **Fit data**: No `.npy` file is saved and no $T_1$ value is fitted or
  extracted by this class — it is purely a visual diagnostic of the raw
  single-shot state populations (fitting $T_1$ from the $f$-state population
  is a noted but unimplemented `TODO`).

___

### ExpZIResOptimal

`class ExpZIResOptimal(ExpZIqubit)`

#### Description

`ExpZIResOptimal` sweeps the readout frequency and, for each of the qubit's
prepared states (`'ge'` or `'gef'`), measures the resonator response using the
Zurich Instruments LabOne Q `dispersive_shift` experiment. It plots the IQ
magnitude/phase and the pairwise state separation vs. frequency for every
pair of states, and — if `calc_single_shot_fidelities` is enabled — also
computes per-frequency single-shot readout fidelities (via
`DataIQDiscriminate`) for every state pairing plus the combined mean. Unlike
most `ExpZI*` classes, updates are **not** automatic: two separate
`update_qubits_by_*` methods must be called explicitly afterwards to commit
whichever frequency (by maximum IQ separation, or by maximum fidelity) is
desired.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and (via `update_qubits_by_*`) write the chosen frequency back to it. |
| `qubit_ids` | `list[str]` | Only the first qubit (`qubit_ids[0]`) is used — this experiment only supports one qubit at a time. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, the summary plot is saved and closed rather than displayed. |
| `states` | `str`, **required** | Which states to prepare and measure — `'ge'` or `'gef'`. The constructor asserts `'states' in kwargs`. |
| `calc_single_shot_fidelities` | `bool`, default `False` | If `True`, forces `states='gef'` (printing a notice if a different value was supplied), sets `do_analysis=False` on the ZI workflow (since the default ZI analysis doesn't support this mode), and runs the sweep in single-shot mode (`AveragingOrder='SingleShot'`) so that per-frequency single-shot fidelities can be computed. |
| `update` | — | **Not settable.** The constructor asserts `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False` — updates must go through `update_qubits_by_separation()`/`update_qubits_by_fidelity()`. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs forwarded to the `dispersive_shift` workflow call, most notably
`frequencies`).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIResOptimal import ExpZIResOptimal

exp = ExpZIResOptimal('resOptimal_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'],
  states='gef', frequencies=np.linspace(6.0e9, 6.05e9, 101), calc_single_shot_fidelities=True)
lab.run_single(exp)
exp.update_qubits_by_fidelity(state_fidelity='gef')
```

#### Analysis, Fitting and Outputs

`_post_process` retrieves one dataset per prepared state (`{qubit}_g`,
`{qubit}_e`, and — if `'gef'` — `{qubit}_f`) and, for each, computes the IQ
magnitude and (unwrapped) phase vs. frequency, plotted on a shared magnitude
axis with a twin phase axis. For every pairwise combination of states (`ge`
only for two states; `ge`, `ef`, `gf` — plus the summed `gef` — for three), it
computes the Euclidean IQ separation vs. frequency and marks the frequency of
maximum separation. If `calc_single_shot_fidelities` is `True`, it
additionally builds a `DataIQDiscriminate` per frequency point for each state
pairing (and for the full 3-state combination), computes the mean pairwise
fidelity at each frequency, plots per-state fidelity curves with their maxima
marked, and renders the best-fidelity IQ scatter/assignment-matrix for each
pairing. `self._readout_fidelity` is set to the last-plotted pairing's average
fidelity.

##### Outputs

- **Plot**: A single multi-panel summary figure — magnitude/phase, IQ
  separation, and (if `calc_single_shot_fidelities`) fidelity curves plus
  per-pairing blob/assignment-matrix panels — is always generated and saved
  to `fitted_plot_{qubit_id}.png`. Displayed interactively unless
  `dont_show_plot` is `True`.
- **Fit data**: `self._fit_data` stores `freqs`, `maxSepIndices` (and, if
  single-shot, `maxFidIndices` and `discriminators`) — kept in memory only, no
  `.npy` file is written.

##### `update_qubits_by_separation(transition='Total')`

Sets the qubit's `ReadoutFrequency` to the frequency of maximum IQ separation
for the requested `transition` (`'ge'`, `'ef'`, `'gf'`, or `'total'`), and
`FidelityReadout` to `self._readout_fidelity`. Requires the experiment to have
been run first.

##### `update_qubits_by_fidelity(state_fidelity='gef')`

Sets the qubit's `ReadoutFrequency` to the frequency of maximum single-shot
fidelity for the requested state combination (`'ge'`, `'ef'`, `'gf'`, or
`'gef'`), and `FidelityReadout` to `self._readout_fidelity`. Requires
`calc_single_shot_fidelities=True` to have been used when running.

##### `print_best_frequencies_by_separation()` / `print_best_frequencies_by_fidelity()`

Print the best frequency for each state pairing (by separation, or by
fidelity respectively) in human-readable units.

##### `plot_blobs(frequency)`

Plots the IQ scatter/assignment-matrix for the discriminator closest to the
given `frequency`. Requires `calc_single_shot_fidelities=True`.

___

### ExpZIResOptimalAmpSweepSS

`class ExpZIResOptimalAmpSweepSS(ExpZIqubit)`

#### Description

`ExpZIResOptimalAmpSweepSS` extends the idea behind
[`ExpZIResOptimal`](#expziresoptimal) with `calc_single_shot_fidelities=True`
into a 2D sweep: for every readout amplitude in a swept range, it re-measures
the full single-shot dispersive-shift response across frequency for the
`'g'`, `'e'`, and `'f'` states, then computes IQ separation and single-shot
fidelity as functions of *both* frequency and amplitude, producing 2D heatmaps
for each. This lets the optimal readout point be chosen jointly over
frequency and amplitude, rather than at a fixed amplitude.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and (via `update_qubits_by_*`) write the chosen frequency/amplitude back to it. |
| `qubit_ids` | `list[str]` | Must contain exactly one qubit (the constructor asserts `len(qubit_ids)==1`). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, the summary plot is saved and closed rather than displayed. |
| `amplitude_range` | array-like, default `np.linspace(0.01, 0.9, 10)` | The readout amplitude values to sweep, applied to the qubit's `ReadoutAmplitude` property (temporarily, via a `VariablePropertyTransient`; the amplitude is restored to its pre-experiment value in `_post_process`). |
| `update` | — | **Not settable.** The constructor asserts `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False` — updates must go through `update_qubits_by_separation()`/`update_qubits_by_fidelity()`. |

The `states` are hardcoded to `'gef'` internally (`self._states = 'gef'`) and
are not accepted as a keyword argument. Any remaining keyword arguments are
passed through to `ExpZIqubit.__init__` (see [`ExpZIRabi`](#expzirabi) for how
`ExpZIqubit` itself handles `use_cal_traces`, `transition`, `ZI_plot`,
`show_pulse_sheet`, and unmatched kwargs forwarded to the `dispersive_shift`
workflow call, most notably `frequencies`).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIResOptimalAmpSweepSS import ExpZIResOptimalAmpSweepSS

exp = ExpZIResOptimalAmpSweepSS('resOptimalAmpSweep_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'],
  frequencies=np.linspace(6.0e9, 6.05e9, 51), amplitude_range=np.linspace(0.05, 0.8, 8))
lab.run_single(exp)
exp.update_qubits_by_fidelity(state_fidelity='gef')
```

#### Analysis, Fitting and Outputs

`_run` sweeps the qubit's `ReadoutAmplitude` (via a `VariablePropertyTransient`)
over `amplitude_range` as the outer loop around the underlying single-shot
`dispersive_shift` sweep over frequency. `_post_process` then, for every
combination of states (`ge`, `ef`, `gf`, and the combined `gef`), computes:

- The mean-cloud IQ separation as a 2D array (amplitude × frequency), plotted
  as a heatmap with the point of maximum separation marked.
- A `DataIQDiscriminate` per (amplitude, frequency) point and the resulting
  mean fidelity, likewise plotted as a heatmap with its maximum marked; the
  best-fidelity IQ scatter and assignment matrix for each state pairing are
  also rendered.

##### Outputs

- **Plot**: A single large multi-panel figure (separation heatmaps, fidelity
  heatmaps, and per-pairing blob/assignment-matrix panels) is always
  generated and saved to `fitted_plot_{qubit_id}.png`. Displayed
  interactively unless `dont_show_plot` is `True`.
- **Fit data**: `self._fit_data` stores `freqs`, `amps`,
  `maxSepAmpIndices`/`maxSepFreqIndices`, `maxFidAmpIndices`/
  `maxFidFreqIndices`, and `discriminators` — kept in memory only, no `.npy`
  file is written.

##### `update_qubits_by_separation(transition='Total')` / `update_qubits_by_fidelity(state_fidelity='gef')`

As in [`ExpZIResOptimal`](#expziresoptimal), but set **both**
`ReadoutFrequency` and `ReadoutAmplitude` from the located 2D optimum (by
separation or by fidelity respectively), plus `FidelityReadout`.

##### `print_best_parameters_by_separation()` / `print_best_parameters_by_fidelity()`

Print the best (frequency, amplitude) pair for each state pairing (by
separation, or by fidelity respectively).

##### `plot_blobs(frequency, amplitude)`

Plots the IQ scatter/assignment-matrix for the discriminator closest to the
given `(frequency, amplitude)` point.

___

### ExpZICalibX

`class ExpZICalibX(ExpZIqubit)`

#### Description

`ExpZICalibX` calibrates the rotation angle of the qubit's $X$ or $X/2$ gate
by repeating it $n=1,2,\dots$ times (an "error amplification" sequence) and
fitting the resulting population oscillation to extract a correction factor
for the drive amplitude. It is the building block used elsewhere (e.g.
[`ExpZIActiveResetTuneup`](#expziactiveresettuneup)) to fine-tune single-qubit
gates. Updates are not automatic — `update_qubits()` must be called
afterwards.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and (via `update_qubits()`) write the correction factor back to it. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to calibrate. |
| `calib_denominator` | `int`, default `1` | Whether to calibrate the $X$ gate (`1`) or the $X/2$ gate (`2`). Must be `1` or `2`. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, each qubit's fitted plot is saved and closed rather than displayed. |
| `only_every_n` | `int`, default `1` | Only include every `n`-th gate-repetition count in the swept sequence (e.g. `2` skips every other count), to shorten the experiment. At least 4 surviving points are required — the constructor asserts this. |
| `num_gates` | `int`, default `20` | The maximum number of gate repetitions swept, i.e. the sequence sweeps `1, 2, ..., num_gates` repetitions of the selected gate (subject to `only_every_n`). |
| `expected_corr_sign` | `None`/`1`/`-1`, default `None` | If set, constrains the fitted correction percentage to be non-negative (`1`) or non-positive (`-1`), narrowing the fit's search bounds; `None` allows either sign. |
| `update` | — | **Not settable.** The constructor asserts `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False` — updates must go through `update_qubits()`. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZICalibX import ExpZICalibX

exp = ExpZICalibX('calibX_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'], 1, num_gates=30)
lab.run_single(exp)
exp.update_qubits()
```

#### Analysis, Fitting and Outputs

For each qubit, `_fit_single_qubit` normalises the raw IQ data into excited-
state population using the `{qubit}_calib` dataset, then fits the population
vs. gate-repetition-count `n` to a model function — $\cos((n-1)(1+c/100)\pi)$
(for the $X$ gate) or $\sin((n-1)(1+c/100)\pi/2)$ (for $X/2$), each multiplied
by an exponential decay envelope $e^{-(n-1)/(100d)}$ and offset by $0.5$ —
using a coarse grid search for an initial guess followed by
`scipy.optimize.curve_fit`. The fitted correction percentage `c` gives the
gate correction factor: `Gate_Corr_Fac = 1/(1+c/100)` (or its
$X$-gate-equivalent mirrored form if `(1+c/100) ≥ 1`). Basic goodness-of-fit
diagnostics are printed if a fitted parameter sits at its search bound, or if
$R^2 < 0.8$.

##### Outputs

- **Plot**: For each qubit, a fitted plot (population vs. gate count, with
  the fitted curve overlaid, titled with the fitted rotation angle in
  degrees) is always saved to `fitted_plot_{qubit_id}.png`. Displayed
  interactively unless `dont_show_plot` is `True`.
- **Fit data**: Always saved to `fitted_data_{qubit_id}.npy`, containing the
  fit parameters, their uncertainties, $R^2$, the fitted angle, and `n_vals`.
- Qubits whose fit raises an exception are recorded in `self._failed_qubits`
  and skipped by `update_qubits()`.

##### `plot_fitted_results(ax, data, qubit_name=None)` *(static)*

Renders a previously-saved fit dict (`data`, e.g. loaded from
`fitted_data_{qubit_id}.npy`) onto a given axis — raw population vs. gate
count with the fit overlaid, titled with the fitted rotation angle.

##### `update_qubits(reverse_parity=False)`

Commits the fitted correction factor to each qubit that had a successful fit:
multiplies `DriveGEAmplitudeXon2` (if `calib_denominator=2`) or
`DriveGEAmplitudeX` (if `calib_denominator=1`) by the correction factor (or by
`2 − Gate_Corr_Fac` if `reverse_parity` is `True`, to flip the correction's
sign when a sign ambiguity has been identified — see
[`ExpZIActiveResetTuneup`](#expziactiveresettuneup)'s two-run parity check).
Qubits in `self._failed_qubits` are skipped with a printed warning. Requires
the experiment to have been run first.

___

### ExpZIRandomisedBenchmarking

`class ExpZIRandomisedBenchmarking(ExpZIqubit)`

#### Description

`ExpZIRandomisedBenchmarking` runs standard single-qubit Clifford-equivalent
randomised benchmarking on one or more qubits, using the
`single_qubit_gates_sweep_chunking` LabOne Q workflow. Random gate sequences
of increasing length (drawn from the gate set $\{X, X/2, -X/2, Y, Y/2,
-Y/2\}$) are generated such that each sequence's final gate returns the qubit
to the excited state, multiple random trials are measured per sequence
length, and the decay of the resulting survival probability with sequence
length is fit (on a log scale) to extract an average error-per-gate, which can
be written back to the qubit's `Fidelity1QRB` property.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object and (optionally) write the fitted error rate back to it. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to benchmark; the same random gate sequences are applied to every qubit in the list. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | Popped and stored (`self._dont_show_plot`), but note `_post_process` always calls `fig.show()` regardless — see the source for the caveat that this flag is not currently wired up to suppress display. |
| `update` | `bool`, default `True` | If `True`, writes the fitted error-per-gate (as a percentage) to each qubit's `Fidelity1QRB` property. |
| `sequence_lengths` | `list[int]`, default `[3,4,5,6,7,8,9,10,11,12]` | The Clifford-equivalent sequence lengths to benchmark. |
| `num_trials` | `int`, default `5` | Number of independently-generated random sequences measured per sequence length. |
| `rb_seed` | `int`, default `88` | Seed for the `numpy` random generator used to draw gate sequences, for reproducibility. |
| `coordinate_system` | `str`, default `'RH'` | Must be `'LH'` or `'RH'` (left/right-handed); forwarded to the ZI workflow. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIRandomisedBenchmarking import ExpZIRandomisedBenchmarking

exp = ExpZIRandomisedBenchmarking('rb_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'],
  sequence_lengths=[4, 8, 16, 32, 64, 128], num_trials=8, update=True)
lab.run_single(exp)
```

#### Analysis, Fitting and Outputs

For each qubit, `_post_process` normalises the raw IQ data into excited-state
population (via `ExpZIqubit.normalise_qubit_data` on the `{qubit}_calib`
dataset), then, for each sequence length, discards trials whose population is
below `0.8` (as a crude outlier filter) and averages the remaining trials'
population to get a mean survival probability and its standard deviation.
The $z$-projection (`mean − 0.5`) is fit to an exponential decay in log-space
via `np.polyfit(seq_lens, log(zProj), deg=1)`, and the error-per-gate is
`exp(slope)`.

##### Outputs

- **Plot**: A two-panel figure — raw per-trial population vs. sequence length
  (with the mean and standard-deviation band overlaid) on the left, and the
  log-space linear fit (with fitted error-per-gate in the title) on the
  right — is always generated, shown, and saved as `Summary.png` in the
  experiment's file path.
- **Fit data**: No `.npy` file is saved by this class.
- If `update` is `True`, `Fidelity1QRB` is set to the fitted error-per-gate
  (as a percentage) for each qubit.

___

### ExpZIBenchmarkETH

`class ExpZIBenchmarkETH(ExpZIqubit)`

#### Description

`ExpZIBenchmarkETH` benchmarks single-qubit gate fidelity by running a fixed
set of short gate sequences (the "ETH-style" gate-set benchmark: identity,
single $X$/$Y$ (and half-)rotations, pairs of gates, and combinations
involving a virtual $Z/2$) and comparing the measured excited-state
population for each sequence against the population predicted by ideal gate
matrices. Unlike `ExpZIRandomisedBenchmarking`, it does not fit a single
error-per-gate number — it is a qualitative diagnostic that visualises
measured-vs-ideal population per sequence.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each qubit object. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The qubit(s) to benchmark; the same fixed gate sequences are applied to every qubit in the list. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, each qubit's bar-chart plot is saved and closed rather than displayed. |
| `extra_gate_seqs` | `list[list[str]]`, default `[]` | Additional gate sequences appended to the fixed built-in set of 21 sequences (identity, $X$, $\pm X/2$, $Y$, $\pm Y/2$, gate pairs, $Z/2$-containing sequences, and Hadamard-based sequences). |
| `coordinate_system` | `str`, default `'RH'` | Must be `'LH'` or `'RH'` (left/right-handed); forwarded to the ZI workflow. |
| `update` | — | **Not settable.** The constructor asserts `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False` — this is a diagnostic-only experiment. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIBenchmarkETH import ExpZIBenchmarkETH

exp = ExpZIBenchmarkETH('benchmarkETH_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'])
lab.run_single(exp)
```

#### Analysis, Fitting and Outputs

For each qubit, `_post_process` normalises the raw IQ data into excited-state
population (via `ExpZIqubit.normalise_qubit_data` on the `{qubit}_calib`
dataset), giving one measured population per sequence. For each sequence in
the fixed (plus any `extra_gate_seqs`) set, the ideal expected population is
computed by composing the corresponding ideal single-qubit rotation matrices
(via `QubitGatesBase.get_rotation_from_Pauli_Matrix`) and applying them to the
ground state.

##### Outputs

- **Plot**: For each qubit, a bar chart of measured population per sequence
  (bars) with the ideal predicted population overlaid as horizontal tick
  marks, is always generated and saved to `Benchmarks_{qubit_dataset}.png` in
  the experiment's file path. Displayed interactively unless `dont_show_plot`
  is `True`.
- **Fit data**: No `.npy` file is saved and no qubit parameter is updated by
  this class.

___

### ExpZIChevrons

`class ExpZIChevrons(ExpZIqubit)`

#### Description

`ExpZIChevrons` runs a "chevron" experiment on a single qubit's *ef*
transition — sweeping drive frequency and pulse duration together using the
`qubit_single_chevron` LabOne Q workflow — to locate the *ef* transition
frequency from the characteristic chevron pattern in a frequency/time colour
map. It fits a Lorentzian to the per-frequency signal variance (which peaks
at resonance, since off-resonant driving produces less oscillation over the
swept durations) to extract the frequency. An explicit call to
`update_qubits()` is required to commit the fitted frequency.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit object and (via `update_qubits()`) write the fitted frequency back to it. |
| `qubit_ids` | `list[str]` | Must contain exactly one qubit (the constructor asserts `len(qubit_ids)==1`). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, the fitted plot is saved and closed rather than displayed. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs forwarded to the `qubit_single_chevron` workflow call, most notably the
frequency/duration sweep values). This is typically used with
`transition='ef'`, since the chevron pattern here is intended for locating the
*ef* transition.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIChevrons import ExpZIChevrons

exp = ExpZIChevrons('chevrons_Q0', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0'], transition='ef')
lab.run_single(exp)
exp.update_qubits()
```

#### Analysis, Fitting and Outputs

`_post_process` retrieves the 2D dataset (frequency × pulse duration) and
computes the IQ phase, $\mathrm{atan2}(Q, I)$, at every point. For each
frequency, the variance of the phase across all swept durations is computed —
this variance is largest near resonance, where the Rabi-like oscillation
sweeps through a wide range of phase values, and small off-resonance. A
Lorentzian (`DFitPeakLorentzian`) is fit to this variance-vs-frequency trace
to extract the resonant frequency, stored in `self._fit_freq`.

##### Outputs

- **Plot**: A two-row figure — the frequency-vs-variance trace with its
  Lorentzian fit on top, and the phase colour map (frequency vs. duration)
  with a vertical dashed line at the fitted frequency below — is always
  generated and saved to `fitted_plot_{qubit_id}.png`. Displayed
  interactively unless `dont_show_plot` is `True`.
- **Fit data**: No `.npy` file is saved by this class; the fitted frequency is
  only kept on the instance (`self._fit_freq`) until `update_qubits()` is
  called.

##### `update_qubits()`

Commits the fitted frequency to the qubit's `DriveEF` (if `self._transition ==
'ef'`) or `DriveGE` property otherwise, then clears `self._fit_freq`. Asserts
the experiment has already been run (`self._fit_freq is not None`).

___

### ExpZIQASM

`class ExpZIQASM(ExpZIqubit)`

#### Description

`ExpZIQASM` compiles and runs an OpenQASM script on the QPU by parsing it (via
`ParserOpenQASM`), scheduling it against the SOFT-QPU/ZI hardware timing model
(`ScheduleParametersSoftQPUZI`), and executing it through the
`oqasm_scheduled_qubits` LabOne Q workflow. It is the underlying execution
engine used by higher-level experiments such as
[`ExpZIBellStateFidelity`](#expzibellstatefidelity), but can also be used
directly to run an arbitrary QASM circuit and retrieve its measurement
outcomes. Results are moved into a `data/` subfolder and are best inspected
via [`ExpZIQASMDataViewer`](#expziqasmdataviewer).

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up each physical qubit that QASM registers get mapped onto. |
| `qubit_ids` | `list[str]` (or as accepted by `ExpZIqubit`) | The physical qubits available for the QASM script's registers to be mapped onto (by default, mapped in declaration order — see [`set_qubit_reg_to_ZI_mappings`](#set_qubit_reg_to_zi_mappingsmapping)). |
| `qasm_file_path` | `str`, default `''` | Path to the QASM source file. Mutually exclusive with supplying `qasm_string` in `kwargs` (the constructor asserts exactly one of the two is given). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | Popped and stored (`self._dont_show_plot`), though this class's own `_post_process` does not itself generate a plot (the QASM schedule is instead rendered to an HTML file — see the Outputs section below). |
| `qasm_string` | `str` | The QASM source as a string, used instead of `qasm_file_path`. |
| `source_dirs` | `list[str]`, default `[]` | Additional directories to search for `include`d QASM source files. |
| `coordinate_system` | `str`, default `'RH'` | Must be `'LH'` or `'RH'` (left/right-handed); forwarded to the ZI workflow. |
| `update` | — | **Not settable.** The constructor asserts `update` is either absent or falsy, then forcibly sets `kwargs['update'] = False`. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIQASM import ExpZIQASM

exp = ExpZIQASM('qasm_test', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q1'], 'bell_state.qasm')
regs = exp.get_qubit_regs()
exp.set_qubit_reg_to_ZI_mappings({('q', 0): 'Q0', ('q', 1): 'Q1'})
lab.run_single(exp, override_ACQ_params={'AcquisitionMode': 'DISCRIMINATION', 'AveragingOrder': 'SingleShot'})
```

#### Methods

##### `get_qubit_regs()`

Returns the qubit registers declared/used in the QASM script (as parsed by
`ParserOpenQASM`).

##### `set_qubit_reg_to_ZI_mappings(mapping)`

Given as key-value pairs where the key is a qubit register tuple (as returned
by `get_qubit_regs()`) and the value is the (string) name of the physical
qubit HAL object it should be mapped onto, re-maps the QASM registers before
running. Asserts the mapping covers exactly the registers used by the script,
and that every mapped qubit name exists in `qubit_ids`.

##### `_run(file_path, sweep_vars=[], **kwargs)`

Parses the QASM script, builds the physical schedule, writes an interactive
schedule visualisation and the compiled main script/measurement-mapping JSON
to disk, forces `AcquisitionMode`/`AveragingOrder` into a QASM-compatible
combination (`DISCRIMINATION`/`SweepBeforeAverage` by default) if not already
set appropriately, then defers to `ExpZIqubit._run` to actually execute the
schedule. After execution, `self.qasm_output` is populated with each
measurement's outcome (only meaningfully for the
`DISCRIMINATION`+`SweepBeforeAverage` combination — otherwise a placeholder
`0`).

#### Outputs

- `compiled_qasm_schedule.html` — an interactive visualisation of the
  compiled hardware schedule, written to the experiment's file path.
- `main.qasm` — the resolved/flattened QASM source actually executed.
- `measurement_mapping.json` — declared classical registers and their mapping
  to internal measurement IDs.
- `measurement_params.json` — the acquisition/averaging mode and sweep sizes
  used, needed by [`ExpZIQASMDataViewer`](#expziqasmdataviewer) to interpret
  the raw data.
- A `data/` subfolder containing one `.h5` file per measurement ID (the
  top-level `data.h5` produced by the base `Experiment` machinery is removed,
  since QASM measurement results are stored per-measurement instead).

___

### ExpZIQASMDataViewer

`class ExpZIQASMDataViewer`

#### Description

`ExpZIQASMDataViewer` is a lightweight reader for the output folder produced
by [`ExpZIQASM`](#expziqasm) — it is not itself an experiment (it has no
`run`/`_run` method), just a helper for pulling out data for a given
classical register by name/index, correctly reshaped according to how the
QASM run's acquisition/averaging mode was configured. It is used internally
by [`ExpZIBellStateFidelity`](#expzibellstatefidelity) to feed measurement
data into `DataDensityMatrix.fromDataViewer`.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `expziqasm_data_folder_path` | `str` | Path to the output folder of a completed [`ExpZIQASM`](#expziqasm) run (i.e. its `_file_path`, containing `measurement_mapping.json`, `measurement_params.json`, and the `data/` subfolder). |

`ExpZIQASMDataViewer` takes no keyword arguments.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIQASMDataViewer import ExpZIQASMDataViewer

ledv = ExpZIQASMDataViewer(exp._file_path)   # exp is a completed ExpZIQASM run
print(ledv.get_inner_slicing_vars())
data = ledv.get_data('c', 0)
```

#### Methods

##### `get_number_of_shots()`

Returns the `NumRepetitions` recorded in `measurement_params.json`.

##### `get_inner_slicing_vars()`

Returns the list of "inner" (non-swept) axis names present in each stored
measurement array — depends on the recorded `acq_type`
(`'DISCRIMINATION'`/`'INTEGRATION'`/`'RAW'`) and `avg_type`
(`'SweepBeforeAverage'` or not) — e.g. `['shot']`, `['iq']`, `['shot','iq']`,
`['samples','iq']`, or `['shot','samples','iq']`, prefixed by any swept
variable names.

##### `get_data(classical_register_name, classical_register_index=None)`

Returns the stored data for the given classical register. If
`classical_register_index` is `None`, returns a list with one entry per bit
in that register (`None` for any bit that was never measured into); otherwise
returns just that bit's data array (discriminated data is cast to `int`, and
a single-element array is unwrapped to a Python `float`).

___

### ExpZIChevrons2QFixedCoupler

`class ExpZIChevrons2QFixedCoupler(ExpZIqubit)`

#### Description

`ExpZIChevrons2QFixedCoupler` sweeps a fixed coupler's flux-pulse amplitude
together with a wait time, using the
`calibrate_tunable_transmon_fixed_coupler_osc` LabOne Q workflow, to produce
the classic two-qubit "chevron" pattern used to find the CZ (or similar
flux-pulse) interaction point between two qubits joined by a tunable-frequency
fixed coupler. It automatically discovers and includes any additional qubits
involved with the coupler (e.g. auxiliary lines), and — in single-shot mode —
computes state populations directly from discriminated outcomes for every
qubit measured.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to `ExpZIqubit`. |
| `hal_QPU` | — | The QPU HAL object; used to look up the coupler and qubit objects. |
| `qubit_ids` | `list[str]` | The two coupled qubits, e.g. `['Q0', 'Q2']`. May be extended in place with any additional qubits the coupler object reports as involved (with a printed warning). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | If `True`, the resulting figure is saved and closed rather than displayed. |
| `amplitudes` | array-like, **required** | The coupler flux-pulse amplitude values to sweep. The constructor asserts `'amplitudes' in kwargs`. |
| `plot_with_frequency` | `bool`, default `True` | If `True` and the tuned qubit has `FluxConversionParams` set, overlays a secondary frequency axis (converted from flux amplitude) on the amplitude axis. |
| `single_shot` | `bool`, default `False` | If `True`, forces `AveragingOrder='SingleShot'`, `AcquisitionMode='DISCRIMINATION'` and plots discriminated $g$/$e$/$f$ population heatmaps for every qubit in `qubit_ids`; if `False`, forces `AveragingOrder='DEFAULT'`, `AcquisitionMode='DEFAULT'` and plots IQ magnitude instead. |
| `show_single_qubit` | `bool` or `str`, default `False` | Only meaningful when `single_shot=False`: if `True`, shows only `qubit_ids[0]`'s trace; if a qubit-ID string (must be in `qubit_ids`), shows only that qubit's trace; if `False`, shows every qubit. |

Any remaining keyword arguments are passed through to `ExpZIqubit.__init__`
(see [`ExpZIRabi`](#expzirabi) for how `ExpZIqubit` itself handles
`use_cal_traces`, `transition`, `ZI_plot`, `show_pulse_sheet`, and unmatched
kwargs forwarded to the workflow call, most notably `wait_times`). Note:
`_run` asserts that no external `sweep_vars` are supplied — the amplitude
sweep is the only sweep this class allows.

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIChevrons2QFixedCoupler import ExpZIChevrons2QFixedCoupler

exp = ExpZIChevrons2QFixedCoupler('chevron2Q_Q0Q2', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q2'],
  amplitudes=np.linspace(0.0, 0.5, 41), wait_times=np.linspace(1e-9, 250e-9, 30), single_shot=True)
lab.run_single(exp, raw_pulse_sheet_duration=1e-3)
```

#### Analysis, Fitting and Outputs

`_run` wraps the coupler's `Amplitude` in a `VariablePropertyTransient` and
sweeps it over `amplitudes` alongside the underlying workflow's own
`wait_times` sweep. In `_post_process`:

- **If `single_shot` is `True`**: for every qubit, computes the fraction of
  shots landing in each of states $g$/$e$/$f$ as a function of (amplitude,
  wait time), plots each as a heatmap (one row per qubit, one column per
  state), and saves the raw per-qubit population arrays to `fitted_data.npy`
  (as `{'qubits':..., 'wait_times':..., 'flux_amps':..., 'pop_qubit_amps_times':...}`
  — this is the file consumed by
  [`ExpZIFixedCouplerTuneup`](#expzifixedcouplertuneup)).
- **Otherwise**: for the qubit(s) selected by `show_single_qubit`, plots the
  raw IQ magnitude as a heatmap (amplitude vs. wait time). No `.npy` file is
  saved in this mode.

In both modes, if the tuned qubit has `FluxConversionParams` set and
`plot_with_frequency` is `True`, a secondary frequency axis is added above the
amplitude axis on the top row of panels.

##### Outputs

A single figure (one row per qubit, in single-shot mode; a stacked column of
per-qubit panels otherwise) is always generated and saved to
`fitted_plot.png`. Displayed interactively unless `dont_show_plot` is `True`.

___

### ExpZIFixedCouplerTuneup

`class ExpZIFixedCouplerTuneup`

#### Description

`ExpZIFixedCouplerTuneup` is an orchestration class (not an `ExpZIqubit`
subclass) that automates finding a fixed coupler's optimal CZ-gate flux-pulse
amplitude and length. It first runs a 2D chevron sweep (via
[`ExpZIChevrons2QFixedCoupler`](#expzichevrons2qfixedcoupler)) across flux
amplitude and wait time to locate the amplitude at which the target state's
population varies most (maximum variance across wait time — indicating the
strongest interaction), then fixes that amplitude and re-runs a 1D wait-time
sweep, fitting a cubic spline to locate the desired extremum (a maximum or
minimum in population) as the optimal pulse length. Both results can be
committed live to the coupler object.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name used to group the sub-experiments (`lab.group_open`/`group_close`). |
| `expt_config` | — | Experiment configuration object passed through to each sub-experiment. |
| `hal_QPU` | — | The QPU HAL object; used to look up the coupler and qubit objects. |
| `qubit_ids` | `list[str]` | The two coupled qubits, e.g. `['Q0', 'Q2']`. |
| `fit_qubit` | `str` | Which of the measured qubits' population to use for locating the interaction amplitude/length (must match one of the qubits present in the chevron sweep's output, including any auto-added coupler-involved qubits). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `fit_state` | `str`, default `'E'` | Which state (`'G'`/`'E'`/`'F'`) of `fit_qubit` to use for locating the interaction amplitude and the pulse-length extremum. |
| `pop_fit_extremum` | `str`, default `'max'` | Whether to locate a `'max'` or `'min'` in the wait-time population trace when fitting the optimal pulse length via the spline. |
| `variance_fit_type` | `str`, default `'default'` | Whether the optimal amplitude is taken from the Lorentzian fit's centre (`'default'`) or from the raw data point with maximum variance (`'max'`). |
| `individual_plots` | `bool`, default `False` | If `True`, each sub-experiment's own per-experiment plot is shown live (`dont_show_plot=not individual_plots` passed through). |
| `update_params_live` | `bool`, default `True` | If `True`, updates the coupler's `Amplitude` and `Length` in-place with the located optima as the routine proceeds. |
| `enable_ZI_log_messages` | `bool`, default `False` | Stored but not directly referenced in `run()`. |
| `flux_amp_range` / `flux_amp_span` / `flux_amp_points` | array-like / `float` (default `0.05`) / `int` (default `11`) | Either supply the full `flux_amp_range` array, or let it be built as `coupler.Amplitude + linspace(-flux_amp_span/2, flux_amp_span/2, flux_amp_points)`. |
| `wait_times` / `wait_time_max` / `wait_time_points` | array-like / `float` (default `250e-9`) / `int` (default `30`) | Either supply the full `wait_times` array, or let it be built as `linspace(1e-9, wait_time_max, wait_time_points)`. |

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIFixedCouplerTuneup import ExpZIFixedCouplerTuneup

exp = ExpZIFixedCouplerTuneup('cplTuneup_Q0Q2', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q2'],
  fit_qubit='Q0', flux_amp_points=17, flux_amp_span=0.03)
exp.run(lab)
```

#### Methods

##### `run(lab)`

1. Opens a `lab` experiment group named `name` and sets up a 2×2 figure grid
   (variance-vs-amplitude / amplitude-vs-time heatmap on the left,
   population-vs-time / extremum-fit on the right).
2. Runs [`ExpZIChevrons2QFixedCoupler`](#expzichevrons2qfixedcoupler) over
   `flux_amp_range`/`wait_times` in single-shot mode, and loads its saved
   `fitted_data.npy`.
3. Fits a Lorentzian to the variance (over wait time) of `fit_qubit`'s
   `fit_state` population vs. flux amplitude, and locates the optimal
   amplitude (per `variance_fit_type`). If `update_params_live` is `True`,
   commits it to the coupler's `Amplitude`.
4. Re-runs `ExpZIChevrons2QFixedCoupler` with a single fixed amplitude (the
   one just located) over the same `wait_times`, to get a clean 1D
   population-vs-time trace.
5. Fits a cubic spline (`scipy.interpolate.CubicSpline`) to that trace, finds
   its stationary points via the spline's derivative, estimates the
   oscillation period from the median spacing between them, and selects the
   stationary point closest to one period as the pulse-length extremum (per
   `pop_fit_extremum`). If `update_params_live` is `True`, commits it to the
   coupler's `Length`.
6. Closes the `lab` experiment group and saves the combined summary figure.

#### Outputs

A single 4-panel summary figure, `Overview.png`, saved in the parent
directory of the chevron sweep's output folder, and always left open for
interactive display (this class has no `dont_show_plot` option of its own).

___

### ExpZIPhaseCompensation2Q

`class ExpZIPhaseCompensation2Q(Experiment)`

#### Description

`ExpZIPhaseCompensation2Q` calibrates the single-qubit $Z$-rotation ("virtual
phase") compensation angles needed around a two-qubit CZ-type gate on a fixed
coupler, for the coupler's main (flux-pulsed) qubit, its stationary
(spectator) qubit, and — if present — an auxiliary qubit sharing the flux
line. For each role, it sweeps a compensating $R_z(\theta)$ angle around a
Ramsey-like echo sequence and fits a sinusoid to locate the angle that
restores the qubit to its ideal state, committing the results to the
coupler's `CompZAngle`/`CompZAngleStationary`/`CompZAngleAux` properties.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name of the experiment. |
| `expt_config` | — | Experiment configuration object passed through to each sub-experiment. Must already have `AcquisitionMode='DISCRIMINATION'` and `AveragingOrder='SingleShot'` set on its acquisition HAL — the constructor asserts both. |
| `hal_QPU` | — | The QPU HAL object; used to look up the coupler and qubit objects. |
| `qubit_ids` | `list[str]` | Must contain more than one qubit, e.g. the two coupled qubits `['Q0', 'Q2']`. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `normalise_data` | `bool`, default `True` | Stored (`self._normalise_data`) but not directly consumed by this class's own `post_process` (which works from raw discriminated shots) — provided for parity/forwarding to the underlying `ExpZIqubit` sub-experiments. |
| `states` | `str`, default `'ge'` | Stored as `self._transition`; forwarded to the sub-experiments. |
| `update_coupler` | `bool`, default `False` | If `True`, commits the fitted compensation angles to the coupler object when `post_process()` is called. |
| `rz_angles` | array-like, default `np.linspace(0, 2π, 11)` | The virtual $R_z(\theta)$ compensation angles to sweep for each role (main/stationary/aux). |
| `coupler_obj` | coupler object, default `None` | The coupler to calibrate. If not supplied, it is looked up via `hal_QPU.get_coupler_obj_from_qubits(qubit_ids[0], qubit_ids[1], TunableTransmonCouplerFixed)`. |
| `coupler_name` | `str`, default `None` | Overwritten internally to `self.cur_coupler_obj.Name` regardless of what is passed — effectively unused as an independent input. |

Any remaining keyword arguments are passed through to each `ExpZIqubit`
sub-experiment. The main/aux/stationary qubit roles are auto-detected from the
coupler's `signals` dict (`'flux'`, `'flux_aux'`, `'drive_comp_stationary'`)
— the constructor asserts a main and a stationary qubit are found (an
auxiliary qubit is optional, with a printed notice if absent).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIPhaseCompensation2Q import ExpZIPhaseCompensation2Q

exp = ExpZIPhaseCompensation2Q('phaseComp_Q0Q2', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q2'],
  rz_angles=np.linspace(0, 2*np.pi, 21), update_coupler=True)
exp.run(lab)
exp.post_process()
```

#### Methods

##### `run(lab)`

Opens a `lab` experiment group named `name`, then runs the
`phase_compensation_cz` LabOne Q workflow once per role — main (with the
coupler's own `CompZAngle` reset to `None` first), auxiliary (if present, with
`CompZAngleAux` reset to `None`), and stationary (with `CompZAngle` reset to
`None` again) — each sweeping `rz_angles`, storing the resulting per-angle
population traces in `self.data`.

##### `post_process()`

Calls the static `plot_fitted_data` to fit and plot all measured roles, then
— if `update_coupler` is `True` — commits the fitted `CompZAngle`,
`CompZAngleStationary`, and (if measured) `CompZAngleAux` to the coupler
object.

##### `plot_fitted_data(data, main_qubit_id=None, coupler_id=None, aux_qubit_id=None, stationary_qubit_id=None, save_path=None)` *(static)*

For each measured role, fits a sinusoid (`DFitSinusoid`) to population vs.
$R_z(\theta)$ and locates the angle minimising the fitted curve (the
compensation angle that best restores the ideal population), plotting each
role's data/fit on its own panel. Returns a dict of fitted angles keyed by
role (`'main'`, `'stationary'`, and — if present — `'aux'`).

#### Outputs

A summary figure (2 or 3 panels, depending on whether an auxiliary qubit is
present) is saved to `fitted_plot.png` in the parent directory shared by the
sub-experiments' output. No `.npy` fit-data file is saved.

___

### ExpZIBellStateFidelity

`class ExpZIBellStateFidelity(ExpZIqubit)`

#### Description

`ExpZIBellStateFidelity` prepares a two-qubit Bell state (via a QASM circuit:
reset, Hadamards, a CZ, and a final Hadamard) on a pair of qubits joined by a
fixed coupler, performs two-qubit state tomography by executing the resulting
QASM script through [`ExpZIQASM`](#expziqasm), reconstructs the density
matrix (`DataDensityMatrix`), and reports the state fidelity and purity
relative to the ideal Bell state. Optionally commits the fidelity to the
coupler's `FidelityBell` property.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name used both for the experiment and to group sub-experiments. |
| `expt_config` | — | Experiment configuration object passed through to the underlying `ExpZIQASM` run. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit and coupler objects. |
| `qubit_ids` | `list[str]` | Must contain exactly two qubits, e.g. `['Q0', 'Q2']` (the constructor asserts `len(qubit_ids)==2`). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `dont_show_plot` | `bool`, default `False` | Popped and stored (`self._dont_show_plot`), though not directly referenced by the provided `run`/`post_process` methods (the 3D density-matrix plot is always saved via `leRho.plot3D`). |
| `update` | `bool`, default `True` | If `True`, writes the measured Bell-state fidelity to the coupler's `FidelityBell` property when `post_process()` is called. |
| `readout_correction` | `'ge'`/`'gef'`/`None`, default `'ge'` | Which readout-correction matrix (from each qubit's `CorrectionMatrix` dict — see [`ExpZIBlobs.get_correction_matrices`](#get_correction_matricesupdatefalse)) to apply during tomographic reconstruction; falls back to uncorrected reconstruction with a printed notice if the requested matrix isn't present. |
| `save_qasm_path` | `str`, default `f'BellStateTomography{{q1}}{{q2}}.qasm'` | Where the generated tomography QASM script is written. |
| `coordinate_system` | `str`, default `'RH'` | Must be `'LH'` or `'RH'`; forwarded to `DataDensityMatrix.generate_tomography_qasm`. |

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIBellStateFidelity import ExpZIBellStateFidelity

exp = ExpZIBellStateFidelity('bellState_Q0Q2', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q2'], update=True)
exp.run(lab)
exp.post_process()
```

#### Methods

##### `run(lab)`

Builds a full two-qubit tomography QASM script from the fixed Bell-state
preparation circuit (via `DataDensityMatrix.generate_tomography_qasm`), then
runs it via [`ExpZIQASM`](#expziqasm) across every qubit on the QPU (mapping
the QASM's `q[0]`/`q[1]` registers onto `qubit_ids[1]`/`qubit_ids[0]`
respectively), forcing `AcquisitionMode='DISCRIMINATION'`,
`AveragingOrder='SingleShot'`.

##### `post_process(use_abs_phase=False, readout_correction=None)`

Reads back the QASM run's output via
[`ExpZIQASMDataViewer`](#expziqasmdataviewer), reconstructs the two-qubit
density matrix (with readout correction applied if configured/available),
computes the fidelity against the ideal Bell state `[1,0,0,1]/√2` (as a
percentage, stored in `self._fidelity`) and the state purity (stored in
`self._purity`), plots a 3D density-matrix visualisation, and — if `update`
was `True` — writes the fidelity to the coupler's `FidelityBell` property. An
explicit `readout_correction` argument here overrides the one set at
construction.

#### Outputs

- **Plot**: A 3D density-matrix visualisation, saved as `BellState.png` in the
  QASM run's output folder.
- No `.npy` fit-data file is saved; `self._fidelity` and `self._purity` are
  kept on the instance.

___

### ExpZICryoscope

`class ExpZICryoscope`

#### Description

`ExpZICryoscope` performs a cryoscope measurement to characterise (and
compensate) the impulse response of a fixed coupler's flux line. For a range
of flux-pulse amplitudes, it measures the second qubit's phase accumulation
($\langle X\rangle$/$\langle Y\rangle$ via two 90°-rotated Ramsey-like
sequences) as a function of time after the flux pulse, demodulates and
converts the resulting phase evolution into an instantaneous frequency shift,
converts that into an equivalent normalised flux via the qubit's spectrum
($f_{max}$, $E_C/h$), and fits a step-response model to that flux trace,
producing a digital pre-distortion (precompensation) filter kernel that can be
loaded onto the coupler's pulse.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Name used to group the two sub-experiments (`lab.group_open`/`group_close`). |
| `expt_config` | — | Experiment configuration object passed through to the sub-experiments. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit and coupler objects. |
| `qubit_ids` | `list[str]` | Must contain more than one qubit (the constructor asserts `len(qubit_ids) > 1`) — the first qubit is the one measured, and a coupler is looked up between it and the second. |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `nyquist_order` | `int`, default `0` | Compensates for aliasing when the true frequency shift lies above the Nyquist frequency set by the sampling rate implied by `lengths`; adds `0.5·nyquist_order/dt` to the demodulated frequency. |
| `amplitudes` | array-like, default `np.linspace(0.3, 0.3, 1)` | The coupler flux-pulse amplitudes to characterise (a single amplitude by default). |
| `lengths` | array-like, default `np.arange(0, 300e-9, 0.5e-9)` | The post-flux-pulse wait times ($\tau$) at which phase is sampled. |
| `transition` | `str`, default `'ge'` | The transition used for calibration-based normalisation. |
| `normalise_data` | `bool`, default `True` | If `True`, normalises the raw IQ traces into $\langle X\rangle$/$\langle Y\rangle$ expectation values using calibration data; required for the reconstruction and fitting steps to run. |
| `f_max` | `float`, default `qubit.FluxConversionParams['f_max']` (if available) | The qubit's maximum (flux-insensitive) transition frequency, used to convert frequency shift into normalised flux. |
| `Ec_over_h` | `float`, **required** | The qubit's charging energy divided by Planck's constant, used in the same flux conversion. The constructor asserts this is provided. |
| `norm_window` | `tuple(int, int)`, default `(0.8·n, n)` | The index range (into the time-trace array of length `n`) used to normalise the reconstructed flux trace to its long-time value; defaults to the last 20% of the trace. |

Any other keyword argument is stored in `self._kwargs` and forwarded through
to each underlying `ExpZIqubit`/`cryo_scope` sub-experiment call (as well as
into `lab.run_single`).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZICryoscope import ExpZICryoscope

exp = ExpZICryoscope('cryoscope_Q0Q2', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q2'],
  amplitudes=np.linspace(0.2, 0.4, 5), lengths=np.arange(0, 300e-9, 0.5e-9), Ec_over_h=200e6)
exp.run(lab)
```

#### Methods

##### `run(lab)`

Runs two `cryo_scope` sub-experiments back-to-back (`y90=False` then
`y90=True`, measuring $\langle Y\rangle$ and $\langle X\rangle$ respectively)
over `lengths`/`amplitudes`, then calls `post_process()`, `plot_summary()`,
and `fit_step_response()` in turn.

##### `post_process(filter_window_length=7, polyorder=2)`

Normalises the raw $X$/$Y$ traces into expectation values (if
`normalise_data`), forms the complex signal $C = X + iY$ for each amplitude,
demodulates it via its dominant FFT frequency, extracts the phase derivative
(both a raw finite-difference version and a Savitzky-Golay-filtered version),
converts the resulting frequency shift into a normalised flux
$\Phi_R/\Phi_0$ via the qubit's spectrum ($f_{max}$, $E_C/h$), and normalises
each amplitude's flux trace by its value within `norm_window` to produce the
final normalised step response `s(t)`. Warns if a trace's normalisation value
is close to zero (a symptom of Nyquist aliasing in the demodulation).

##### `plot_calibrated_traces()` / `plot_fft_grid(...)` / `plot_amplitude_grid(...)` / `plot_summary()`

Diagnostic plotting helpers: the calibrated $X$/$Y$/phase traces per
amplitude; a grid of FFT spectra (showing the chosen demodulation frequency
and the Nyquist band) for a subset of amplitudes; a grid of per-amplitude
detuning/flux/normalised-step-response traces; and (`plot_summary`) all
three in sequence.

##### `fit_step_response(amplitude_index=0, update_coupler=True)`

Fits a pole-zero model to the normalised step response at the given
amplitude index (via `Flattenator.fit_step_response`, 5 poles/5 zeros) and, if
`update_coupler` is `True`, writes the resulting compensation kernel onto the
coupler's `Pulse['precomp_kernel']`.

##### `fit_step_response_from_s_data(normalised_step_response)` *(static)*

Lower-level helper: fits the pole-zero model directly to a given normalised
step-response array and returns the compensation kernel.

#### Outputs

Three diagnostic figures (calibrated traces, FFT grid, amplitude grid) plus
the `Flattenator` fit's own response plot, all left open for interactive
display; this class does not expose a `dont_show_plot` option, and does not
save any of its figures to disk itself (though the underlying `cryo_scope`
sub-experiments' own outputs are saved as usual). The fitted compensation
kernel is returned by `fit_step_response_from_s_data` and (if requested)
written directly onto the coupler object rather than saved to a file.

___

### ExpZIDailyTuneup

`class ExpZIDailyTuneup`

#### Description

`ExpZIDailyTuneup` is the top-level orchestration class (not an `ExpZIqubit`
subclass) that runs a full daily maintenance/tuneup routine on a single
qubit: fine $X$-gate tuneup, readout resonator + integration-weight
optimisation, $T_1$, two-qubit gate fine-tuning (chevron amplitude/length) if
a coupled qubit is found, single-qubit randomised benchmarking, and two-qubit
Bell-state fidelity — printing a running summary and (optionally) saving the
QPU configuration to disk.

#### Arguments

##### Positional

| Argument | Type | Description |
|---|---|---|
| `name` | `str` | Stored as `self._name` but not currently used by `run()` — every sub-experiment's name is built from the hardcoded literal `'DailyTuneup'` (e.g. `f'DailyTuneup_{qubit_id}_FinetuneX'`), not from this argument. |
| `expt_config` | — | Experiment configuration object passed through to every sub-experiment. |
| `hal_QPU` | — | The QPU HAL object; used to look up the qubit (and any coupled qubit/coupler) objects. |
| `qubit_id` | `str` | A single qubit ID, as a string (the constructor asserts `isinstance(qubit_id, str)`). |

##### Keyword arguments

| Argument | Type / Default | Description |
|---|---|---|
| `tune_readout` | `bool`, default `True` | If `True`, runs the readout-resonator optimisation ([`ExpZIResOptimal`](#expziresoptimal)), integration-weight optimisation, and (if `update_params_live`) an [`ExpZIBlobs`](#expziblobs) fidelity check. |
| `individual_plots` | `bool`, default `False` | Passed through to sub-experiments as `dont_show_plot=not individual_plots`/`ZI_plot=individual_plots` (whichever each sub-experiment exposes). |
| `update_params_live` | `bool`, default `True` | Gates whether each step's fitted result is actually committed to the qubit/coupler as the routine proceeds (readout frequency, $T_1$, two-qubit gate amplitude/length, randomised-benchmarking fidelity, Bell-state fidelity). |
| `enable_ZI_log_messages` | `bool`, default `False` | Stored but not directly referenced in `run()` (each sub-experiment manages its own ZI logging). |
| `save_config` | `bool`, default `False` | If `True`, saves the QPU configuration to a timestamped JSON file at the end of the routine (backing up any existing file of the same generated name first). |
| `print_summary` | `bool`, default `True` | If `True`, calls `hal_QPU.print_summary_ZIQubits()` at the end of the routine. |
| `save_summary_config_from_json` | `bool`, default `True` | If `True` (and `save_config` is also `True` — forced to `False` otherwise), also generates a summary JSON (via `SOFTqpu.create_summary_config_from_json`) intended for a website/dashboard update. |
| `summary_json_file` | `str`, default `f'{today:%Y%m%d}_QPUsummary.json'` | Output path for the summary JSON described above. |
| `skip_2qg` | `bool`, default `False` | If `True`, skips both the two-qubit gate fine-tuning and the Bell-state fidelity steps entirely. |
| `states` | `str`, default `'gef'` | Must be `'ge'`, `'ef'`, or `'gef'`; used for the readout-fidelity update rule and passed through where relevant. |
| `res_is_trough` | `bool`, default `True` | Stored (`self._res_trough`) but not directly referenced in the provided `run()` body. |
| `update_qubits_by_fidelity` | `str`, default `'mean'` | Which state's fidelity to prioritise (`'g'`/`'e'`/`'f'`/`'mean'`, case-insensitive) when calling [`ExpZIResOptimal.update_qubits_by_fidelity`](#update_qubits_by_fidelitystate_fidelitygef) for the readout step. |
| `res_freq_range` / `res_freq_span` / `res_freq_points` | array-like / `float` (default `10e6`) / `int` (default `101`) | Either supply the full `res_freq_range` array, or let it be built as `linspace(ReadoutFrequency − 2·span/3, ReadoutFrequency + span/3, points)`. |
| `chevron_amp_pts` | `int`, default `17` | Passed as `flux_amp_points` to the [`ExpZIFixedCouplerTuneup`](#expzifixedcouplertuneup) sub-experiment during the two-qubit gate step. |
| `chevron_amp_span` | `float`, default `0.03` | Passed as `flux_amp_span` to the same sub-experiment. |
| `skip_benchmarking` | `bool`, default `False` | If `True`, skips both the single-qubit randomised-benchmarking and (as a consequence) the Bell-state fidelity steps, since the latter is nested inside the former's `if` block in the source. |
| `rb_sequence_lengths` | `list[int]`, default `[4, 8, 16, 32, 64, 128]` | Passed as `sequence_lengths` to [`ExpZIRandomisedBenchmarking`](#expzirandomisedbenchmarking). |
| `rb_num_trials` | `int`, default `6` | Passed as `num_trials` to the same sub-experiment. |

All other keyword arguments are stored in `self._kwargs` and forwarded to the
fine-$X$-tuneup step ([`ExpZISingleQubitTuneup.run_fine_tuneup`](ZI_SingleQubitTuneup.md)).

#### Example snippet
```python
from sqdtoolz.Experiments.Experimental.ExpZIDailyTuneup import ExpZIDailyTuneup

exp = ExpZIDailyTuneup('DailyTuneup', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q0',
  save_config=True, rb_sequence_lengths=[4, 8, 16, 32, 64])
exp.run(lab)
```

#### Methods

##### `run(lab)`

Runs, in order: fine $X$-gate tuneup
([`ExpZISingleQubitTuneup.run_fine_tuneup`](ZI_SingleQubitTuneup.md)); (if
`tune_readout`) readout-resonator optimisation
([`ExpZIResOptimal`](#expziresoptimal)) plus integration-weight optimisation
(a `time_traces` `ExpZIqubit` run) plus (if `update_params_live`) an
[`ExpZIBlobs`](#expziblobs) fidelity check; $T_1$
([`ExpZIT1`](#expzit1)); (unless `skip_2qg`, and only if a coupled qubit is
found on the QPU) two-qubit gate fine-tuning
([`ExpZIFixedCouplerTuneup`](#expzifixedcouplertuneup)); (unless
`skip_benchmarking`) single-qubit randomised benchmarking
([`ExpZIRandomisedBenchmarking`](#expzirandomisedbenchmarking)) followed by
(unless `skip_2qg`, and only if a coupled qubit was found) Bell-state fidelity
([`ExpZIBellStateFidelity`](#expzibellstatefidelity)); and finally the
summary-printing/config-saving steps described above. Progress and
before/after values for each step are printed to the console throughout.

#### Outputs

Each step's own plots/`.npy` files are produced as usual by the sub-experiment
it runs; `ExpZIDailyTuneup` itself does not generate any additional plot. If
`save_config` is `True`, a timestamped `{YYYYMMDD_HHMM}_QPU_config.json` is
written (with any pre-existing file of that name backed up to
`/Config_backups/` first), and — if `save_summary_config_from_json` is also
`True` — a summary JSON is written to `summary_json_file`.