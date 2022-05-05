# Overview of CPU Processors

To use a CPU processor, define a `ProcessorCPU` object, add the appropriate CPU processing stages and then attach it to an [ACQ HAL](ACQ.md). On doing so, any data acquired from said ACQ HAL will now output real-time processed data (which is subsequently [stored in the experiment](Exp_Overview.md)) as opposed to the raw data. Note that the resulting [Experiment Configuration object](Exp_Config_Basic.md) will store all the Processor configurations attached to any of its designated ACQ HAL objects and implement them during an experiment.

The following code demonstrates a possible implementation of a CPU data processor (assuming that `lab` has is a valid `Laboratory` object):


```python
import sqdtoolz as stz

...

#(A) - Create a CPU processor object.
stz.ProcessorCPU('ddcIntegCPU', lab)
#(B) - OPTIONALLY reset pipeline
lab.PROC('ddcIntegCPU').reset_pipeline()
#(C) - Add the processing stages
lab.PROC('ddcIntegCPU').add_stage(stz.CPU_DDC([25e6, 25e6]))
lab.PROC('ddcIntegCPU').add_stage(stz.CPU_FIR([{'Type' : 'low', 'Taps' : 128, 'fc' : 1e6, 'Win' : 'hamming'}]*4))
lab.PROC('ddcIntegCPU').add_stage(stz.CPU_Mean('sample'))
lab.PROC('ddcIntegCPU').add_stage(stz.CPU_Mean('segment'))
lab.PROC('ddcIntegCPU').add_stage_end(stz.CPU_Mean('repetition'))

#(D) - Attach the processor to an ACQ HAL
lab.HAL("TabACQ").set_data_processor(lab.PROC('ddcIntegCPU'))
```

The `ProcessorCPU` above can be fetched via its name: `lab.PROC('ddcIntegCPU')`. Now note the following features:
- (A) - The CPU object is created by giving it a unique name and a `Laboratory` object. Note that if it is recreated under the same name, its processing pipeline is NOT reset.
- (B) - A pipeline reset deletes all processing nodes in the main and end-stage pipelines.
- (C) - The real-time processing is done in the order prescribed on calling `add_stage` and `add_stage_end` commands. The details on setting up the individual CPU processing nodes is given [here](Proc_CPU_list.md).
- (D) - On [defining an ACQ HAL](ACQ.md) called `"TabACQ"`, one may attach the new CPU data processor via `set_data_processor`. To remove it later, pass `None` to the `set_data_processor` function.

Note that in the above example, one defines processing on the main pipeline and the end-stage pipeline. The difference is as follows:

- **Main Pipeline**
    - Added via: `add_stage`
    - Data is processed as data acquired - e.g. per repetition
- **End-Stage Pipeline**
    - Added via `add_stage_end`
    - Data is processed only once all data is acquired

In the above example, averaging across all repetitions cannot be done when only partial data (a few repetitions) has been acquired to which using `add_stage` will throw an error. Thus, while all other processing stages are done during data acquisition, the repetition average is done only once all repetitions (that is, complete acquisition) have been acquired.
