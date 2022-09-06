# Synthesising SQDToolz HDF5 data files

Experiments automatically generate data in the form of SQDToolz HDF5 files. However, there may be cases where the user wishes to modify a SQDToolz HDF5 file (e.g. to view in SQDViz). In such a case, there is a static utility function for ease of use in the `FileIOWriter` class. Here is a simple example of its usage:

```python
from sqdtoolz.Utilities.FileIO import FileIOWriter

data_array = np.zeros( (2,3,4,2) )
param_names = ["power", "frequency", "flux"]
param_vals = [np.array([-10,0]), np.array([0,1,2]), np.array([0,1,2,3])]
dep_param_names = ['rf_I', 'rf_Q']

FileIOWriter.write_file_direct('testFile.h5', data_array, param_names, param_vals, dep_param_names)
```

Note that the inputs must be valid as follows:
- Dimensions of `data_array` must match the number of `param_names` plus one (i.e. for the dependent parameters).
- Number of `dep_param_names` must match the size of the final dimension of `data_array`
- Size of `param_names` must match size of `param_vals` (both given as lists).
