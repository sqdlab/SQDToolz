# Overview of FPGA Processors

Before using a FPGA Processor, take note of the following:

- The ACQ instrument must be a pipelined FPGA that is compatible with the FPGA processor framework
- The processors do not implment `push_data` and thus, cannot be used to process data manually
- This framework simply notifies the ACQ instrument of the pipeline configuration to run during data acquisition

To use a FPGA processor, define a `ProcessorFPGA` object, add the appropriate FPGA processing stages and then attach it to an [ACQ HAL](ACQ.md). On doing so, any data acquired from said ACQ HAL will now output real-time processed data (which is subsequently [stored in the experiment](Exp_Overview.md)) as opposed to the raw data. Note that the resulting [Experiment Configuration object](Exp_Config_Basic.md) will store all the Processor configurations attached to any of its designated ACQ HAL objects and implement them during an experiment.

The following code demonstrates a possible implementation of a FPGA data processor (assuming that `lab` has is a valid `Laboratory` object):


```python
import sqdtoolz as stz

...

#(A) - Create a FPGA processor object.
stz.ProcessorFPGA('ddcIntegFPGA', lab)
#(B) - OPTIONALLY reset pipeline
lab.PROC('ddcIntegFPGA').reset_pipeline()
#(C) - Add the processing stages
lab.PROC('ddcIntegFPGA').add_stage(stz.FPGA_DDC([25e6, 25e6]))
lab.PROC('ddcIntegFPGA').add_stage(stz.FPGA_FIR([{'Type' : 'low', 'Taps' : 128, 'fc' : 1e6, 'Win' : 'hamming'}]*4))
lab.PROC('ddcIntegFPGA').add_stage(stz.FPGA_Mean('sample'))
lab.PROC('ddcIntegFPGA').add_stage(stz.FPGA_Mean('segment'))
lab.PROC('ddcIntegFPGA').add_stage(stz.FPGA_Mean('repetition'))

#(D) - Attach the processor to an ACQ HAL
lab.HAL("TabACQ").set_data_processor(lab.PROC('ddcIntegFPGA'))
```

The `ProcessorFPGA` above can be fetched via its name: `lab.PROC('ddcIntegFPGA')`. Now note the following features:
- (A) - The FPGA object is created by giving it a unique name and a `Laboratory` object. Note that if it is recreated under the same name, its processing pipeline is NOT reset.
- (B) - A pipeline reset deletes all processing nodes in the main and end-stage pipelines.
- (C) - The real-time processing is done in the order prescribed on calling `add_stage` command. The details on setting up the individual FPGA processing nodes is given [here](Proc_FPGA_list.md).
- (D) - On [defining an ACQ HAL](ACQ.md) called `"TabACQ"`, one may attach the new FPGA data processor via `set_data_processor`. To remove it later, pass `None` to the `set_data_processor` function.

Note that unlike the CPU/GPU processors, there is no `add_stage_end` command as FPGA pipelines are not split into blocks etc.
