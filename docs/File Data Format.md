# File Data Format

The HDF5 file format is great for storing large chunks of contiguous numerical data and thus, the chosen format for SQDToolz. The H5 file holds the N-dimensional array data along with the parameter names and slicing indices to help extract data.

## Basic format

The main data lives inside the dataset called `data` which is a 2D array:

- Rows equal to the product of slicing dimensions
- Columns equal to the number of output channels (dependent variables)

For example, if one sweeps across 10 points in frequency, 9 points in flux and 8 points in power, then the data array would have 720 rows in which one may slice it via the usual meshgrid convention. That is, one may effectively reshape the array via `np.reshape(data_array, (10,9,8, num_outputs))` (noting that `num_outputs` is the number of columns in the initial array) and then start indexing it via frequency, flux and power to obtain the values across the channel outputs via a final index across the columns.

Thus, to deconstruct the data array, one requires the slicing indices (along with the indexing parameter names) and the channel output names across the column indices. This information is stored in the HDF5 file over two data groups:

- `parameters` (the independent variables)
    - Holds the indexing parameters needed to slice the rows of the data array
    - Each dataset's name corresponds to the indexing parameter
    - The actual data is a 1D array
    - Since HDF5's specification does not guarantee the preservation of dataset ordering, the dimensional slicing index, is stored in the first slot of the 1D array
    - The remaining entries of the array correspond to the parameter values when slicing a particular zero-based index
- `measurements` (the dependent variables)
    - Since HDF5 does not natively support the storage of string arrays, the names of the output channels corresponding to the data columns are given in datasets
    - Each dataset's name corresponds to the channel output name
    - Since HDF5's specification does not guarantee the preservation of dataset ordering, the dimensional slicing index, is stored in the data as a singleton.



