from sqdtoolz.ExperimentConfiguration import ExperimentConfiguration

class ExpConfigIQpulseInSingleOut(ExperimentConfiguration):

    # Its sole purpose is to set different HAL parameters & bindings & Waveforms.
    def __init__(self, duration, pulser, pulser_to_awg_ch_name, awg_2_channel_IQ, acq_module, acq_sample_rate):
        super().__init__(duration, [pulser], [awg_2_channel_IQ], acq_module)
        # ADD all the HAL objects HERE
        self._pulser = pulser
        self._pulser_output_name = pulser_to_awg_ch_name
        self._awg_IQ = awg_2_channel_IQ
        self._awg_marker_channel = 0
        self._awg_marker_index = 0
        self._acq_module = acq_module
        self._acq_module.InputTriggerEdge = 1
        self._acq_sample_rate = acq_sample_rate
        self._acq_ch_ind = 0
        
    def set_awg_marker_to_acq_output(self, awg_marker_channel = 0, awg_marker_index = 0):
        # TRIGGER ACQ with the AWG here, if you want to.
        self._awg_marker_channel = awg_marker_channel
        self._awg_marker_index = awg_marker_index

    def set_acq_channel_index(self, ch_index = 0):
        # Set Channel from which you want to measure.
        self._acq_ch_ind = ch_index

    def init_instrument_relations(self):
        # define trigger binding here.
        self._pulser.set_trigger_output_params(self._pulser_output_name, 50e-9)
        self._acq_module.SampleRate = self._acq_sample_rate
        self._acq_module.set_trigger_source(self._awg_IQ.get_output_channel(self._awg_marker_channel).marker(self._awg_marker_index))
        self._awg_IQ.set_trigger_source_all(self._pulser.get_trigger_output(self._pulser_output_name))

    def update_waveforms(self, awg_segment_list, num_samples, num_segments, **kwargs):
        # accept AWG stuff and marker and trigger for DDG,
        # and programming ACQ and AWG (HALS objs)
        readout_segs = kwargs.get('readout_segments', None)
        readout_times = kwargs.get('readout_time_lens', None)
        assert readout_segs != None or readout_times != None, "Must specify a valid readout_segments or readout_time_lens."

        self._acq_module.NumSamples = num_samples
        self._acq_module.NumSegments = num_segments

        if readout_segs != None:
            self._awg_IQ.set_waveform_segments(awg_segment_list)
            self._awg_IQ.get_output_channel(self._awg_marker_channel).marker(self._awg_marker_index).set_markers_to_segments(readout_segs)            
        elif readout_times != None:
            #TODO: Generate the arbitrary numpy array etc...
            pass

    def get_data(self):
        #TODO: Pack the data appropriately if using multiple ACQ objects (coordinating their starts/finishes perhaps?)
        cur_acq = self._instr_ACQ
        cur_data = cur_acq.get_data()
        return cur_data[self._acq_ch_ind]  #Isolate the channel given that it is just a single-channel acquisition
