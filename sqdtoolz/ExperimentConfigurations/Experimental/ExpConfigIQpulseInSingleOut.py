from sqdtoolz.ExperimentConfiguration import ExperimentConfiguration

class ExpConfigIQpulseInSingleOut(ExperimentConfiguration):

    # Its sole purpose is to set different HAL parameters & bindings & Waveforms.
    def __init__(self, duration, list_DDGs, list_AWGs, instr_ACQ, list_GENs, awg_2_channel_IQ, awg_ro_mkr_ch = 0, awg_ro_mkr_ind = 0, awg_acq_seq_mkr_ch = 0, awg_acq_seq_mkr_ind = 1):
        super().__init__(duration, list_DDGs, list_AWGs, instr_ACQ, list_GENs)
        self._awg_IQ = awg_2_channel_IQ
        
        self._awg_ro_mkr_ch = awg_ro_mkr_ch
        self._awg_ro_mkr_ind = awg_ro_mkr_ind
        self._awg_acq_seq_mkr_ch = awg_acq_seq_mkr_ch
        self._awg_acq_seq_mkr_ind = awg_acq_seq_mkr_ind

        self._acq_module = instr_ACQ
        self._acq_module.InputTriggerEdge = 1
        self._acq_ch_ind = 0
        
    def set_acq_channel_index(self, ch_index = 0):
        #Set desired Channel from which to measure.
        self._acq_ch_ind = ch_index

    def update_waveforms(self, awg_segment_list, num_acq_samples, num_acq_segments, **kwargs):
        # accept AWG stuff and marker and trigger for DDG,
        # and programming ACQ and AWG (HALS objs)
        readout_segs = kwargs.get('readout_segments', None)
        readout_times = kwargs.get('readout_time_lens', None)
        assert readout_segs != None or readout_times != None, "Must specify a valid readout_segments or readout_time_lens."

        self._acq_module.NumSamples = num_acq_samples
        self._acq_module.NumSegments = num_acq_segments

        if readout_segs != None:
            self._awg_IQ.set_waveform_segments(awg_segment_list)
            self._awg_IQ.get_output_channel(self._awg_ro_mkr_ch).marker(self._awg_ro_mkr_ind).set_markers_to_segments(readout_segs)
            #ACQ Sequence marker
            acq_seq_mkr = self._awg_IQ.get_output_channel(self._awg_acq_seq_mkr_ch).marker(self._awg_acq_seq_mkr_ind)
            acq_seq_mkr.set_markers_to_trigger()
            acq_seq_mkr.TrigPulseDelay = 0
            acq_seq_mkr.TrigPulseLength = self._awg_IQ.Duration * 0.5
        elif readout_times != None:
            #TODO: Generate the arbitrary numpy array etc...
            pass

    def get_data(self):
        #TODO: Pack the data appropriately if using multiple ACQ objects (coordinating their starts/finishes perhaps?)
        cur_acq = self._instr_ACQ
        cur_data = cur_acq.get_data()
        return cur_data[self._acq_ch_ind]  #Isolate the channel given that it is just a single-channel acquisition
