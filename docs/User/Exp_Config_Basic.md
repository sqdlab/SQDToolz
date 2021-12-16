# Creating Experiment Configurations

A given HAL instrument can have different settings depending on the experiment at hand. The `ExperimentConfiguration` satisfies the following roles:

- Holds the list of instruments relevant to a given experiment
- Stores a snapshot of all (HAL-level) instrument settings of all associated instruments used in an experiment
- When running an experiment, the settings in a given `ExperimentConfiguration` are automatically set on all associated instruments before acquiring any data

The idea is that different experiments may utilise different `ExperimentConfiguration` objects. This page covers:

- [Basic usage](#basic-usage)
- [Inheriting ExperimentConfiguration settings](#inheriting-experimentconfiguration-settings)

## Basic usage

Consider a simple use-case when defining an `ExperimentConfiguration` object (assuming that `lab` is a valid `Laboratory` object):

```python
#Load instruments
lab.load_instrument('virACQ')
lab.load_instrument('virDDG')
lab.load_instrument('virAWG')
lab.load_instrument('virMWS')

...

#Initialise HALs
ACQ("acq", lab, 'virACQ')
DDG("ddg", lab, 'virDDG', )
GENmwSource("MW-Src", lab, 'virMWS', 'CH1')

...

#(A) - Set the particular settings for the given experiment
#
lab.HAL("ddg").set_trigger_output_params('A', 50e-9)
lab.HAL("ddg").get_trigger_output('B').TrigPulseLength = 100e-9
lab.HAL("ddg").get_trigger_output('B').TrigPulseDelay = 50e-9
lab.HAL("ddg").get_trigger_output('B').TrigPolarity = 1
#
WaveformAWG("Wfm1", lab, [('virAWG', 'CH1'), ('virAWG', 'CH2')], 1e9)
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("init", None, 20e-9, 0.5-0.1*m))
lab.HAL("Wfm1").add_waveform_segment(WFS_Constant("zero1", None, 30e-9, 0.1*m))
lab.HAL("Wfm1").add_waveform_segment(WFS_Gaussian("init2", None, 45e-9, 0.5-0.1*m))
lab.HAL("Wfm1").add_waveform_segment(WFS_Constant("zero2", None, 77e-9*(m+1), 0.0))
read_segs = ["init"]
trig_segs = ["zero2"]
awg_wfm.get_output_channel(0).marker(1).set_markers_to_segments(read_segs)
awg_wfm.get_output_channel(1).marker(0).set_markers_to_segments(trig_segs)
#
lab.HAL("MW-Src").Mode = 'PulseModulated'
lab.HAL("MW-Src").Frequency = 500e6
lab.HAL("MW-Src").Power = -25
#
lab.HAL("acq").set_acq_params(10,2,30)

#(B) - Setup trigger relationships
lab.HAL("acq").set_trigger_source(lab.HAL("Wfm1").get_output_channel(0).marker(0))
lab.HAL("Wfm1").set_trigger_source_all(lab.HAL("ddg").get_trigger_output('A'))
lab.HAL("MW-Src").set_trigger_source(awg_wfm.get_output_channel(1).marker(0))

#(C) - Create ExperimentConfiguration object
ExperimentConfiguration("testConf", lab, 1.0, ["ddg", "Wfm1", "MW-Src"], "acq")

#(D) - Plot timing diagram for this setup/configuration
lab.CONFIG("testConf").plot()
```

The `ExperimentConfiguration` above can be fetched via its name: `lab.CONFIG("testConf")`. Now note the following features:
- (A) - All settings relevant to the experiment should be explicitly set. **All associated HAL settings at the time of creating the `ExperimentConfiguration` object are saved**. Thus, if there are any residual settings that are not overwritten, they get saved and initialised on running the experiment with this experiment configuration.
- (B) - The source can be specified for all instruments that requires a trigger (to run its output) via `set_trigger_source`. The trigger relationships do not have any bearing in the experiment except in the generation of the timing diagram. These settings should reflect the physical hard-wired trigger connections and/or any software settings set in the YAML. Note that `WaveformAWG` HALs have a special `set_trigger_source_all` function to set the outputs/markers to a single trigger source.
- (C) - The `ExperimentConfiguration` object requires:
    - A valid `Laboratory` object to register itself for future access
    - Total length of the repetition window. Ensure that it is long enough to house all relevant signal outputs in this configuration.
    - A list of all relevant HAL objects to which the settings must be saved and initialised later on running the experiment. If a HAL is not in this list, its settings will not be saved and thus, will not be guaranteed to be in the desired state on running the experiment. The list can be empty.
    - The final argument is the acquisition HAL. Note that it can be set to `None`.
- (D) - The timing diagram is generated from the HALs that produce timed signals (e.g. a microwave source in continuous mode will not appear in the timing diagram) and their associated triggering relationships.

Note that in general, the act of setting the HAL parameters is not expensive. In fact, in the case of AWG waveforms, no waveform is programmed into the associated AWGs when simply defining the `WaveformAWG` object (instead, that occurs when running the actual experiment).


## Inheriting ExperimentConfiguration settings

Sometimes a bunch of HAL settings may be defined and passed onto an `ExperimentConfiguration` object. When creating a second configuration, one may wish to tweak just one HAL setting without having to copy and paste the giant block of code used to define the settings for the first configuration. There are several usage patterns depending on the use cases.

**Case 1:** New configuration uses the same list of HALs and has the same repetition window length.
```python
#Copy the ExperimentConfiguration
ExperimentConfiguration.copyConfig("testConf2", lab, lab.CONFIG("testConf"))

#Edit the new configuration (this just sets all instruments to the settings prescribed by testConf2)
lab.CONFIG("testConf2").edit()

#Make any relevant changes to the HAL settings
lab.HAL("MW-Src").Frequency = 100e6
...

#Commit all changes
lab.CONFIG("testConf2").commit()
```

**Case 2:** New configuration uses a different set of HALs, but is to inherit all settings for common HALs in previous configuration.
```python
#Initialise the settings of testConf onto all its instruments
lab.CONFIG("testConf").init_instruments()

#Make any relevant changes to the HAL settings
lab.HAL("acq").set_acq_params(10,25,60)
...

#Create new ExperimentConfiguration
ExperimentConfiguration("testConf2", lab, 1.0, ["ddg", "Wfm1"], "acq")
```

Note that functionally, there is no difference between `edit()` and `init_instruments()` with the former provided as syntactic sugar.
