from sqdtoolz.Experiment import*
from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Experiments.Experimental.ExpCalibGE import*

class ExpCalibXrot(Experiment):
    def __init__(self, name, expt_config, wfmt_qubit_drive, SPEC_qubit, rotDenom, numPeriods=4, iq_indices = [0,1], **kwargs):
        #This assumes that Pi-X and frequency (i.e. Ramsey) have been reasonably calibrated...
        #Rotation angle is np.pi / rotDenom

        super().__init__(name, expt_config)

        self._iq_indices = iq_indices
        self._wfmt_qubit_drive = wfmt_qubit_drive

        self._rotDenom = rotDenom
        self._numTotalRepeats = numPeriods * self._rotDenom * 2
        
        # self._range_amps = kwargs.get('range_amps', None)
        self._post_processor = kwargs.get('post_processor', None)

        self._SPEC_qubit = SPEC_qubit

        #Calculate default load-time via T1 of qubit or default to 40e-6
        def_load_time = self._SPEC_qubit['GE T1'].Value * 4
        if def_load_time == 0:
            def_load_time = 40e-6
        #Override the load-time if one is specified explicitly
        self.load_time = kwargs.get('load_time', def_load_time)

        if self._rotDenom == 1:
            self._gate_Xamp = kwargs.get('drive_amplitude', self._SPEC_qubit['GE X-Gate Amplitude'].Value)
            self.drive_time = kwargs.get('drive_time', self._SPEC_qubit['GE X-Gate Time'].Value)
        elif self._rotDenom == 2:
            self._gate_Xamp = kwargs.get('drive_amplitude', self._SPEC_qubit['GE X/2-Gate Amplitude'].Value)
            self.drive_time = kwargs.get('drive_time', self._SPEC_qubit['GE X/2-Gate Time'].Value)
        else:
            self._gate_Xamp = kwargs.get('drive_amplitude', self._SPEC_qubit['GE X-Gate Amplitude'].Value / self._rotDenom)
            self.drive_time = kwargs.get('drive_time', self._SPEC_qubit['GE X-Gate Time'].Value)

        self.readout_time = kwargs.get('readout_time', 2e-6)
        self.normalise_reps = kwargs.get('normalise_reps', 5)

    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."

        self.norm_expt = ExpCalibGE('GE Calibration', self._expt_config, self._wfmt_qubit_drive, self.normalise_reps, self._SPEC_qubit, self._iq_indices,
                                    load_time = self.load_time, readout_time = self.readout_time, drive_time = self._SPEC_qubit['GE X-Gate Time'].Value)
        self.norm_expt._run(file_path, data_file_index=0, **kwargs)

        self._expt_config.init_instruments()


        wfm = WaveformGeneric(['qubit'], ['readout'])
        wfm.set_waveform('qubit', [
            WFS_Constant("SEQPAD", None, -1, 0.0),
            WFS_Constant("init", None, self.load_time, 0.0),
            WFS_Group('drivePulses', [WFS_Gaussian("drive", self._wfmt_qubit_drive.apply(), self.drive_time, self._gate_Xamp)], -1, 1),
            WFS_Constant("pad", None, 5e-9, 0.0),
            WFS_Constant("read", None, self.readout_time, 0.0)
        ])
        wfm.set_digital_segments('readout', 'qubit', ['read'])
        self._temp_vars = self._expt_config.update_waveforms(wfm, [('Num Pulses', 'qubit', 'drivePulses', 'NumRepeats')] )
        
        sweep_vars = [(self._temp_vars[0], np.arange(0,self._numTotalRepeats+1))]

        kwargs['skip_init_instruments'] = True

        self._cur_param_name = self._temp_vars[0].Name
        self._file_path = file_path

        # Run experiment in a loop and update vars? 

        return super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        if self._post_processor:
            self._post_processor.push_data(data)
            data = self._post_processor.get_all_data()
        
        assert self._cur_param_name in data.param_names, "Something went wrong and the sweeping parameter disappeared in the data processing?"

        arr = data.get_numpy_array()

        data_raw_IQ = np.vstack([ arr[:,self._iq_indices[0]], arr[:,self._iq_indices[1]] ]).T
        fig, axs = plt.subplots(ncols=2, gridspec_kw={'width_ratios':[2,1]})
        fig.set_figheight(5); fig.set_figwidth(15)
        data_y = self.norm_expt.normalise_data(data_raw_IQ, ax=axs[1])

        # dpkt = dfit.get_fitted_plot(data_x, data_y, 'Drive Amplitude', 'IQ Amplitude', fig, axs[0])
        x_vals = np.arange(0,self._numTotalRepeats+1)
        axs[0].plot(x_vals, data_y, 'kx')
        axs[0].set_xlabel('Number of Pulses'); axs[0].set_ylabel('Normalised Population')
        axs[0].grid(visible=True, which='minor'); axs[0].grid(visible=True, which='major', color='k');

        for m in range(self._rotDenom+1):
            axs[0].axhline(y=1.0/self._rotDenom*m, color='b', linestyle='dashed')

        ax2 = axs[0].twiny()
        ax2.set_xlim([x*self.drive_time for x in axs[0].get_xlim()])
        ax2.set_xticks(x_vals * self.drive_time)

        fig.show()
        fig.savefig(self._file_path + 'fitted_plot.png')
