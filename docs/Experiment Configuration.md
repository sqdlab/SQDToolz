# Experiment configuration

The experiment configuration handles a collection of HAL objects to be fed into an experiment. For example, an experimental run may consist of timing pulses from a DDG controlling an AWG to generate timed pulse sequences with the resulting signals captured by some acquisition instrument.

## Trigger chains

Different instruments can trigger other instruments to synchronise the measurement tool-chain. This section discusses how one should implement output and input triggers such that they automatically appear in the timing diagrams.

### Trigger outputs

HAL objects with an output that can trigger other objects via a digital trigger signal must implement a couple of classes:

- The HAL object itself must implement `TriggerOutputCompatible` in order both appear in timing diagrams and to pass internal verification checks run on HAL objects by the `ExperimentConfiguration` class when using said HAL object as a trigger source.
- The individual trigger outputs are usually implemented as a list of classes housed within the HAL object (although it can be the HAL object itself); said objects must implement `TriggerOutput` to ensure that they have the right functions to interface with the `ExperimentConfiguration` class.

For example, the AWG waveforms are represented via the `WaveformAWG` class which implements `TriggerOutputCompatible`, while the actual output markers live within the `AWGOutputMarker` class which implements `TriggerOutput`. The `TriggerOutput` class requires one to implement:

- `_get_parent_HAL` - returns reference to the parent HAL object holding the `TriggerOutput` (can be itself if the HAL object class is itself the digital trigger output).
- `get_trigger_times` - returns the times and gated-segments in which a target device will be triggered relative to the time in which the current HAL device is triggered. The return value is given as a tuple consisting of two arrays:
    - Trigger-edge times as referenced to the positive/negative edge which triggers the target device
    - Gated times as referenced to the positive/negative edge which triggers the target device given as a 2-column numpy array in which each row defines a time-segment (across the columns) that gate-triggers the target device.
- `get_trigger_id` - returns a string or integer or a list of strings/integers (can be a mix) that can be used to obtain the trigger output from the HAL object via `_get_trigger_output_by_id` (discussed below). It is up to the developer to choose what value(s) are required to uniquely identify the trigger output in the given hierarchical structure. For example, with the `WaveformAWG` HAL, the `TriggerOutput` class is implemented via `AWGOutputMarker` which is housed within `AWGOutputChannel`. Thus, one requires a list of two integers indicating the channel index and the marker index. Note that in the case where the HAL object is itself the `TriggerOutput` object, the identifier could also be a blank string or 0.
- `_get_timing_diagram_info` - returns a dictionary defining how this input instrument is to be displayed on the timing-diagram (as discussed below).

The `TriggerOutputCompatible` class requires the implementation of:

- `_get_trigger_output_by_id` - returns the `TriggerOutput` object corresponding to the supplied ID (either a list of integers/strings or a single identifier).
- `_get_all_trigger_outputs` - returns all the IDs of all available trigger outputs in the given HAL. Using any of these IDs with the function `_get_trigger_output_by_id` should yield a valid `TriggerOuput` object.

### Trigger inputs

HAL objects that can accept an input trigger to synchronise their output waveforms (like acquisition or AWG modules) must implement a similar couple of classes:

- The HAL object itself must implement `TriggerInputCompatible` in order both appear in timing diagrams and to pass internal verification checks run on HAL objects by the `ExperimentConfiguration` class when using said HAL object to accept a trigger input signal.
- The individual trigger inputs are either implemented within the object itself or via a list of classes housed within the HAL object (like with AWG markers); said objects must implement `TriggerInput` to ensure that they have the right functions to interface with the `ExperimentConfiguration` class.

The primary function of `TriggerInputCompatible` is to implement:

- `_get_all_trigger_inputs` - returns all possible trigger inputs associated with the HAL in terms of `TriggerInput` objects.

The `TriggerInput` class must implement:

- `_get_instr_trig_src` - returns the `TriggerOutput` object that triggers the current trigger input.
- `_get_instr_input_trig_edge` - returns the edge polarity of the trigger input (positive edge being 1 and negative edge being 0).
- `_get_timing_diagram_info` - returns a dictionary defining how this input instrument is to be displayed on the timing-diagram (as discussed below).


## Timing diagrams

The timing diagram displays the relative placement of outputs and inputs. To display a HAL object on the timing diagram, the individual trigger inputs/outputs must implement `TriggerInput` and/or `TriggerOuput` to unlock the implementation of `_get_timing_diagram_info`. This function is to return a dictionary containing the following keys:

- `Type` - the bar display to use on the plot. The allowed values include:
    - `None` - The trigger input/output is not displayed on the timing diagram.
    - `BlockShaded` - A shaded box used to signify a general block (like signal acquisition)
    - `DigitalSampled` - A plot of the actual digital trigger waveform
    - `AnalogueSampled` - A stream of boxes with a pictorial representations of the analogue waveforms embedded within each time-segment 
    - `DigitalEdges` - A plot of the actual digital trigger waveform
- `Period` - the time period to which the signal is to occupy the timing diagram upon receiving and aligning to a trigger signal (for example, for an ACQ object, this is the period of acquisition).
- `Data` - optional argument holding the data required when the display is a digital pulse or an analogue waveform block:
    - `DigitalSampled` - data given as a uniformly sampled array (for example, the raw marker array) with the sample-rate supplied alongside as a tuple: (data_array, sample_rate).
    - `AnalogueSampled` - data given as a list of analogue waveform segments in which each element is a dictionary contains the keys `Duration` and `yPoints` holding the actual duration of the segment and a numpy array of points respectively. Note that the array is just a pictorial representation so try to coarsely sample it to a few points like 20.
    - `DigitalEdges` - data given as a list of tuples (time, value) in which value is 0 or 1. The idea is to simply supply the points in which the digital waveform changes value and then to quote the subsequent value to be sure (waveform changes value right on the time-point). Note that the first tuple must include the zeroth time: (0, 0|1).
- `TriggerType` - can be either `Edge` or `Gated`. If `Gated`, the key `Type` must be `BlockShaded` only (for now). In this case, the `Period` is ignored and inferred from the trigger signal.
