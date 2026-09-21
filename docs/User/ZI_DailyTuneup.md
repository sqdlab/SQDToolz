# Automated daily qubit tuneup with ZI

`ExpZIDailyTuneup` orchestrates a full daily maintenance/re-calibration routine for a single qubit, building on top of `ExpZISingleQubitTuneup`. It re-locks the $X$/$X/2$ gates, (optionally) finds the optimal readout frequency, re-optimises integration weights and re-characterises single-shot readout (blobs), re-measures $T_1$, optionally fine-tunes a two-qubit gate (2QG) with a coupled neighbour, optionally runs single-qubit randomised benchmarking and (if a coupled qubit was found) two-qubit Bell-state fidelity, and (optionally) saves the QPU configuration and a human/machine-readable summary. It assumes the qubit has already been through a full `ExpZISingleQubitTuneup.run()` at some point, and is intended to be run routinely (e.g. once per day) to correct for drift.

### Example

```python
from sqdtoolz.Experiments.Experimental.ExpZIDailyTuneup import ExpZIDailyTuneup

exp = ExpZIDailyTuneup('DailyTuneup', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q3', save_config=False)
exp.run(lab)
```

## Constructor arguments

`ExpZIDailyTuneup(name, expt_config, hal_QPU, qubit_id, **kwargs)`

- `name`: Stored as `self._name`, but not currently used by `run()` — every sub-experiment's name is built from the hardcoded literal `'DailyTuneup'` (e.g. `f'DailyTuneup_{qubit_id}_FinetuneX'`), not from this argument. Pass any string; it has no effect on the routine's behaviour or output filenames.
- `expt_config`: The ZI experiment configuration (e.g. `lab.CONFIG('ZI')`).
- `hal_QPU`: The QPU HAL object (e.g. `lab.HAL('QPU')`).
- `qubit_id`: A single qubit ID, passed as a string (e.g. `'Q0'`).

Optional keyword arguments:
- `tune_readout`: If `True`, runs the readout-resonator optimisation, integration-weight optimisation, and (if `update_params_live`) the blobs fidelity check. If `False`, all three steps are skipped. Defaults to `True`.
- `individual_plots`: Whether each sub-experiment shows its own plot as it runs. Also forwarded to the fine-tuneup step. Defaults to `False`.
- `update_params_live`: Whether measurement results are used to update qubit parameters as each step completes (readout optimisation, blobs, integration weights, $T_1$, 2QG, benchmarking fidelity, Bell-state fidelity). Also forwarded to the fine-tuneup step. Defaults to `True`.
- `enable_ZI_log_messages`: Stored but not directly referenced in `run()` (each sub-experiment manages its own ZI logging). Also forwarded to the fine-tuneup step. Defaults to `False`.
- `states`: Which qubit states to characterise/prepare — `'ge'`, `'ef'`, or `'gef'`. Also forwarded to the fine-tuneup step. Defaults to `'gef'`.
- `save_config`: Whether to save the QPU configuration to a timestamped JSON file at the end of the run (backing up any pre-existing file of the same name first). Defaults to `False`.
- `print_summary`: Whether to print a summary of the QPU's qubit parameters at the end of the run. Defaults to `True`.
- `save_summary_config_from_json`: Whether to generate a summary JSON (e.g. for a status webpage) from the saved config file. Automatically forced to `False` if `save_config` is `False`, since it depends on the saved config file. Defaults to `True`.
- `summary_json_file`: Output path for the summary JSON file. Defaults to `'{today's date, YYYYMMDD}_QPUsummary.json'`.
- `skip_2qg`: If `True`, skips both the two-qubit gate fine-tuning step and the Bell-state fidelity step entirely. Defaults to `False`.
- `res_is_trough`: Stored (`self._res_trough`) but not directly referenced in `run()`. Defaults to `True`.
- `update_qubits_by_fidelity`: Which readout fidelity metric to optimise against when picking the readout frequency — one of `'g'`, `'e'`, `'f'`, or `'mean'` (case-insensitive). Defaults to `'mean'`.
- `res_freq_range`: Explicit array of frequencies to sweep for readout optimisation, e.g. `res_freq_range=np.linspace(7.2e9, 7.3e9, 101)`. Cannot be combined with `res_freq_span`/`res_freq_points`.
- `res_freq_span`: Span (in Hz) of the readout frequency sweep, centred (asymmetrically — see note below) around the qubit's current `ReadoutFrequency`. Defaults to `10e6`. Cannot be combined with `res_freq_range`.
- `res_freq_points`: Number of points in the readout frequency sweep. Defaults to `101`. Cannot be combined with `res_freq_range`.
- `chevron_amp_pts`: Number of flux-amplitude points (`flux_amp_points`) passed to the `ExpZIFixedCouplerTuneup` sub-experiment during the two-qubit gate step. Defaults to `17`.
- `chevron_amp_span`: Flux-amplitude span (`flux_amp_span`) passed to the same sub-experiment. Defaults to `0.03`.
- `skip_benchmarking`: If `True`, skips both the single-qubit randomised-benchmarking step and (as a consequence) the Bell-state fidelity step, since the latter is only attempted inside the former's `if` block. Defaults to `False`.
- `rb_sequence_lengths`: Sequence lengths (`sequence_lengths`) passed to `ExpZIRandomisedBenchmarking`. Defaults to `[4, 8, 16, 32, 64, 128]`.
- `rb_num_trials`: Number of random sequences per length (`num_trials`) passed to the same sub-experiment. Defaults to `6`.

