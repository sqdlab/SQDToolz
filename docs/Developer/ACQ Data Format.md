
# ACQ data format

The ACQ data format is made to be flexible to data gathering across multiple channels, segments, samples and repetitions. Over a given experiment window (that is, the timing diagram in which the trigger pulses and waveforms are sent), there may be multiple acquisition events (synchronised to trigger pulses) in which the ACQ instrument records a certain number of samples. These acquisition events are referred to as 'segments' while the individual data points taken within each acquisition event are referred to as 'samples'. Now the experiment window can be triggered multiple times to create many 'repetitions' which may be averaged to yield the average signal across each segment. Although this can be done by the user calling repeatedly calling the `get_data` function, there are cases where requesting a large cache of data is more efficient to overcome communication overheads.

The format breakdown is mapped onto the required properties for ACQ-compatible driver instruments:

- `NumSamples` - The number of sample points to take in a given acquisition segment
- `NumSegments` - Number of segments within an experiment window
- `NumRepetitions` - Number of experiment windows to capture

Note that each reptitition is typically synchronised via a sequence trigger along with the individual acquisition triggers over each individual segment. The resulting array is referenced as `data[channel][repetition][segment][sample]`. Now the demarcation of the channels might suggest that one returns one ACQ-compatible instrument object per channel of the acquisition instrument. However, most acquisition cards tend to operate on the principle of a single acquisition trigger and then acquiring synchronously across multiple input channels. Thus, the channel selection/binding is provided via the following mandatory driver-level properties:

- `ChannelsAvailable` - Read-only property that returns the number of available channels.
- `ChannelsAcquired`  - A boolean list (size equal to the number of available channels) indexing the channels currently being acquired. For example, if channels 2 and 3 on a 4-channel ACQ instrument are to be read, then the list is: `[False, True, True, False]`.

The idea is that the channels are to read concurrently. If multiple channels are to acquire in a disjointed manner, then one may subdivide the instrument driver into channels which are themselves ACQ-compatible driver objects; a pattern similar to that adopted with the AWG or microwave source drivers. Nonetheless, one may choose to pair up individual portions to perform the device-optimised concurrent readout.

# Note on multipurpose instruments

Some instruments can act as both AWG and ACQ instruments (e.g. the Tabor P2584M). In such cases, there may be a conflict of properties. In such cases, the driver should internally instantiate two separate `InstrumentChannel` submodules in QCoDeS for each sub-instrument type (e.g. for AWG and ACQ). In the case of instantiating a HAL object, one can access the appropriate submodule for the required AWG or ACQ HAL-level object.
