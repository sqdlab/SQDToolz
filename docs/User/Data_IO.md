# Data Retrieval

Experiments generate data in the form of HDF5 files. Said data can be retrieved via the file-io utilities provided in the engine via a set of utility classes:

- [FileIOReader](#fileioreader)
    - [Basic usage](#basic-usage)
    - [Time-stamps](#time-stamps)
- [FileIODirectory](#fileiodirectory)

When using these classes, the user need not write low-level HDF5 file-retrieval commands. Note that the utilities do not require a running `Laboratory` and thus, one may retrieve data by simply importing the required class as shown in the examples below.

## FileIOReader

Data can be read from the HDF5 file via the `FileIOReader` class or taken from the return-value on [running an experiment](Exp_Overview.md):

```python
from sqdtoolz.Utilities.FileIO import FileIOReader

#Fetch the data from a file
leData = FileIOReader(r'Z:\Data\EH_QuantumClock_V2\2021-07-12\202908-rabi\data.h5')

#Get the data from running an experiment
exp = Experiment("Rabi", lab.CONFIG('AutoExp'))
leData = lab.run_single(exp)
```

Note that the raw data is not read and parsed into RAM; this is simply retrieving the metadata. So even if it is a monster data file, it should run fast. In fact, the returned object on running an experiment is a `FileIOReader` object that has been automatically constructed on the HDF5 file freshly created by the experiment.

### Basic usage

The data is typically packed as an ND-array. To slice/index the array, one may query the relevant metadata as follows:

```python
#Get parameter names (that is, the parameters on each axis when slicing)
>>> leData.param_names
  ['power', 'frequency']

#Get parameter values corresponding to each slicing axis
>>> leData.param_vals
  [array([-5, -10, -15, -20, -25, -30]),
   array([0., 2000, 4000, ...,
          998000, 1000000])]

#Get dependent parameters (that is, the last few slicing indices)
>>> leData.param_names
  ['rf_I', 'rf_Q']
```

To retrieve the actual ND-array and thus, parsing the data into RAM, one may use the `get_numpy_array` function:

```python
#Get the ND array
arr = leData.get_numpy_array()

#Get all the I-channel values for the first power and all frequencies
i_vals_power_minus5 = arr[0][:][0]
#Get all the Q-channel values for the first power and all frequencies
q_vals_power_minus5 = arr[0][:][1]
```

Notice that there are 3 slicing indices/axes in the ND-array. Here, the first two axes are for the independent sweeping parameters: `'power'` and `'frequency'`. The last slicing axis is to slice the dependent variables; in this example, the size of this dimension is 2 for `rf_I` and `rf_Q` values. When plotting, one may use the `param_vals` attribute to fetch the axis values, while using the sliced array values to plot the resulting dataset.

### Time-stamps

For each point of data in the ND-array, there is an associated time-stamp that is recorded during the experiment. This is useful when correlating the results with the time-frames over which the experiment was run:

```python
#Retrive the ND time-stamp array
tsArr = leData.get_time_stamps()

#Get the time-stamps for the first power and its frequencies
ts_vals_first_power = arr[0][:]
```

Note that the ND-array of time-stamps is sliced over the independent sweeping parameters: `'power'` and `'frequency'`. Each time-stamp in the ND-array is a `numpy.datetime64` object:

```python
#Get the first time-stamp:
>>> ts_first = arr[0][0]
  numpy.datetime64('2021-11-19T16:05:59.253367')
```

## FileIODirectory

The `FileIODirectory` class amalgamates multiple datasets of similar experiments into a single array. This saves the user from having to manually look up the directory names and having to loop over them and manually construct the resulting array. The details on its usage are best explained in the article on [grouped experiments](Exp_CascadeGroup.md).

The syntax for data-retrieval in the `FileIODirectory` class is exactly the same as `FileIOReader`. For the handling of the case where the individual datasets are of different sizes, refer to the article on [Non-uniform data sampling](ACQ_NonUniformDataSampling.md).
