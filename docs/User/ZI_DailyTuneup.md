# Automated daily qubit tuneup with ZI

`ExpZIDailyTuneup` orchestrates a full daily maintenance/re-calibration routine for a single qubit, building on top of `ExpZISingleQubitTuneup`. It re-locks the $X$/$X/2$ gates, finds the optimal readout frequency and integration weights, re-characterises single-shot readout (blobs), optionally fine-tunes a two-qubit gate (2QG) with a coupled neighbour, re-measures $T_1$, and (optionally) saves the QPU configuration and a human/machine-readable summary. It assumes the qubit has already been through a full `ExpZISingleQubitTuneup.run()` at some point, and is intended to be run routinely (e.g. once per day) to correct for drift.

### Example

```python
from sqdtoolz.Experiments.Experimental.ExpZIDailyTuneup import ExpZIDailyTuneup

exp = ExpZIDailyTuneup('DailyTuneup', lab.CONFIG('ZI'), lab.HAL('QPU'), 'Q3', save_config=False)
exp.run(lab)
```

## Constructor arguments

`ExpZIDailyTuneup(name, expt_config, hal_QPU, qubit_id, **kwargs)`

- `name`: Name of this experiment, used as a prefix for all child experiment names.
- `expt_config`: The ZI experiment configuration (e.g. `lab.CONFIG('ZI')`).
- `hal_QPU`: The QPU HAL object (e.g. `lab.HAL('QPU')`).
- `qubit_id`: A single qubit ID, passed as a string (e.g. `'Q0'`).

Optional keyword arguments:
- `individual_plots`: Whether each sub-experiment shows its own plot as it runs. Also forwarded to the fine-tuneup step. Defaults to `False`.
- `update_params_live`: Whether measurement results are used to update qubit parameters as each step completes (readout optimisation, integration weights, $T_1$). Also forwarded to the fine-tuneup step. Defaults to `True`.
- `enable_ZI_log_messages`: Whether ZI logging is enabled during sub-experiments. Also forwarded to the fine-tuneup step. Defaults to `False`.
- `states`: Which qubit states to characterise/prepare — `'ge'`, `'ef'`, or `'gef'`. Also forwarded to the fine-tuneup step. Defaults to `'gef'`.
- `save_config`: Whether to save the QPU configuration to a timestamped JSON file at the end of the run (backing up any pre-existing file of the same name first). Defaults to `False`.
- `print_summary`: Whether to print a summary of the QPU's qubit parameters at the end of the run. Defaults to `True`.
- `save_summary_config_from_json`: Whether to generate a summary JSON (e.g. for a status webpage) from the saved config file. Automatically forced to `False` if `save_config` is `False`, since it depends on the saved config file. Defaults to `True`.
- `summary_json_file`: Output path for the summary JSON file. Defaults to `'{today's date, YYYYMMDD}_QPUsummary.json'`.
- `skip_2qg`: If `True`, skips the two-qubit gate fine-tuning step entirely. Defaults to `False`.
- `res_is_trough`: Whether the readout resonator response is a trough (vs. peak). Defaults to `True`.
- `update_qubits_by_fidelity`: Which readout fidelity metric to optimise against when picking the readout frequency — one of `'g'`, `'e'`, `'f'`, or `'mean'` (case-insensitive). Defaults to `'mean'`.
- `res_freq_range`: Explicit array of frequencies to sweep for readout optimisation, e.g. `res_freq_range=np.linspace(7.2e9, 7.3e9, 101)`. Cannot be combined with `res_freq_span`/`res_freq_points`.
- `res_freq_span`: Span (in Hz) of the readout frequency sweep, centred (asymmetrically — see note below) around the qubit's current `ReadoutFrequency`. Defaults to `10e6`. Cannot be combined with `res_freq_range`.
- `res_freq_points`: Number of points in the readout frequency sweep. Defaults to `101`. Cannot be combined with `res_freq_range`.

