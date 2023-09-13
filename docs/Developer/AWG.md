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
