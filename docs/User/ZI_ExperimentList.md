# List of ZI experiments
A list of all current experiments for ZI hardware. Detailed documentation of each experiment is still a work in progress. The source code for these experiments can be found in `sqdtoolz/Experiments/Experimental/`.

### Table of contents
This table of contents is given in roughly the order experiments would be needed for tuneup and experimentation on a new qubit chip.
- **[Resonator spectroscopy](#expzires):** `ExpZIRes`
    - [Resonator power sweep](#expzirespowersweep): `ExpZIResPowerSweep` 
    - [Resonator flux sweep](#expziresfluxsweep): `ExpZIResFluxSweep`
- **[Qubit spectroscopy](#expziqubitspec):** `ExpZIQubitSpec`
    - [Qubit spectroscopy flux sweep](#expziqubitfluxsweep): `ExpZIQubitFluxSweep`
    - [Qubit spectroscopy power sweep](#expziqubitpowersweep): `ExpZIQubitPowerSweep`
- **Qubit time domain experiments:**
    - [Amplitude Rabi](#expzirabi): `ExpZIRabi`
    - [Lifetime $T_1$](expzit1):  `ExpZIT1`
    - [Ramsey $T_2^*$](#expziramsey): `ExpZIRamsey`
- **[Dispersive shift](#expzidispersive)** $\chi$: `ExpZIDispersive`
- **Single shot readout and active reset:**
    - IQ blobs: `ExpZIBlobs`
    - Active reset tuneup: `ExpZIActiveResetTuneup`
    - TWPA optimisation: `ExpZITWPATuneup`
    - Lifetime $T_1$ (single shot): `ExpZIT1SingleShot`
    - Resonator frequency for optimised readout fidelity: `ExpZIResOptimal`
- **Single qubit $X$ gate calibration:** `ExpZICalibX`
- **Two qubit chevrons:** `ExpZIChevrons`
- **QASM implementation:** `ExpZIQASM`

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
documentation for the full breakdown of `use_cal_traces`, `transition`,
`ZI_plot`, `show_pulse_sheet`, and how unmatched kwargs are forwarded into
the `ramsey` `experiment_workflow` call).

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