Any remaining keyword arguments (e.g. Ramsey, DRAG, or X-calibration parameters — see the `ExpZISingleQubitTuneup` fine tuneup documentation) are stored and forwarded directly to the internal `ExpZISingleQubitTuneup` instance used for the X-gate fine-tuning step.

## Measurement sequence

Calling `exp.run(lab)` runs the following steps in order:

1. **Fine-tune X gates:** Instantiates an `ExpZISingleQubitTuneup` (named `'{name}_{qubit_id}_FinetuneX'`) with all unconsumed keyword arguments, and calls `run_fine_tuneup(lab)` on it. Re-locks the qubit frequency (fine Ramsey), re-optimises the DRAG pulse, and recalibrates the $X$/$X/2$ gate amplitudes.
2. **Readout resonator:** Runs `ExpZIResOptimal` over `res_freq_range`/`res_freq_span` to find the readout frequency that maximises single-shot readout fidelity for the chosen `states`. If `update_params_live` is `True`, updates the qubit's readout frequency via `update_qubits_by_fidelity(update_qubits_by_fidelity)`.
3. **Blobs:** Runs `ExpZIBlobs` to re-characterise the single-shot readout distributions ("blobs") for the prepared `states`.
4. **Optimise integration weights:** Runs a qubit experiment using `time_traces` to re-optimise the readout integration weights, updating the qubit if `update_params_live` is `True`.
5. **2QG fine-tuning** *(skipped if `skip_2qg=True`)*: Searches the QPU for the first other qubit that shares a valid coupler with `qubit_id`, then runs `ExpZIFixedCouplerTuneup` on that qubit pair to fine-tune the two-qubit gate. If no coupled qubit is found, this step will error — set `skip_2qg=True` for qubits with no coupler in the QPU.
6. **$T_1$:** Runs `ExpZIT1` to re-measure the qubit's relaxation time, updating `T1GE` on the qubit if `update_params_live` is `True`.
7. **Save config / print summary:**
    - If `save_config` is `True`: saves the QPU configuration to a timestamped JSON file (`'{YYYYMMDD_HHMM}_QPU_config.json'`), first backing up any existing file of that name to `/Config_backups/`.
    - If `print_summary` is `True`: prints a summary of the QPU's qubit parameters via `qpu.print_summary_ZIQubits()`.
    - If `save_summary_config_from_json` is `True` (requires `save_config=True`): generates a summary JSON (e.g. for a status dashboard) from the just-saved config file, written to `summary_json_file`.

## Known issues to check before relying on this

A few things stood out while reading through the implementation that are worth verifying/fixing:

- **`datetime.now()` is used but not imported.** Only `from datetime import date` is imported at the top of the file, not `datetime`. The line `config_datestamp = datetime.now().strftime('%Y%m%d_%H%M')` inside the `save_config` block will raise a `NameError` when `save_config=True`. Likely fix: `from datetime import date, datetime` and use `datetime.now()`, or use `date.today()` if you don't need the time component.
- **`individual_plots`, `update_params_live`, `enable_ZI_log_messages`, and `states` use `kwargs.get(...)` instead of `kwargs.pop(...)`.** This means they're read but *not* removed from `kwargs`, so they'll also be present in `self._kwargs` and get passed a second time (redundantly, but not erroneously, since `ExpZISingleQubitTuneup` accepts the same keyword names) into the `ExpZISingleQubitTuneup(**self._kwargs)` call in step 1. This works today only because the receiving constructor happens to accept the same parameter names with the same meaning — if that ever changes, or if you want `self._kwargs` to only contain the truly "passthrough" arguments, switch these to `.pop(...)`.
- **2QG step has no coupled-qubit fallback.** If no other qubit in `self._qpu._qubits` shares a valid coupler with `qubit_id`, `coupled_qubit` is never assigned, and the subsequent `ExpZIFixedCouplerTuneup(..., [self._qubit_id, coupled_qubit], ...)` call will raise a `NameError` rather than a clear, actionable error. Consider raising a more descriptive exception (or auto-setting `skip_2qg=True` with a warning) when no coupled qubit is found.