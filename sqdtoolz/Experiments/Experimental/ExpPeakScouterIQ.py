from sqdtoolz.Experiment import*
from sqdtoolz.Utilities.DataFitting import*

class ExpPeakScouterIQ(Experiment):
    def __init__(self, name, expt_config, iq_indices = [0,1], **kwargs):
        super().__init__(name, expt_config)

        self._iq_indices = iq_indices
        self._post_processor = kwargs.get('post_processor', None)
        self._param_centre = kwargs.get('param_centre', None)
        self._param_width = kwargs.get('param_width', None)
        self._param_amplitude = kwargs.get('param_amplitude', None)
        self._param_offset = kwargs.get('param_offset', None)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 1, "Can only sweep one variable in this experiment."
        self._cur_param_name = sweep_vars[0][0].Name
        return super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        if self._post_processor:
            self._post_processor.push_data(data)
            data = self._post_processor.get_all_data()
        
        assert self._cur_param_name in data.param_names, "Something went wrong and the sweeping parameter disappeared in the data processing?"
        cur_sweep_ind = data.param_names.index(self._cur_param_name)

        arr = leData.get_numpy_array()
        data_x = data.param_vals[cur_sweep_ind]
        data_y = np.sqrt(arr[:,self._iq_indices[0]]**2 + arr[:,self._iq_indices[1]]**2)

        dfit = DFitPeakLorentzian()
        dpkt = dfit.get_fitted_plot(data_x, data_y)

        #Commit to parameters...
        if self._param_centre:
            self._param_centre.Value = dpkt['centre']
        if self._param_width:
            self._param_width.Value = dpkt['width']
        if self._param_amplitude:
            self._param_amplitude.Value = dpkt['amplitude']
        if self._param_offset:
            self._param_offset.Value = dpkt['offset']

        dpkt['fig'].show()
        
