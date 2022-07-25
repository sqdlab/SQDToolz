# Data Retrieval

Experiments generate data in the form of HDF5 files. Said data can be retrieved via the file-io utilities provided in the engine via a set of utility classes:

- [FileIOReader](#fileioreader)
    - [Basic usage](#basic-usage)
    - [Time-stamps](#time-stamps)
    - [One-many Parameters](#one-many-parameters)
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

### One-many Parameters

This refers to the parsing of datasets swept with parameters that are [one-many mappings](Exp_Sweep.md#one-many-sweeps). THe dataset will have the one-many parameters appear in the `param_names` as shown above with their `param_vals` simply being integers indexed from 0 to the number of tuples that it sweeps. To get the variables this one-many parameter sweeps along with their respective tuple values, the `FileIOReader` object will implement (if one-many parameters exist) the attribute `param_many_one_maps` which is a dictionary:

- Its keys are the names of the one-many parameters
- Each key contains a separate dictionary with the keys `'param_names'` and `'param_vals'`:
  - The key `'param_names'` contains an ordered list of the variables that are set by the given one-many parameter
  - The key `'param_vals'` contains a list, for every corresponding variable in `'param_names'`, of the values set in every swept step
- This attribute `param_many_one_maps` only exists if there is at least, one one-many parameter in the experiment's sweep

For example, consider the experiment:

``` python
#Create experiment object (it's temporary and not stored in lab) using configuration 'AutoExp'
exp = Experiment("Rabi", lab.CONFIG('AutoExp'))
#Run experiment with two sweeping parameters:
leData = lab.run_single(exp, [ (lab.VAR("wait_amps"), np.arange(0,0.3,0.1)), 
                                ('gateSet', [lab.VAR("A1"), lab.VAR("P1"), lab.VAR("A2"), lab.VAR("P2")],
                                  np.array([[1,0,3,-4], [4,-3,2,-2], [5,7,0,-1]])) ])
```

The following commands may be used to probe the stored data:

```python
#Get parameter names (that is, the parameters on each axis when slicing)
>>> leData.param_names
  ['wait_amps', 'gateSet']

#Get parameter values corresponding to each slicing axis
>>> leData.param_vals
  [array([0.0, 0.1, 0.2]),
   array([0, 1, 2])]

#Get the variables set by 'gateSet':
>>> leData.param_many_one_maps['gateSet']['param_names']
  ['A1', 'P1', 'A2', 'P2']

#Get the variables values by 'gateSet':
>>> leData.param_many_one_maps['gateSet']['param_names']
  [array([1,4,5]),
   array([0,-3,7]),
   array([3,2,0]),
   array([-4,-2,-1])]
```


## FileIODirectory

The `FileIODirectory` class amalgamates multiple datasets of similar experiments into a single array. This saves the user from having to manually look up the directory names and having to loop over them and manually construct the resulting array. The details on its usage are best explained in the article on [grouped experiments](Exp_CascadeGroup.md).

The syntax for data-retrieval in the `FileIODirectory` class is exactly the same as `FileIOReader`. Nonetheless, there are additional attributes of interest:

- `folders` - Corresponds to the folders from which data has been extracted.
- `folders_ignored` - Corresponds to the folders that were ignored during data extraction due to incomplete data or metadata (typically implies that the experiment failed to complete).
- `non_uniform` - If `True`, it refers to [non-uniform data sampling](ACQ_NonUniformDataSampling.md).

Note that the attribute `cur_folders` corresponds one-to-one with the resulting data array for the case where no sweeping variables have been used (in which case, the outer slicing variable is by a default index: `'DirFileNo'`).

There are also additional functions of interest:

- `get_var_dict_arrays()` - returns a dictionary across all available variable names. The value on each variable name in this dictionary is a numpy array corresponding to how the folders are sliced.

TO BE WRITTEN IN MORE DETAIL.

Finally, to handle the special case where the individual datasets are of different sizes, refer to the article on [Non-uniform data sampling](ACQ_NonUniformDataSampling.md).