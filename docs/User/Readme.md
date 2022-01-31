# User Documentation

Quick-start guide

Main structure:
- [Laboratory Class](Laboratory.md)
- Defining HALs and instrument settings for a given experiment:
    - [AWG Pulse Building](AWG_Pulse_Building.md)
        - [Waveform Segments](AWG_WFS.md)
        - [Waveform Transformations](AWG_WFMTs.md)
    - Data acquisition:
        - [Basic ACQ HAL](ACQ.md)
        - VNA
    - Setting up real-time processing
        - CPU Processors
        - GPU Processors
- Combine HAL settings to form `ExperimentConfiguration` objects:
    - [Creating ExperimentConfiguration objects](Exp_Config_Basic.md)
    - [Defining Variables](Var_Defns.md)
    - [Using ExperimentSpecifications objects](Exp_Config_SPEC.md)
    - [Using Waveform Mappers](Exp_Config_WFMMAP.md)
- Take experiment configurations and run an `Experiment` object:
    - [Overview of general workflow](Exp_Overview.md)
    - [Sweeping parameters in experiments](Exp_Sweep.md)
    - [Cascading and grouping multiple experiments](Exp_CascadeGroup.md)
    - [Automated experiments](Exp_Automated.md)
- Retrieve and analyse the data returned from an experiment:
    - [Data retrieval](Data_IO.md)
    - Data processing


Other advanced use-cases:
- [Non-uniform data sampling](ACQ_NonUniformDataSampling.md)
