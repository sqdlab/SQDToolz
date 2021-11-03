from sqdtoolz.Experiment import*
from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Experiments.Experimental.ExpCalibGE import*

class ExpT1GE(Experiment):
    def __init__(self, name, expt_config, wfmt_qubit_drive, range_waits, SPEC_qubit, iq_indices = [0,1], **kwargs):
        super().__init__(name, expt_config)

        self._iq_indices = iq_indices
        self._wfmt_qubit_drive = wfmt_qubit_drive
        
        self._range_waits = range_waits
        self._post_processor = kwargs.get('post_processor', None)
        self._param_decay_time = kwargs.get('param_T1_decay_time', None)

        self._SPEC_qubit = SPEC_qubit

        #Calculate default load-time via T1 of qubit or default to 40e-6
        def_load_time = self._SPEC_qubit['GE T1'].Value * 4
        if def_load_time == 0:
            def_load_time = 40e-6
        #Override the load-time if one is specified explicitly
        self.load_time = kwargs.get('load_time', 40e-6)

        #Calculate X-Gate amplitude
        def_X_ampl = self._SPEC_qubit['GE X-Gate Amplitude'].Value
        #Override the tip-amplitude if one is specified explicitly
        self.X_ampl = kwargs.get('X_amplitude', def_X_ampl)
        assert self.X_ampl != 0, "X-amplitude is zero. Either supply a X_amplitude or have \'GE X-Gate Amplitude\' inside the qubit SPEC to be non-zero (e.g. run Rabi first?)."

        #Calculate tipping time
        def_X_time = self._SPEC_qubit['GE X-Gate Time'].Value
        #Override the tip-time if one is specified explicitly
        self.X_time = kwargs.get('X_time', def_X_time)
        assert self.X_time != 0, "X-time is zero. Either supply a X_time or have \'GE X-Gate Time\' inside the qubit SPEC to be non-zero (e.g. run Rabi first?)."

        self.readout_time = kwargs.get('readout_time', 2e-6)

        self.normalise_data = kwargs.get('normalise', False)
        assert isinstance(self.normalise_data, bool), 'Argument \'normalise\' must be boolean.'
        self.normalise_reps = kwargs.get('normalise_reps', 5)

        self._expect_rise=kwargs.get('expect_rise',True)    #Only for unnormalised fitting
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."

        if self.normalise_data:
            self.norm_expt = ExpCalibGE('GE Calibration', self._expt_config, self._wfmt_qubit_drive, self.normalise_reps, self._SPEC_qubit, self._iq_indices,
                                        load_time = self.load_time, readout_time = self.readout_time, drive_time = self.X_time)
            self.norm_expt._run(file_path, data_file_index=0, **kwargs)

        self._expt_config.init_instruments()

        wfm = WaveformGeneric(['qubit'], ['readout'])
        wfm.set_waveform('qubit', [
            WFS_Constant("SEQPAD", None, -1, 0.0),
            WFS_Constant("init", None, self.load_time, 0.0),
            WFS_Gaussian("drive", self._wfmt_qubit_drive.apply(phase=0), self.X_time, self.X_ampl),
            WFS_Constant("wait", None, 1e-9, 0.0),
            WFS_Constant("pad", None, 5e-9, 0.0),
            WFS_Constant("read", None, self.readout_time, 0.0)
        ])
        wfm.set_digital_segments('readout', 'qubit', ['read'])
        self._temp_vars = self._expt_config.update_waveforms(wfm, [('Wait Time', 'qubit', 'wait', 'Duration')] )

        sweep_vars = [(self._temp_vars[0], self._range_waits)]

        kwargs['skip_init_instruments'] = True

        self._cur_param_name = self._temp_vars[0].Name
        self._file_path = file_path
        return super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        if self._post_processor:
            self._post_processor.push_data(data)
            data = self._post_processor.get_all_data()
        
        assert self._cur_param_name in data.param_names, "Something went wrong and the sweeping parameter disappeared in the data processing?"
        cur_sweep_ind = data.param_names.index(self._cur_param_name)

        arr = data.get_numpy_array()
        data_x = data.param_vals[cur_sweep_ind]

        dfit = DFitExponential()
        if self.normalise_data:
            data_raw_IQ = np.vstack([ arr[:,self._iq_indices[0]], arr[:,self._iq_indices[1]] ]).T
            fig, axs = plt.subplots(ncols=2, gridspec_kw={'width_ratios':[2,1]})
            fig.set_figheight(5); fig.set_figwidth(15)
            data_y = self.norm_expt.normalise_data(data_raw_IQ, ax=axs[1])

            dpkt = dfit.get_fitted_plot(data_x, data_y, rise=False, fig=fig, axs=axs[0])
            axs[0].set_xlabel('Wait time'); axs[0].set_ylabel('Normalised Population')
            axs[0].grid(b=True, which='minor'); axs[0].grid(b=True, which='major', color='k')
        else:
            data_y = np.sqrt(arr[:,self._iq_indices[0]]**2 + arr[:,self._iq_indices[1]]**2)
            dpkt = dfit.get_fitted_plot(data_x, data_y, rise=self._expect_rise)

        #Commit to parameters...
        if self._param_decay_time:
            self._param_decay_time.Value = dpkt['decay_time']

        self._SPEC_qubit['GE T1'].Value = dpkt['decay_time']

        print(dpkt)
        if self.normalise_data:
            fig.show()
            fig.savefig(self._file_path + 'fitted_plot.png')
        else:
            dpkt['fig'].show()
            dpkt['fig'].savefig(self._file_path + 'fitted_plot.png')
              
