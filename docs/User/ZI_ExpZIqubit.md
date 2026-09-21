# Using `ExpZIqubit` to run LabOne Q workflows

`ExpZIqubit` is a light wrapper class used to run LabOne Q workflows in the SQDtoolz environment. After an experiment configuration and QPU object have been initialised, we can setup an `ExpZIqubit` experiment as follows. [Documentation for LabOne Q workflows](https://docs.zhinst.com/labone_q_user_manual/applications_library/how-to-guides/sources/01_superconducting_qubits/index.html) should be referred to for experiment options. [Custom ZI-style workflows](#custom-zi-style-workflows) can also be run inside `ExpZIqubit` (see `.py` files in `Experiments/Experimental/ZI`).

### Running a simple single qubit workflow
Here, we run the LabOne Q workflow `qubit_spectroscopy` on `Q0`, which is an object in our `lab.HAL('QPU)`. Experiment parameters (in this case `frequencies`) are passed as keyword arguments, and are handled by the ExpZIqubit class.

```python
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from laboneq_applications.experiments import qubit_spectroscopy

ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')

exp = ExpZIqubit('QubitSpec', lab.CONFIG('ZI'), qubit_spectroscopy, lab.HAL('QPU'), ['Q0'], frequencies=[np.linspace(5.8e9, 6.2e9, 101)])
lab.run_single(exp)
```

When executing `lab.run_single(exp)`, the hardware execution time is printed. Data is saved to the `lab`'s data directory as for all other SQDtoolz experiments, along with a pulse sheet and text files containing experiment configuration information. 

### Passing multiple qubit objects
The experiment can be performed on multiple qubits by passing a list of qubits `['Q0', 'Q1']` to `ExpZiqubit` (instead of the single `[Q0]` in the above example). Simulated experiments - making use of LabOne Q's emulation mode - can be run by setting `lab.run_single(exp, debug_skip_experiment=True)`, as in the following example of a `single_qubit_gates` workflow.

```python
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ZI import single_qubit_gates

ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')

exp = ExpZIqubit('test', lab.CONFIG('ZI'), single_qubit_gates, lab.HAL('QPU'), 
    ['Q0', 'Q1'], gate_lists=[['X','Y'],['X','Z/2','H','Y',('Rx',0.1)]])
lab.run_single(exp, debug_skip_experiment=True)
```
### Custom ZI-style workflows
Custom workflows defined in the style of LabOneQ workflows (found in `sqdtoolz/Experiments/Experimental/ZI)`) can also be passed to `ExpZIqubit`.

### Sweeping experiment variables
We can also sweep an experiment variable in the `run_single()` call of an `ExpZIqubit`, as shown in the below example of a resonator spectroscopy power sweep.

```python
import sqdtoolz as stz
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from laboneq_applications.experiments import resonator_spectroscopy

stz.VariableProperty('resAmp_Q0', lab, lab.HAL('Q0'), 'ReadoutAmplitude')

exp = ExpZIqubit('resPower', lab.CONFIG('ZI'), resonator_spectroscopy, 
    lab.HAL('QPU'), ['Q0'],  frequencies=np.linspace(7.1e9, 7.2e9, 1001))
lab.run_single(exp, [(lab.VAR('resAmp_Q0'), np.linspace(0.01, 0.9, 20))])
```

### Keyword arguments

`ExpZIqubit.__init__(name, expt_config, workflow_module, hal_QPU, qubit_ids, **kwargs)` recognises the following keyword arguments; anything else is stored in `self._args` and is either forwarded on to the LabOne Q workflow's `create_experiment` call (if it's a parameter of that function, e.g. `frequencies` in the examples above) or, failing that, applied directly to the workflow's `options` object if it happens to expose a matching attribute (e.g. a workflow-specific option that isn't one of the generic ones listed below).

