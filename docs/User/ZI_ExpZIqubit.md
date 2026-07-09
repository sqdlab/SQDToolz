# Using `ExpZIqubit` to run LabOne Q workflows

`ExpZIqubit` is a light wrapper class used to run LabOne Q workflows in the SQDtoolz environment. After an experiment configuration and QPU object have been initialised, we can setup an `ExpZIqubit` experiment as follows.

Here, we run the LabOne Q workflow `qubit_spectroscopy` on `Q0`, which is an object in our `lab.HAL('QPU)`. Experiment parameters (in this case `frequencies`) are passed as keyword arguments, and are handled by the ExpZIqubit class.

```python
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from laboneq_applications.experiments import qubit_spectroscopy

ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')

exp = ExpZIqubit('QubitSpec', lab.CONFIG('ZI'), qubit_spectroscopy, lab.HAL('QPU'), ['Q0'], frequencies=[np.linspace(5.8e9, 6.2e9, 101)])
lab.run_single(exp, debug_skip_experiment=False, disable_ZI_logging=True)
```

When executing `lab.run_single()`, the hardware execution time is printed. Data is saved to the `lab`'s data directory as for all other SQDtoolz experiments, along with a pulse sheet and text files containing experiment configuration information. 

The experiment can be performed on multiple qubits by passing a list of qubits `['Q0', 'Q1']` to `ExpZiqubit` (instead of the single `[Q0]` in the above example). Simulated experiments - making use of LabOne Q's emulation mode - can be run by setting `lab.run_single(exp, debug_skip_experiment=True)`, as in the following example of a `single_qubit_gates` workflow.

```python
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ZI import single_qubit_gates

ExperimentConfiguration('ZI', lab, 0, [], 'ZIacq')

exp = ExpZIqubit('test', lab.CONFIG('ZI'), single_qubit_gates, lab.HAL('QPU'), ['Q0', 'Q1'], gate_lists=[['X','Y'],['X','Z/2','H','Y',('Rx',0.1)]])
lab.run_single(exp, debug_skip_experiment=True)
```

Custom workflows defined in the style of LabOneQ workflows (found in `sqdtoolz/Experiments/Experimental/ZI)`) can also be passed to `ExpZIqubit`.

Documentation for LabOne Q workflows can be found [here](https://docs.zhinst.com/labone_q_user_manual/applications_library/how-to-guides/sources/01_superconducting_qubits/index.html). 
