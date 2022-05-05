# Overview of GPU Processors

Before using a GPU Processor, take note of the following:

- The computer must have an Nvidia CUDA enabled GPU - otherwise, it will utilise normal CPU-bound `numpy` functions instead of the `cupy` functions.
- Make sure the latest stable version of CUDA has been installed on the computer.

To use a GPU processor, define a `ProcessorGPU` object, add the appropriate GPU processing stages and then attach it to an [ACQ HAL](ACQ.md). On doing so, any data acquired from said ACQ HAL will now output real-time processed data (which is subsequently [stored in the experiment](Exp_Overview.md)) as opposed to the raw data. Note that the resulting [Experiment Configuration object](Exp_Config_Basic.md) will store all the Processor configurations attached to any of its designated ACQ HAL objects and implement them during an experiment.

The following code demonstrates a possible implementation of a GPU data processor (assuming that `lab` has is a valid `Laboratory` object):


```python
import sqdtoolz as stz

...

#(A) - Create a GPU processor object.
stz.ProcessorGPU('ddcIntegGPU', lab)
#(B) - OPTIONALLY reset pipeline
lab.PROC('ddcIntegGPU').reset_pipeline()
#(C) - Add the processing stages
lab.PROC('ddcIntegGPU').add_stage(stz.GPU_DDC([25e6, 25e6]))
lab.PROC('ddcIntegGPU').add_stage(stz.GPU_FIR([{'Type' : 'low', 'Taps' : 128, 'fc' : 1e6, 'Win' : 'hamming'}]*4))
lab.PROC('ddcIntegGPU').add_stage(stz.GPU_Mean('sample'))
lab.PROC('ddcIntegGPU').add_stage(stz.GPU_Mean('segment'))
lab.PROC('ddcIntegGPU').add_stage_end(stz.GPU_Mean('repetition'))

#(D) - Attach the processor to an ACQ HAL
lab.HAL("TabACQ").set_data_processor(lab.PROC('ddcIntegGPU'))
```

The `ProcessorGPU` above can be fetched via its name: `lab.PROC('ddcIntegGPU')`. Now note the following features:
- (A) - The GPU object is created by giving it a unique name and a `Laboratory` object. Note that if it is recreated under the same name, its processing pipeline is NOT reset.
- (B) - A pipeline reset deletes all processing nodes in the main and end-stage pipelines.
- (C) - The real-time processing is done in the order prescribed on calling `add_stage` and `add_stage_end` commands. The details on setting up the individual GPU processing nodes is given [here](Proc_GPU_list.md).
- (D) - On [defining an ACQ HAL](ACQ.md) called `"TabACQ"`, one may attach the new GPU data processor via `set_data_processor`. To remove it later, pass `None` to the `set_data_processor` function.

Note that in the above example, one defines processing on the main pipeline and the end-stage pipeline. The difference is as follows:

- **Main Pipeline**
    - Added via: `add_stage`
    - Data is processed as data acquired - e.g. per repetition
- **End-Stage Pipeline**
    - Added via `add_stage_end`
    - Data is processed only once all data is acquired

In the above example, averaging across all repetitions cannot be done when only partial data (a few repetitions) has been acquired to which using `add_stage` will throw an error. Thus, while all other processing stages are done during data acquisition, the repetition average is done only once all repetitions (that is, complete acquisition) have been acquired.