Any remaining keyword arguments (e.g. Ramsey, DRAG, or X-calibration parameters — see the `ExpZISingleQubitTuneup` fine tuneup documentation) are stored and forwarded directly to the internal `ExpZISingleQubitTuneup` instance used for the X-gate fine-tuning step. Note that `individual_plots`, `update_params_live`, `enable_ZI_log_messages`, and `states` are read with `kwargs.get(...)` rather than `kwargs.pop(...)`, so they remain in `self._kwargs` and get forwarded a second time alongside the other passthrough arguments — see "Known issues" below.

## Measurement sequence

Calling `exp.run(lab)` runs the following steps in order:

1. **Fine-tune X gates:** Instantiates an `ExpZISingleQubitTuneup` (named `f'DailyTuneup_{qubit_id}_FinetuneX'`) with all unconsumed keyword arguments, and calls `run_fine_tuneup(lab)` on it. Re-locks the qubit frequency (fine Ramsey), re-optimises the DRAG pulse, and recalibrates the $X$/$X/2$ gate amplitudes.
2. **Readout resonator** *(skipped if `tune_readout=False`)*: Runs `ExpZIResOptimal` over `res_freq_range`/`res_freq_span` to find the readout frequency that maximises single-shot readout fidelity for the chosen `states`. If `update_params_live` is `True`, updates the qubit's readout frequency via `update_qubits_by_fidelity(update_qubits_by_fidelity)`.
3. **Optimise integration weights** *(skipped if `tune_readout=False`)*: Runs a qubit experiment using `time_traces` to re-optimise the readout integration weights, updating the qubit if `update_params_live` is `True`.
4. **Blobs** *(skipped if `tune_readout=False` or `update_params_live=False`)*: Runs `ExpZIBlobs` to re-characterise the single-shot readout distributions ("blobs") for the prepared `states`.
5. **$T_1$:** Runs `ExpZIT1` to re-measure the qubit's relaxation time, updating `T1GE` on the qubit if `update_params_live` is `True`.
6. **2QG fine-tuning** *(skipped if `skip_2qg=True`, or silently skipped if no coupled qubit is found)*: Searches the QPU for the first other qubit that shares a valid coupler with `qubit_id`. If one is found, runs `ExpZIFixedCouplerTuneup` on that qubit pair (using `chevron_amp_pts`/`chevron_amp_span`) to fine-tune the two-qubit gate. If none is found, this step is simply skipped — it no longer errors (see "Known issues" below for the historical behaviour).
7. **Randomised benchmarking** *(skipped if `skip_benchmarking=True`)*: Runs `ExpZIRandomisedBenchmarking` (using `rb_sequence_lengths`/`rb_num_trials`) to measure single-qubit gate fidelity.
8. **Bell-state fidelity** *(only runs if step 7 ran, `skip_2qg=False`, and a coupled qubit was found in step 6)*: Runs `ExpZIBellStateFidelity` on the qubit pair to measure two-qubit Bell-state fidelity.
9. **Save config / print summary:**
    - If `print_summary` is `True`: prints a summary of the QPU's qubit parameters via `qpu.print_summary_ZIQubits()`.
    - If `save_config` is `True`: saves the QPU configuration to a timestamped JSON file (`'{YYYYMMDD_HHMM}_QPU_config.json'`), first backing up any existing file of that name to `/Config_backups/`.
    - If `save_summary_config_from_json` is `True` (requires `save_config=True`, and is forced `False` otherwise): generates a summary JSON (e.g. for a status dashboard) from the just-saved config file, written to `summary_json_file`.

## Known issues to check before relying on this

A few things stood out while reading through the implementation that are worth being aware of:

- **`individual_plots`, `update_params_live`, `enable_ZI_log_messages`, and `states` use `kwargs.get(...)` instead of `kwargs.pop(...)`.** This means they're read but *not* removed from `kwargs`, so they'll also be present in `self._kwargs` and get passed a second time (redundantly, but not erroneously, since `ExpZISingleQubitTuneup` accepts the same keyword names) into the `ExpZISingleQubitTuneup(**self._kwargs)` call in step 1. This works today only because the receiving constructor happens to accept the same parameter names with the same meaning — if that ever changes, or if you want `self._kwargs` to only contain the truly "passthrough" arguments, switch these to `.pop(...)`.

Two issues previously noted in this section — a missing `datetime` import that would raise a `NameError` when `save_config=True`, and a missing coupled-qubit fallback that would raise a `NameError` in the 2QG step when no coupler was found — have since been fixed in the source (`datetime` is imported as a module and used correctly, and the 2QG step is now guarded by `if coupled_qubit is not None:`, so it degrades gracefully to a no-op instead of erroring).
