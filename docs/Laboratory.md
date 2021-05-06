# Laboratory

The role of the laboratory class is to manage the entire experiment and to handle the tabulation plus the loading/saving of summoned HAL, variable and experiment objects. The Laboratory object is instantiated as follows:

``` python
lab = Laboratory(instr_config_file='instr_config.yaml', save_dir='save_dir')
```

The arguments `instr_config_file` and `save_dir` are optional and specify the instrument YAML and absolute (or relative) save directory in which to post the experiment results. Although the YAML automatically loads the instrument configurations, the individual QCoDeS instruments must be loaded manually via the `load_instrument` command.

## Design pattern

All objects that are relevant to the experiment (easily defined as those that must exist if one were to reload the current state of the experiment from scratch) must register themselves to the Laboratory object. Said objects are initialised via initialisers that have a standard `name` and `lab` as their first two arguments. That is, the object will use the name to register itself under that name in the Laboratory object via one of its internal `_register_XXXX` commands. To access said objects after initialisation, one uses one of the accessor functions within the Laboratory object:

``` python
#Accessing a HAL instrument object
lab.HAL('MW-Src')
#Accessing a variable object
lab.VAR('CavFreq')
#Accessing a data-processor object
lab.PROC('gpu_ddc_fir')
#Accessing a waveform-transformation object
lab.WFMT('gpu_ddc_fir')
#Accessing an experiment-configuration object
lab.CONFIG('cont_meas')
```


