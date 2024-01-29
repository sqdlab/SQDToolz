from sqdtoolz.Experiment import*
from sqdtoolz.HAL.WaveformGeneric import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Experiments.Experimental.ExpCalibGE import*

class ExpRabi(Experiment):
    '''
    An automated Rabi experiment.

    Inputs
    ---------
    name (str): Name of experiment directory for saving purposes
    expt_config (ExperimentConfiguration): custom experiment config
    wfmt_qubit_drive (WaveformTransformation): Qubit drive 
    range_amps (np.array): Range of amplitudes to sweep
    SPEC_qubit (ExperimentSpecification): Experiment Spec for qubit of interest
    transition (str) [default 'GE']: select transition to drive
    phase (float) [default 0]: Axis of rotation for drive; typically a multiple of pi/2
    iq_indices (list[int]) [default [0,1]]: Data indices for I and Q components

    Outputs
    ---------
    Returns data, displays plotted data, saves calibrations into SPEC_qubit
    '''
    def __init__(self, name, expt_config, wfmt_qubit_drive, range_amps, SPEC_qubit, transition='GE', phase=0, iq_indices = [0,1], **kwargs):
        super().__init__(name, expt_config)

        self._iq_indices = iq_indices
        self._wfmt_qubit_drive = wfmt_qubit_drive

        assert transition == 'GE' or transition == 'EF', "Transition must be either GE or EF"
        self._transition = transition

        assert (phase >= 0) & (phase <= 2*np.pi), "Phase must be between 0 and 2pi"
        self._phase = phase
        
        # self._range_amps = kwargs.get('range_amps', None)
        self._range_amps = range_amps
        self._post_processor = kwargs.get('post_processor', None)
        self._param_rabi_frequency = kwargs.get('param_rabi_frequency', None)
        self._param_rabi_decay_time = kwargs.get('param_rabi_decay_time', None)

        self._SPEC_qubit = SPEC_qubit

        #Calculate default load-time via T1 of qubit or default to 40e-6
        def_load_time = self._SPEC_qubit[transition + ' T1'].Value * 4
        if def_load_time == 0:
            def_load_time = 40e-6
        #Override the load-time if one is specified explicitly
        self.load_time = kwargs.get('load_time', def_load_time)

        self.readout_time = kwargs.get('readout_time', 2e-6)
        self.drive_time = kwargs.get('drive_time', 20e-9)

        self.normalise_data = kwargs.get('normalise', False)
        assert isinstance(self.normalise_data, bool), 'Argument \'normalise\' must be boolean.'
        self.normalise_reps = kwargs.get('normalise_reps', 5)

        self._dont_update_values = kwargs.get('dont_update_values', False)
    
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
        self._temp_vars = self._expt_config.update_waveforms(wfm, [('Drive Amplitude', 'qubit', 'drive', 'Amplitude')] )

        sweep_vars = [(self._temp_vars[0], self._range_amps)]

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

        dfit = DFitSinusoid()
        if self.normalise_data:
            data_raw_IQ = np.vstack([ arr[:,self._iq_indices[0]], arr[:,self._iq_indices[1]] ]).T
            fig, axs = plt.subplots(ncols=2, gridspec_kw={'width_ratios':[2,1]})
            fig.set_figheight(5); fig.set_figwidth(15)
            data_y = self.norm_expt.normalise_data(data_raw_IQ, ax=axs[1])

            dpkt = dfit.get_fitted_plot(data_x, data_y, 'Drive Amplitude', 'IQ Amplitude', axs[0])
            axs[0].set_xlabel('Amplitude'); axs[0].set_ylabel('Normalised Population')
            axs[0].grid(visible=True, which='minor'); axs[0].grid(visible=True, which='major', color='k');
        else:
            data_y = np.sqrt(arr[:,self._iq_indices[0]]**2 + arr[:,self._iq_indices[1]]**2)
            dpkt = dfit.get_fitted_plot(data_x, data_y, 'Drive Amplitude', 'IQ Amplitude')

        #Commit to parameters...
        if self._param_rabi_frequency:
            self._param_rabi_frequency.Value = dpkt['frequency']
        if self._param_rabi_decay_time:
            self._param_rabi_decay_time.Value = 1.0 / dpkt['decay_rate']

        axis = None
        if self._phase == 0:
            axis = 'X'
        elif self._phase == np.pi/2:
            axis = 'Y'
        elif self._phase == np.pi:
            axis = '-X'
        elif self._phase == 3*np.pi/2:
            axis = '-Y'

        if (not self._dont_update_values) and (axis is None):
            raise ValueError('Cannot update gate parameters if chosen phase is arbitrary (non-multiple of pi/2)')

        if not self._dont_update_values:
            if self._transition == 'GE':
                if self.normalise_data:
                    #Find X and X/2 amplitudes...
                    n = np.ceil( dpkt['phase']/(2*np.pi) )
                    amp_X = ( 2*n*np.pi - dpkt['phase'] ) / ( 2*np.pi * dpkt['frequency'] )
                    amp_Xon2 = amp_X - 0.25 / dpkt['frequency']

                    #Plot X and X/2 points on plot...
                    axs[0].plot([amp_Xon2, amp_Xon2], [0,1], '-b')
                    axs[0].plot([amp_X, amp_X], [0,1], '-b')
                    axs[0].text(amp_Xon2, 0.5, '$\pi/2$')
                    axs[0].text(amp_X, 0.5, '$\pi$')

                    self._SPEC_qubit[f'GE {axis}/2-Gate Amplitude'].Value = amp_Xon2
                    self._SPEC_qubit[f'GE {axis}/2-Gate Time'].Value = self.drive_time
                    self._SPEC_qubit[f'GE {axis}-Gate Amplitude'].Value = amp_X
                    self._SPEC_qubit[f'GE {axis}-Gate Time'].Value = self.drive_time
                else:
                    self._SPEC_qubit[f'GE {axis}/2-Gate Amplitude'].Value = 0.25/dpkt['frequency']
                    self._SPEC_qubit[f'GE {axis}/2-Gate Time'].Value = self.drive_time
                    self._SPEC_qubit[f'GE {axis}-Gate Amplitude'].Value = 0.5/dpkt['frequency']
                    self._SPEC_qubit[f'GE {axis}-Gate Time'].Value = self.drive_time
            else:
                assert False, 'Ask Developer about the EF :P'
                self._SPEC_qubit['EF X-Gate Amplitude'].Value = 0.5/dpkt['frequency']
                self._SPEC_qubit['EF X-Gate Time'].Value = self.drive_time
                self._SPEC_qubit['EF X-Gate Amplitude'].Value = 0.25/dpkt['frequency']
                self._SPEC_qubit['EF X-Gate Time'].Value = self.drive_time

        if self.normalise_data:
            fig.show()
            fig.savefig(self._file_path + 'fitted_plot.png')
        else:
            dpkt['fig'].show()
            dpkt['fig'].savefig(self._file_path + 'fitted_plot.png')