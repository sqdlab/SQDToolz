# User Documentation

Quick-start guide
- [Example usage](example_usage.ipynb)

Main structure:
- [Laboratory Class](Laboratory.md)
- Defining HALs and instrument settings for a given experiment:
    - [AWG Pulse Building](AWG_Pulse_Building.md)
        - [Waveform Segments](AWG_WFS.md)
        - [Waveform Transformations](AWG_WFMTs.md)
        - [Sweeping AWG waveform parameters using VARs](AWG_VARs.md)
    - Data acquisition:
        - [Basic ACQ HAL](ACQ.md)
        - VNA
    - [Real-time Data Processing](Proc_Overview.md)
        - [CPU Processor - Overview](Proc_CPU_Overview.md)
        - [Available CPU processors](Proc_CPU_list.md)
        - [GPU Processor - Overview](Proc_GPU_Overview.md)
        - [Available GPU processors](Proc_GPU_list.md)
        - [FPGA Processor - Overview](Proc_FPGA_Overview.md)
        - [Available FPGA processors](Proc_FPGA_list.md)
    - General purpose HALs:
        - [Microwave sources](GENmwSource.md)
        - [Switches](GENswitch.md)
- Combine HAL settings to form `ExperimentConfiguration` objects:
    - [Creating ExperimentConfiguration objects](Exp_Config_Basic.md)
    - [Defining Variables](Var_Defns.md)
    - [Using ExperimentSpecifications objects](Exp_Config_SPEC.md)
    - [Using Waveform Mappers](Exp_Config_WFMMAP.md)
- Take experiment configurations and run an `Experiment` object:
    - [Overview of general workflow](Exp_Overview.md)
    - [Sweeping parameters in experiments](Exp_Sweep.md) - including many-one variable sweeps.
    - [Sample ordering in experiment sweeps](Exp_SweepPerm.md)
    - [Recording extra parameters](Exp_RecParams.md) - i.e. `rec_params`
    - [Cascading and grouping multiple experiments](Exp_CascadeGroup.md)
    - [Automated experiments](Exp_Automated.md)
- Retrieve and analyse the data returned from an experiment:
    - [Data retrieval](Data_IO.md)
    - [Data fitting (Basic)](Data_Fitting.md)
    - [Data fitting (RF resonators)](Data_Fitting_RF.md)


Other advanced use-cases:
- [Synthesising SQDToolz HDF5 data files](Data_Write.md)
- [Non-uniform data sampling](ACQ_NonUniformDataSampling.md)

Other auxiliary articles:
- **[Driver-level documentation](InstrumentSpecific/Readme.md)** on setting up the hardware (e.g. template YAML and wiring diagrams)
- [Notes on custom devices](CustomDevices/Readme.md)
- [Measurement methods](MeasurementMethods/Readme.md)
