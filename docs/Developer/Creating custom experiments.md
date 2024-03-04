# Creating custom experiments

`Experiments/Experimental` contains a library of custom experiments. It is encouraged that any custom experiments made (which may be useful to others) are formalised into an class which inherits from `Experiment`, and deposited here. In this way a library of useful subroutines can build over time. The easiest way to learn the structure of these objects is probably to peruse the existing ones, and adapt the closest one to your own.

## Overview

A custom experiment will inherit from the underlying Experiment class following:

```
from sqdtoolz.Experiment import *
class Custom_Experiment(Experiment):
	def__init__(self, ...):

	def _run(self, ...):

	def _post_process(self, ...):

```

As you can see there are three necessary methods: 
- `__init__()` 
- `_run()` 
- `_post_process()`

There are exceptions to this workflow where `_post_process()` is substituted with more technical alternatives. This is probably a topic for other docs.

### \_\_init__()
This should accept name (an experiment name) and expt_config (an experiment config) as arguments, for starters. Then, use these to initialise the underlying Experiment class in the normal way, and prepare instruments accordingly, via `super().__init__(name, expt_config)` 

Subsequent arguments are dependent on the experiment being designed. Typically there will be some default arguments which are required to parametrise the experiment, and then a catch-all `**kwargs` argument for optional parameters.

This function should be used to initialise all the configurable parameters for the experiment. For example, in a T1 experiment, the user provides:
- `wfmt_qubit_drive`
- `range_waits`
- `SPEC_qubit`

These are the specific waveform transformation (which abstracts the IQ modulation details), range of wait times (which define the x-axis for a T1 experiment) and relevant qubit frequency/gate parameters (which define the $\pi$-pulse required for a T1 experiment). 

Within `__init__()`, these are simply stored for later use by the `_run()` functionality, by
- `self._wfmt_qubit_drive = wfmt_qubit_drive`
- `self._range_waits = range_waits`
- `self._SPEC_qubit = SPEC_qubit`

### \_run()
The run function should contain the meat of the routine.

It has arguments 
- `file_path`
- `sweep_vars`
- `**kwargs`

to satisfy the inherited `Experiment._run()` class. Usually, `sweep_vars` is not used as the variable to sweep is hardcoded in the experiment itself.

In this function, initialise the instruments as per the provided `expt_config` by `self._expt_config.init_instruments()`. For time-domain experiments the developer will subsequently define a relevant waveform, setting up the pulses, measurements, and padding needed.

The variable/s to sweep (e.g. for a T1 experiment, it is wait time) are then defined as
`sweep_vars = [(some_var, some_list_of_values),...]`
where `some_var` is typically a hard-coded feature of the experiment and `some_list_of_values` was provided by the user at initialisation.

The experiment is then run through the underlying Experiment class, typically following the pattern

```python
kwargs['skip_init_instruments'] = True
self._cur_param_name = some_var.Name
self._file_path = file_path
return super()._run(file_path, sweep_vars, **kwargs)
```
where the param name and file path are saved for reference in post processing.

### \_post_process()
Simply accepts `data` as a default argument. The role of this function is to turn the raw data into results, presented in a manner chosen by the developer.

This often involves importing a convenient fitter from `from sqdtoolz.Utilities.DataFitting import *` , generating a plot with `matplotlib` and either yielding some fit parameters or committing them to the qubit spec following
`self._SPEC_qubit[parameter_name].Value = fit_param[n]`

If useful plots are created, it is also handy to save these in the data folder, stored in `self._file_path`. This can be very convenient for searching through experiments later.
