# Non-uniform data sampling

## Issue

Usually one would sweep across multiple axes over some set of predetermined static intervals. This implies that the resulting dataset is a hypercube. However, there may be cases where one wishes to sample data dynamically. For example, one could sample uniformly across some parameter while taking a different interval across (non-uniformly) a second parameter. Although the default data-storage does not support this type of acquisition, one may take multiple striped experiments and utilise the `FileIODirectory` class to piece together the final dataset.

## Resolution

Consider the following examples of non-uniform data sampling:

``` python
#Assuming that lab is a Laboratory object

lab.group_open("nonuniform_experiment")
for f in range(3e6,6e6,1e6):
    exp = Experiment("testExp", lab.CONFIG('testConf'))
    res = lab.run_single( exp, [(lab.VAR("Freq"), np.arange(f))] )
lab.group_close()

lab.group_open("nonuniform_experiment")
for p in lab.VAR('Power').arange(-40,-80,-10):
    for f in lab.VAR('Flux').arange(4,6,1):
        exp = Experiment("testExp", lab.CONFIG('testConf'))
        res = lab.run_single( exp, [(lab.VAR("Freq"), np.arange(f*1e6))] )
lab.group_close()
```

In both examples, the variable 'Freq' sweeps over a dynamic range while the remaining variables sweep over a static range. The data will be stored in a directory with the usual time-stamp and name 'nonuniform_experiment'. Within said directory there will be multiple 'testExp' folders for each iteration. To retrieve the data, one would proceed via the file-handling utilities:

``` python
#From path
leData = FileIODirectory(r'...\2021-06-09\113134-nonuniform_experiment\113134-testExp\data.h5')
#Or equivalently from the last result FileIOReader object returned from the experiment...
leData = FileIODirectory.fromReader(res)

leData.get_numpy_array()
```

Although the syntax is the same for the amalgamation of uniformly sampled data files within a directory, the output is slightly different in the following ways:

- The flag `leData.non_uniform` is set to `True` and the attribute `uniform_indices` yields a boolean array of the parameters are are uniformly sampled.
- The returned dataset can be sliced immediately as per the indices given in `param_names` up to the file-level. That is, in the second example above, one can slice the 'Power' and 'Flux' variables in the array.
- However, at the file-level (everything within the sweeping-parameters given in the individual experiment; so, 'Freq' in the above example), one obtains a dictionary with two keys `param_vals` and `data` which both yield the usual list of parameter-values (for each slicing parameter) on slicing the remaining dataset and resulting uniform numpy-array respectively.

Note that the values within `param_vals` within each data dictionary (after slicing the outer indices amongst the different experiment files) will be different for the data is sampled non-uniformly. Finally, there is a handy utility to aid in plotting across multiple non-uniform datasets (that is, across different experiment files):

``` python
#Plot across channel 3 (index 2) with the axes being Flux and Freq (having Freq on the y-axis - hence the last argument being False)
pc = leData.get_rects_from_nonuniform_index('Flux', {'repetition':0, 'segment':0, 'sample':0, 'Power':1}, 2, False)

fig, ax = plt.subplots()
ax.add_collection(pc)
ax.autoscale()
plt.show()
```

Note that the polygon collection returned by the function is a bunch of quadrilaterals. Note that one cannot in general use `pcolormesh` without resampling the dataset to all unique x and y values. This is a common occurrence in the case where one wishes to sample N points across a differing interval. Thus, the grid is not a uniform rectangular grid. The slicing dictionary supplied to the function gives the indices for all remaining parameters in the amalgamated dataset. Finally, note that the function is only supported for a limited use case:

- It only supports the case where one axis parameter is a sweeping variable across multiple experiment files, otherwise, the desired dataset is within one experiment file and one may simple utilise numpy slicing to gather the required data array.
- One of the axes is by default the non-uniform dataset for otherwise, slicing across said dimension is in general ill-defined.
- There cannot be multiple non-uniform indices for once again, the slicing is in general ill-defined.

In fact, it is the ill-defined nature of non-uniformly sampled datasets and the ease of representation that has led to the solution prescribed above.
