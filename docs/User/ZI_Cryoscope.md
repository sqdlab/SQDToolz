# `ExpZICryoscope` — Usage Guide

`ExpZICryoscope` runs a [cryoscope](https://arxiv.org/pdf/1907.04818) experiment on a qubit/coupler pair, reconstructs the
flux-pulse step response from the measured qubit phase, and provides a fitted
predistortion kernel that can be applied to the coupler's flux pulse. This predistortion filter can be used to correct any pulse shape (e.g. `gaussian_square`, `square`, etc.).

The [typical workflow](#full-workflow-example) has four stages, run in order:

1. [**Construct** `ExpZICryoscope(...)`](#1-running-the-experiment) — runs the X90/Y90 cryoscope experiments and collects raw data.
2. [**`post_process(...)`**](#2-post-processing) — demodulates, filters, and reconstructs the flux step response `s(t)`.
3. [**`plot_summary()`**](#3-visual-inspection) — visualises the calibrated traces, FFT spectra, and reconstructed response.
4. [**`fit_step_response(...)`**](#4-fitting-the-compensation-kernel) — fits a compensation kernel to the step response and (optionally) writes it to the coupler's pulse parameters (e.g. `lab.HAL('Cpl12').Pulse['precomp_kernel]`).


#### Full workflow example

```python
exp = ExpZICryoscope("cryoscope_Q1Q2", lab.CONFIG('ZI'), lab.HAL('QPU'),
    ["Q1", "Q2"], amplitudes=np.array([-0.35]),
    lengths=np.arange(0.0, 400e-9, (1/2.0)*1e-9), 
    Ec_over_h=200e6, f_max=5e9)

exp.post_process()
exp.plot_summary()
exp.fit_step_response(update_coupler=True)
```


## 1. Running the experiment

```python
exp = ExpZICryoscope(
    name="cryoscope_Q1Q2",
    expt_config=expt_config,
    hal_QPU=hal_QPU,
    qubit_ids=["Q1", "Q2"],          
    amplitudes=np.linspace(0.1, 0.3, 3),
    lengths=np.linspace(0.0, 100e-9, 1/(2e9)),
    transition="ge",
    normalise_data=True,
    Ec_over_h=200e6, # qubit anharmonicity, used for flux reconstruction
    f_max=5e9, # optional: falls back to FluxConversionParams['f_max']
    norm_window=None, # (start_idx, end_idx) window used to normalise flux
    nyquist_order=0, # correct for aliasing if f_demod wraps around Nyquist
)
```

**What happens on construction:**

- Runs two sub-experiments back-to-back (`lab.run_single`):
  - An **X90** experiment (measures `⟨Y⟩`).
  - A **Y90** experiment (measures `⟨X⟩`).
- Each is swept over `lengths` (the cryoscope delay `τ`) and `amplitudes` (flux pulse amplitude).
- If `normalise_data=True`, calibration datasets (`calibX`, `calibY`) are also retrieved for later normalisation in `post_process`.
- Raw results are stored in `exp.data`:
  - `data['X']`, `data['Y']` — raw measured arrays.
  - `data['tau']` — delay sweep values (s).
  - `data['amplitude']` — flux pulse amplitude sweep values.

**Requirements:**
- `qubit_ids` must contain **at least two entries** — the second is used to identify the associated coupler (`TunableTransmonCouplerFixed`) whose pulse gets updated later.
- `Ec_over_h` is **required** (no default) — the constructor will assert if it's missing.
- `f_max` is required either as a kwarg or via the qubit's `FluxConversionParams`.

---

## 2. Post-processing

```python
exp.post_process(filter_window_length=7, polyorder=2)
```

This converts the raw `⟨X⟩`/`⟨Y⟩` traces into a reconstructed, normalised flux step response.

**Steps performed internally, per amplitude:**

1. Normalise `X`/`Y` traces against calibration data (if `normalise_data=True`) and combine into a complex signal `C(τ) = X_norm + i·Y_norm`.
2. FFT `C(τ)` to find the dominant demodulation frequency `f_demod`.
3. Demodulate and unwrap the phase, `φ(τ)`.
4. Compute the raw frequency shift from the phase derivative, and a [Savitzky–Golay](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html)-filtered version (`filter_window_length`, `polyorder` control the smoothing).
5. Convert frequency shift → flux (`Φ_R/Φ_0`) using `f_max` and `Ec_over_h`.
6. Normalise the flux trace by its mean value over `norm_window` (defaults to the last 20% of the trace) to produce the final **normalised step response** `s(t)`, which should settle to `1.0`.

**Key outputs added to `exp.data`:**

| Key | Meaning |
|---|---|
| `f_demod` | Demodulation frequency per amplitude |
| `phase` | Unwrapped demodulated phase per amplitude |
| `delta_f_R_raw` / `delta_f_R` | Raw / filtered frequency shift vs. `τ` |
| `Phi_R` | Reconstructed flux (`Φ_R/Φ_0`) vs. `τ` |
| `s` | **Normalised step response** — the main quantity used for kernel fitting |
| `norm_value` | Normalisation constant used per amplitude |
| `spec`, `freqs` | FFT spectrum and frequency axis |

> **Note:** If a trace's `norm_value` is near zero, a warning is raised — this usually indicates `f_demod` aliasing around the Nyquist frequency. Check `nyquist_order` or inspect the FFT plots below before trusting that trace.

---

## 3. Visual inspection

```python
exp.plot_summary()
```

This produces three figures in sequence:

- **`plot_calibrated_traces()`** — `⟨X⟩`, `⟨Y⟩`, and phase `φ` vs. `τ`, overlaid across all amplitudes.
- **`plot_fft_grid()`** — FFT magnitude spectrum per amplitude (up to `max_amps`, default 5), with the chosen `f_demod` peak marked and the Nyquist band shaded red, plus a summary panel of `f_demod` vs. amplitude.
- **`plot_amplitude_grid()`** — per-amplitude grid of frequency shift (raw + filtered), reconstructed flux `Φ_R`, and the normalised step response `s(t)`, with the normalisation window shaded.

Use this step to sanity-check demodulation before fitting — aliased or noisy `f_demod` choices are usually obvious in the FFT grid (peak inside the red Nyquist band).

Individual plots can also be called directly, e.g. `cryo.plot_fft_grid(max_amps=3)` or `cryo.plot_amplitude_grid(amp_indices=[0, 2])`.

---

## 4. Fitting the compensation kernel

```python
exp.fit_step_response(amplitude_index=0, update_coupler=True)
```

This fits a predistortion (compensation) kernel to the normalised step response `s(t)` and, if requested, writes it directly to the coupler's flux pulse parameters so subsequent pulses are pre-corrected.

**What it does:**

1. Selects the step response `s(t)` for the given `amplitude_index`.
2. Calls a helper to fit the kernel, which:
   - Rescales `s(t)` around 1 (currently a no-op rescale, `(s-1)*1+1`, kept as a hook for future tuning).
   - Fits a pole-zero model via `Flattenator.fit_step_response` (`num_poles=5`, `num_zeros=5`, `num_samples_missing=1`, with diagnostic plots shown).
   - Extracts the compensation kernel via `get_compensation_kernel()`.
3. If `update_coupler=True`, writes the kernel to:
   ```python
   cur_coupler_obj.Pulse['precomp_kernel'] = compensation_kernel
   ```
   where `cur_coupler_obj` is the `TunableTransmonCouplerFixed` HAL object identified from `qubit_ids` at construction time.
