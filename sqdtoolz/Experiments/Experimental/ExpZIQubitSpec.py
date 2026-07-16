from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import qubit_spectroscopy
from sqdtoolz.Experiments.Experimental.ZI import qubit_spectroscopy_gef

class ExpZIQubitSpec(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_id, **kwargs):
        assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        self._qubit_dataset = qubit_id

        self._update_qubit = kwargs.pop('update_qubit_params', True)
        self._states = kwargs.pop('states', 'ge')
        # assert self._states in ['ge', 'ef'], "Supply states as either 'ge' or 'ef'."
        assert self._states=='ge', "Only states='ge' qubit spectroscopy currently supported." # TODO: fix 'ef' spectroscopy
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
    
        self._iq_indices = kwargs.pop('iq_indices', [0,1])
        self._is_trough = kwargs.pop('is_trough', False)
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')
        self._hal_QPU = hal_QPU
        self._spectroscopy_reset_delay = kwargs.pop('spectroscopy_reset_delay', 200e-6)

        if self._states=='ge':
            super().__init__(name, expt_config, qubit_spectroscopy, hal_QPU, [qubit_id], **kwargs)
        elif self._states=='ef':
            kwargs['states'] = self._states
            kwargs['spectroscopy_reset_delay'] = self._spectroscopy_reset_delay
            super().__init__(name, expt_config, qubit_spectroscopy_gef, hal_QPU, [qubit_id], **kwargs)
    
    def _post_process(self, data):
        data = self.retrieve_last_dataset(self._qubit_dataset)
        assert len(data.param_names), "The sweep should only be 1D."

        arr = data.get_numpy_array()
        data_x = data.param_vals[0]
        data_y = np.sqrt(arr[:,self._iq_indices[0]]**2 + arr[:,self._iq_indices[1]]**2)

        dfit = DFitPeakLorentzian()
        dpkt = dfit.get_fitted_plot(data_x, data_y**2, xLabel="Frequency (Hz)", title=f"{self._qubit_dataset} ({self._states})", dip=self._is_trough, dontplot=self._dont_plot, xUnits=self._xUnits)
        #Commit to parameters...
        if self._update_qubit:
            cur_qubit = self._hal_QPU.get_qubit_obj(self._qubit_dataset)
            if self._states=='ge':
                cur_qubit.DriveGE = dpkt['centre']
            elif self._states=='ef':
                cur_qubit.DriveEF = dpkt['centre']
        dpkt['fit_data'] = {'squared_amplitude': dpkt['fit_data']}

        if not self._dont_plot:
            if not self._dont_show_plot:
                dpkt['fig'].show()
            dpkt['fig'].savefig(self._file_path + 'fitted_plot.png')
        if 'fit_data' in dpkt:
            np.save(self._file_path + 'fitted_data.npy', dpkt['fit_data'])
