# AWG pipeline

The `WaveformAWG` HAL handles waveforms across multiple AWG channels. This document highlights the program flow run internally when running experiments. 

## Basic control flow

When running an experiment:
- `init_instruments` is called. The `_set_current_config` command will reset the 'programmed' waveforms
- `prepare_instruments` is called on every sweeping iteration:
    - `activate` is called to turn ON all the AWG outputs
    - `prepare_initial` is called. This assembles the waveform and sets up the segmentation for AutoCompression etc. The `dont_reprogram` flag will be `False` initially as the 'programmed' flag is cleared during `init_instruments`. It will skip some processing if it shouldn't reprogram. The function `prepare_waveform_memory` on the AWG driver is called if it needs to be reprogrammed. Note that this will pass on the waveforms to the AWG driver.
    - `prepare_final` is called to reprogram the waveforms if required - done so by calling `program_channel` in the AWG driver. Once again, the same waveform information is passed onto the AWG driver.
- `deactivate` is called in the end to turn OFF all AWG outputs

The idea is that some AWGs require all channels to be programmed at once - this is why, `prepare_initial` is used to give it a chance to collate the waveforms and allocate memory as required. On a slight technicality, one could program all channels at once and ignore the rest of the `program_channel` calls given that the state of those channels is known from the previous `prepare_waveform_memory` calls from before.

## AWG object resolution

See this [article](Lab_ObjectTreeResolution.md).

## WaveformGeneric and WaveformMapper

Now consider:

- In the higher level, one wishes to just visualise the shape of the waveforms as it enters the final wire (e.g. charge line of a qubit)
- In the lower levels, the `WaveformAWG` HALs map to analogue waveforms which are synthesised sometimes with multiple channels (e.g. IQ modulation)
- In the higher level, one wishes to just digitally trigger a readout event or perhaps a microwave pulse event
- In the lower level, this usually maps to some AWG marker or some digital output pulse trigger

The `WaveformGeneric` and `WaveformMapper` classes help map the higher-level visualisations into the lower-level HAL arrangements held in an `ExperimentConfiguration` object. The `WaveformMapper` object just holds dictionaries mapping the higher-level waveform or digital construct to lower-level HAL or marker objects. The `WaveformGeneric` object just holds the waveform segments of different higher-level waveforms (to be mapped onto different AWG HAL objects) and the digital waveforms (to be mapped onto marker objects). After mapping the waveform via `map_waveforms`, the function `update_waveforms` (both found in the `ExperimentConfiguration` object) can be used to imprint the higher-level generic waveform onto the HALs. As the segment names can be new, the variables required to sweep this waveform (in the context of an automated `Experiment` class) can be returned from this function. That is, the `WaveformGeneric` object has minimal object resolution so that one may write:

```python
wfm = WaveformGeneric(['qubit'], ['readout'])
wfm.set_waveform('qubit', [
    WFS_Constant("SEQPAD", None, -1, 0.0),
    WFS_Constant("init", None, self.load_time, 0.0),
    WFS_Gaussian("tip", self._wfmt_qubit_drive.apply(phase=0), self.tip_time, self.tip_ampl),
    WFS_Constant("wait", None, 1e-9, 0.0),
    WFS_Gaussian("echo", self._wfmt_qubit_drive.apply(), self.echo_time, self.echo_ampl),
    WFS_Constant("wait2", None, 1e-9, 0.0),
    WFS_Gaussian("untip", self._wfmt_qubit_drive.apply(), self.tip_time, self.tip_ampl),
    WFS_Constant("pad", None, 5e-9, 0.0),
    WFS_Constant("read", None, self.readout_time, 0.0)
])
wfm.set_digital_segments('readout', 'qubit', ['read'])
sweep_vars = self._expt_config.update_waveforms(wfm, [('WaitTime', wfm.get_waveform_segment('qubit', 'wait'), 'Duration'),
                                                      ('WaitTime2', wfm.get_waveform_segment('qubit', 'wait2'), 'Duration'),
                                                      ('echoPhase', wfm.get_waveform_segment('qubit', 'echo').get_WFMT(), 'phase')] )
```

The above script returns two `VariablePropertyTransient` (this object is not registered to the `Laboratory` object and is thus, *transient*) named `'WaitTime'`, `'WaitTime2'` and `'echoPhase'` into `sweep_vars`. These can be used to set and sweep the parameters. Note that the `'echoPhase'` points to the WFMT object's `phase` parameter. That is, the syntax to query these variables is similar to the way one sets up normal [AWG variables](../User/AWG_VARs.md). Note that these variables disappear once the experiment object finishes running.
