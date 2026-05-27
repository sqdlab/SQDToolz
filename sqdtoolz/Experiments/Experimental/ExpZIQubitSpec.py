from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import qubit_spectroscopy

class ExpZIQubitSpec(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_id, **kwargs):
        assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        self._qubit_dataset = qubit_id

        self._update_qubit = kwargs.pop('update_qubit_params', True)

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
    
        self._iq_indices = kwargs.pop('iq_indices', [0,1])
        self._is_trough = kwargs.pop('is_trough', False)
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')
        self._hal_QPU = hal_QPU

        super().__init__(name, expt_config, qubit_spectroscopy, hal_QPU, [qubit_id], **kwargs)
    
    def _post_process(self, data):
        data = self.retrieve_last_dataset(self._qubit_dataset)
        assert len(data.param_names), "The sweep should only be 1D."

        arr = data.get_numpy_array()
        data_x = data.param_vals[0]
        data_y = np.sqrt(arr[:,self._iq_indices[0]]**2 + arr[:,self._iq_indices[1]]**2)

        dfit = DFitPeakLorentzian()
        dpkt = dfit.get_fitted_plot(data_x, data_y**2, xLabel="Frequency (Hz)", dip=self._is_trough, dontplot=self._dont_plot, xUnits=self._xUnits)
        #Commit to parameters...
        if self._update_qubit:
            cur_qubit = self._hal_QPU.get_qubit_obj(self._qubit_dataset)
            cur_qubit.DriveGE = dpkt['centre']
        dpkt['fit_data'] = {'squared_amplitude': dpkt['fit_data']}

        if not self._dont_plot:
            if not self._dont_show_plot:
                dpkt['fig'].show()
            dpkt['fig'].savefig(self._file_path + 'fitted_plot.png')
        if 'fit_data' in dpkt:
            np.save(self._file_path + 'fitted_data.npy', dpkt['fit_data'])
