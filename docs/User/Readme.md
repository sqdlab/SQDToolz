# User Documentation

Quick-start guide

Main structure:
- [Laboratory Class](Laboratory.md)
- Defining HALs and instrument settings for a given experiment:
    - [AWG Pulse Building](AWG_Pulse_Building.md)
        - [Waveform Segments](AWG_WFS.md)
        - [Waveform Transformations](AWG_WFMTs.md)
- Combine HAL settings to form `ExperimentConfiguration` objects:
    - [Creating ExperimentConfiguration objects](Exp_Config_Basic.md)
    - [Using ExperimentSpecifications objects](Exp_Config_SPEC.md)
    - [Using Waveform Mappers](Exp_Config_WFMMAP.md)
- Take experiment configurations and run an `Experiment` object:
    - [Overview of general workflow](Exp_Overview.md)
    - [Sweeping parameters in experiments](Exp_Sweep.md)
    - [Cascading and grouping multiple experiments](Exp_CascadeGroup.md)
    - [Automated experiments](Exp_Automated.md)
