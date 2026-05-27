from sqdtoolz.Experiment import*

class ExpVNAoptimalSNR(Experiment):
    def __init__(self, name, expt_config, wfmt_qubit_drive, range_amps, SPEC_qubit, transition='GE', phase=0, iq_indices = [0,1], **kwargs):
        super().__init__(name, expt_config)

    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."

        if self.normalise_data:
            self.norm_expt = ExpCalibGE('GE Calibration', self._expt_config, self._wfmt_qubit_drive, self.normalise_reps, self._SPEC_qubit, self._iq_indices,
                                        load_time = self.load_time, readout_time = self.readout_time, drive_time = self.drive_time)
            self.norm_expt._run(file_path, data_file_index=0, **kwargs)

        self._expt_config.init_instruments()

        wfm = WaveformGeneric(['qubit'], ['readout'])
        wfm.set_waveform('qubit', [
            WFS_Constant("SEQPAD", None, -1, 0.0),
            WFS_Constant("init", None, self.load_time, 0.0),
            WFS_Gaussian("drive", self._wfmt_qubit_drive.apply(phase=self._phase), self.drive_time, 0.001),
            WFS_Constant("pad", None, 5e-9, 0.0),
            WFS_Constant("read", None, self.readout_time, 0.0)
        ])
        wfm.set_digital_segments('readout', 'qubit', ['read'])
        self._temp_vars = self._expt_config.update_waveforms(wfm, [('Drive Amplitude', wfm.get_waveform_segment('qubit', 'drive'), 'Amplitude')] )

        sweep_vars = [(self._temp_vars[0], self._range_amps)]

        kwargs['skip_init_instruments'] = True

        self._cur_param_name = self._temp_vars[0].Name
        self._file_path = file_path
        return super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        pass