| Argument | Type / Default | Description |
|---|---|---|
| `update` | `bool`, default `False` | Forwarded to `options.update(...)` (if the workflow exposes it) — whether the workflow updates qubit parameters from its fitted results. |
| `use_cal_traces` | `bool`, default `True` | Forwarded to `options.use_cal_traces(...)` (if exposed) — whether calibration traces are used to normalise the readout data. |
| `transition` | `str`, default `'ge'` | Forwarded to `options.transition(...)` (if exposed) — which qubit transition the workflow targets. |
| `ZI_plot` | `bool`, default `False` | Whether LabOne Q's own analysis figures are left open (`options.close_figures(not ZI_plot)`, if exposed). Setting this `True` forces `skip_ZI_analysis` to `False`, since the analysis workflow must run in order to produce a plot. |
| `skip_ZI_analysis` | `bool`, default `True` | Forwarded to `options.do_analysis(not skip_ZI_analysis)` (if exposed) — whether the workflow's own (LabOne Q-side) analysis/fitting step runs at all, independently of SQDtoolz's own data saving/analysis. |
| `cal_states` | `str`, default: falls back to `transition` | Forwarded to `options.cal_states(...)` (if exposed) — which states the calibration traces prepare. Only relevant when `use_cal_traces=True`. Unlike the other options above, this one is read with `self._args.get(...)` rather than popped, so if the underlying workflow also exposes an attribute literally named `cal_states`, it can be applied a second time via the generic passthrough loop described above. |
| `show_pulse_sheet` | `bool`, default `False` | Popped into `self._show_pulse_sheet` in the constructor, but **not currently referenced anywhere in `_run`** — it has no effect. The actual switch that controls whether a pulse sheet is generated is the `print_pulse_sheet` run-time argument below (passed to `lab.run_single(...)`, not to the constructor). |

The following are not constructor arguments — they're read inside `_run`/`_estimate_experiment_params` via `kwargs.get(...)`/`kwargs.pop(...)`, so they're passed to `lab.run_single(exp, ...)` instead (as in the `debug_skip_experiment=True` example above):

| Argument | Type / Default | Description |
|---|---|---|
| `override_ACQ_params` | `dict`, default `{}` | Each key/value pair is applied as `setattr(hal_ACQ, key, value)` on the `ZIACQ` HAL before the workflow's options are built — a quick way to override acquisition parameters (e.g. `NumRepetitions`) for a single run without changing the HAL permanently. |
| `disable_ZI_logging` | `bool`, default `False` | If `True`, suppresses LabOne Q/`laboneq` logging output for the duration of the run. |
| `debug_skip_experiment` | `bool`, default `False` | Connects the ZI session in emulation mode (`do_emulation=True`) and, unless `debug_skip_experiment__run=True`, still builds and runs the (emulated) experiment — printing `"ZI Emulating experiment"` — rather than skipping it outright. |
| `debug_skip_experiment__run` | `bool`, default `False` | Only relevant alongside `debug_skip_experiment=True`: if both are `True`, the experiment workflow is constructed but never executed at all (prints `"Not running experiment"` and returns immediately). |
| `quick_query` | `bool`, default `False` | If `True`, skips building/running the full experiment workflow and instead just calls `prepare_instruments()`/`get_data()` directly on the experiment configuration — useful for a fast instrument read without a full sequence. |
| `skip_timing_diagram` | `bool`, default `False`/unset | If truthy, skips the pulse-sheet generation and execution-time estimation step entirely (see `_estimate_experiment_params`). |
| `min_buffer_between_acquisitions` | `float`, default `40e-9` | Minimum required time spacing between acquisition triggers on any one qubit; asserted to be at least `20e-9` (the ZI hardware team's recommended minimum) and checked against the compiled pulse sheet when the timing diagram is generated. |
| `print_pulse_sheet` | `bool`, default `True` | Whether to generate and save the pulse-sheet timing diagram (both the LabOne Q pulse-sheet viewer HTML and the raw per-channel Bokeh plot). This is the argument that actually controls pulse-sheet generation — not the constructor's `show_pulse_sheet`. |
| `print_estimated_execution_time` | `bool`, default `True` | Whether to print the experiment's estimated hardware execution time before running. |
| `raw_pulse_sheet_duration` | `float`, default `100e-6` | Time window (from `t=0`) plotted in the raw per-channel pulse-sheet HTML. |

### `normalise_qubit_data` (static method)

`ExpZIqubit.normalise_qubit_data(fileioreader_calib, transition)` is a small static helper used elsewhere (e.g. by other `ExpZI*` experiment classes) to build a `DataIQNormalise` object from a `FileIOReader` of calibration-trace data. `transition` is a two-character string (e.g. `'ge'`, `'ef'`) whose two characters are matched as prefixes against `fileioreader_calib.dep_params` to select the "0"-state and "1"-state calibration columns, which are then passed to `DataIQNormalise` for IQ-blob normalisation of subsequent shots.
