# Recording extra parameters

There are cases where one wishes to (either solely or additionally) record the values of certain HAL parameters throughout the experiment (either once or in a [sweep](Exp_Sweep.md)). For example, if one wishes to record the measured current and voltage from a benchtop multimeter, there is no reason to create an elaborate ACQ structure.

To satisfy this use-case, there is an additional keyword argument `rec_params` passed into the `run_single` function (assuming that `lab` is a valid Laboratory object):

```python
#Create experiment object (it's temporary and not stored in lab) using configuration 'AutoExp'
exp = Experiment("Rabi", lab.CONFIG('AutoExp'))
#Run an experiment while recording the value of VAR 'current'
result = lab.run_single(exp, rec_params=[lab.VAR('current')])
#Run a sweep across the VAR 'cav_freq' while recording the value of VAR 'current' and the 'SenseVoltage' parameter of the HAL "SMU"
result = lab.run_single(exp, rec_params=[lab.VAR('current'), (lab.HAL("SMU"), 'SenseVoltage')])
```

Note that the CONFIG could have a blank ACQ (i.e. set to `None`); in this case, the `rec_params` are the only recorded values. In the above code, the syntax for `rec_params` is to give a list of entities to record:

- To record the value of a [VAR](Var_Defns.md), the object itself suffices.
- To record the property value of a HAL or WFMT, pass on the object and the property name as a tuple (similar to the syntax used in [VariableProperty](Var_Defns.md##VariableProperty)). 

Parameter values (taken to be univariate) recorded in `rec_params` are stored in a different file (so that it does not have to match the shape of the ACQ object in the CONFIG) named `'rec_params.h5'` in the [experiment folder](Exp_Overview.md##run). The shape of the array matches that of the specified sweeping parameters (a singleton if no sweeping parameters are specified). To retrieve the values, one may:

- Use [FileIOReader](Data_IO.md) on the `'rec_params.h5'` file.
- Use the file-handle from a completed experiment, use `exp.last_rec_params`

Note that `last_rec_params` is a `FileIOReader` object similar to `result`  (return value of `run_single` function) in the above code, except that it opens the `'rec_params.h5'` file as opposed to the normal ACQ data file (usually `'data.h5'`).
