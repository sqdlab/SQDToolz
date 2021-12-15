# ACQ Data Processing and Data Storage

## The processor model

The ACQ module is mainly a HAL object that retrieves data from lower driver-level objects. The complete raw data may not be useful for analysis and the actual data may be too large for feasible storage. Thus, it is useful to perform real-time post-processing on the data. The processor framework is designed to automatically queue incoming data, process them in a pipeline manner and eventually cache the results. The processor HAL object attaches onto an ACQ object via `ACQ.set_data_processor` and subsequently calling `ACQ.get_data` will automatically process and deliver the final datasets.

There are currently two processor classes given in `ProcCPU` and `ProcGPU` in which the processing is done on the CPU and GPU. Although CuPy should enable a universal syntax across platforms (for example, CuPy arrays are treated as numpy arrays on PCs without Nvidia graphics cards), the implementations are not necessarily the identical. For example, the CPU implementation could make use of CPU multithreading. In the future there may be a third class for grid-based processing via OpenMP or other post-processing nodes (note that FPGA preprocessing is a part of ACQ driver object and the ACQ driver object should appropriately pack the data).

To enable a list of post-processing nodes (for example, DDC, FIR etc.), the implementations are divided into their appropriate folders; being CPU and GPU at the moment inside the directory sqdtoolz/HAL/Processors. These nodes are child classes of the archetype prescribed in the associated files in `ProcCPU.py` and `ProcGPU.py` (being `ProcNodeCPU` and `ProcNodeGPU`). The node classes in general must implement:

- `input_format` - Returns a list of the indexing parameters expected in the last few indices in the input dataset
- `output_format` - Returns a list of the indexing parameters that will be output by the last few indices in this node
- `process_data` - Actual function to run the processing

Note that the error handling in the `process_data` function should be written in mind that the formats may change and one may wish to interchange the order of operations. Thus, unless it is explicitly required, the error-handling and subsequent operations should simply operate on the last few indices like 'sample' and 'segment'. In addition, note that in the future, the GPU processing structure may have an overhaul in which the individual nodes are no longer processed individually (that is, CPU-bound) and instead processed as a dynamically compiled pipeline such that any data fed into it automatically processes through the GPU pipeline without any CPU intervention (for example, with Nvidia CUDA, this pipeliningmay be achieved with DALI).


## Data passing

There cannot be a unified format for acquired data due to different instrument classes; for example, segmented capture of time-domain data from an ADC is distinctly different from frequency from a VNA. Thus, to signal the driver (mainly automated sections like data-storage), the datasets are passed in a dictionary with the following key structure:

- `data` - A *dictionary* of N-dimensional numpy arrays in which each key is the name of the output measurement
- `parameters` - A list of N strings representing the indexing through the ND-arrays
- `parameter_values` - A dictionary (can be empty) mapping parameters in `parameters` onto a list of values. If none are given, the values are enumerated via whole numbers.

Now take the example where two channels are measured as a time-series. The data may be accessed as follows:

```python
#Data from the ACQ driver is given in acq_data.
>>> acq_data['parameters']
  ['repetition', 'segment', 'sample']
>>> acq_data['data'].keys()
  ['ch1', 'ch2']

#Access repetition 1, segment 0, sample 29 on channel 2
>>> acq_data['data']['ch2'][1][0][29]
  13.6

...

#Now after processing through a DDC, the data is in final_data
>>> final_data['parameters']
  ['repetition', 'segment', 'sample']
>>> acq_data['data'].keys()
  ['ch1_I', 'ch1_Q', 'ch2_I', 'ch2_Q']

#Access repetition 61, segment 2, sample 63 on the Q-channel of channel 1
>>> acq_data['data']['ch1_Q'][61][2][63]
  0.42
```

The processor stages may process the data to produce a different dimensional array with new indexing parameters and thus, the dataset dictionary should reflect this change. Thus, the processor stages may utilise the `parameters` list to perform type-checking and error-handling before processing the data. Finally note that although it appears to add superfluous overhead, the performance of numpy or CuPy arrays should not be compromised and one should seek to make full generous use of the pass-by-reference standard. Thus, expect the input data packets to be modified - if this is undesirable, then ensure to pass on copies or make private copies...

The data packets may additionally hold other useful nuggets of information pertaining to their data type to give hints to the processors. For example, for frame-captured time-series data, the sample rate of the points is important when calculating the down-conversion sinusoids or performing appropriate filtering. Thus, under the key 'misc', one finds the key 'SampleRates' to help flag the channel sample-rates (that is, `acq_data['misc']['SampleRates']`). Note that this implies that the ACQ drivers must implement the following keys under 'misc' if returning frame-captured time-series data:

- `SampleRates` - List of sample rates of every channel in the captured time-series data (mostly just the same sample rates repeated across each channel).




