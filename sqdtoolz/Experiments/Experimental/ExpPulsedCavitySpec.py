from sqdtoolz.Experiment import*
from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.Utilities.DataFitting import*

class ExpPulsedCavitySpec(Experiment):
    def __init__(self, name, expt_config, wfmt_qubit_drive, var_cav_freq, cav_freq_range, SPEC_qubit, iq_indices = [0,1], **kwargs):
        super().__init__(name, expt_config)

        self._iq_indices = iq_indices
        self._wfmt_qubit_drive = wfmt_qubit_drive
        
        self._var_cav_freq = var_cav_freq
        self._cav_freq_range = cav_freq_range
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

        self.runG = kwargs.get('scan_ground', True)
        self.runE = kwargs.get('scan_excited', True)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."

        ex_ampls = []
        if self.runG:
            ex_ampls += [0.0]
        if self.runE:
            ex_ampls += [self.X_ampl]

        ret_datas = []        
        for m, cur_ampl in enumerate(ex_ampls):
            self._expt_config.init_instruments()
            wfm = WaveformGeneric(['qubit'], ['readout'])
            wfm.set_waveform('qubit', [
                WFS_Constant("SEQPAD", None, -1, 0.0),
                WFS_Constant("init", None, self.load_time, 0.0),
                WFS_Gaussian("drive", self._wfmt_qubit_drive.apply(phase=0), self.X_time, cur_ampl),
                WFS_Constant("pad", None, 5e-9, 0.0),
                WFS_Constant("read", None, self.readout_time, 0.0)
            ])
            wfm.set_digital_segments('readout', 'qubit', ['read'])
            self._temp_vars = self._expt_config.update_waveforms(wfm)

            sweep_vars = [(self._var_cav_freq, self._cav_freq_range)]

            kwargs['skip_init_instruments'] = True

            ret_datas += [super()._run(file_path, sweep_vars, data_file_index=m, **kwargs)]
        return ret_datas

    def _post_process(self, data):
        #TODO: Once there are nice dispersive peaks, work on fitting the individual traces and printing the dispersive shift...

        dataG = data[0].get_numpy_array()
        dataE = data[1].get_numpy_array()

        fig, ax = plt.subplots(1)

        legend_vals = []
        if self.runG:
            ax.plot(self._cav_freq_range, dataG[:,self._iq_indices[0]]**2+dataG[:,self._iq_indices[1]]**2)
            legend_vals += ['Ground']
        if self.runE:
            ax.plot(self._cav_freq_range, dataE[:,self._iq_indices[0]]**2+dataE[:,self._iq_indices[1]]**2)
            legend_vals += ['Excited']
        ax.set_xlabel('Cavity Frequency'); ax.set_ylabel('|I+jQ|^2')
        ax.grid(visible=True, which='minor'); ax.grid(visible=True, which='major', color='k')
        ax.legend(legend_vals)

        fig.show()
