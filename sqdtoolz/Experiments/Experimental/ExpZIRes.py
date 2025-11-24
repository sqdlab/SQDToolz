from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Utilities.ResonatorTools import ResonatorPowerSweep
from laboneq_applications.experiments import (
    resonator_spectroscopy,
    resonator_spectroscopy_amplitude,
)

class ExpZIRes(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_id, **kwargs):
        assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        self._qubit_dataset = qubit_id

        self._update_qubit = kwargs.pop('update_qubit_params', True)

        self._iq_indices = kwargs.pop('iq_indices', [0,1])
        self._is_trough = kwargs.pop('is_trough', False)
        self._fit_type = kwargs.pop('fit_type', 'Default')  #Default, Fano, Full
        assert self._is_trough or (not self._is_trough and not self._fit_res_fano), "Fano resonance fitting only supports troughs at the moment."
        self._param_centre = kwargs.pop('param_freq', None)
        self._param_width = kwargs.pop('param_width', None)
        self._param_amplitude = kwargs.pop('param_amplitude', None)
        self._param_offset = kwargs.pop('param_offset', None)
        self._param_fano = kwargs.pop('param_fano', None)
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')

        self._hal_QPU = hal_QPU

        super().__init__(name, expt_config, resonator_spectroscopy, hal_QPU, [qubit_id], **kwargs)
    
    def _post_process(self, data):
        data = self.retrieve_last_dataset(self._qubit_dataset)
        assert len(data.param_names), "The sweep should only be 1D."

        arr = data.get_numpy_array()
        data_x = data.param_vals[0]
        data_i = arr[:,self._iq_indices[0]]
        data_q = arr[:,self._iq_indices[1]]
        data_y = np.sqrt(arr[:,self._iq_indices[0]]**2 + arr[:,self._iq_indices[1]]**2)

        if self._fit_type == "Default":
            dfit = DFitPeakLorentzian()
            dpkt = dfit.get_fitted_plot(data_x, data_y, xLabel="Frequency (Hz)", dip=self._is_trough, dontplot=self._dont_plot, xUnits=self._xUnits)
            #Commit to parameters...
            if self._update_qubit:
                cur_qubit = self._hal_QPU.get_qubit_obj(self._qubit_dataset)
                cur_qubit.ReadoutFrequency = dpkt['centre']
            if self._param_centre:
                self._param_centre.Value = dpkt['centre']
            if self._param_width:
                self._param_width.Value = dpkt['width']
            if self._param_amplitude:
                self._param_amplitude.Value = dpkt['amplitude']
            if self._param_offset:
                self._param_offset.Value = dpkt['offset']
        elif self._fit_type == "Fano":
            dfit = DFitFanoResonance()
            dpkt = dfit.get_fitted_plot(data_x, data_y**2, xLabel="Frequency (Hz)", yLabel="Squared IQ Amplitude", dontplot=self._dont_plot, xUnits=self._xUnits) #, dip=self._is_trough)
            #Commit to parameters...
            if self._update_qubit:
                cur_qubit = self._hal_QPU.get_qubit_obj(self._qubit_dataset)
                cur_qubit.ReadoutFrequency = dpkt['xMinimum']
            if self._param_centre:
                self._param_centre.Value = dpkt['xMinimum']
            if self._param_width:
                self._param_width.Value = dpkt['width']
            if self._param_amplitude:
                self._param_amplitude.Value = dpkt['amplitude']
            if self._param_offset:
                self._param_offset.Value = dpkt['offset']
            if self._param_fano:
                self._param_offset.Value = dpkt['FanoFac']
        elif self._fit_type == "Full":
            dpkt = ResonatorPowerSweep.single_circlefit(data_x, data_i, data_q, power_dBm=-100, dont_plot=self._dont_plot)
            #Commit to parameters...
            if self._update_qubit:
                cur_qubit = self._hal_QPU.get_qubit_obj(self._qubit_dataset)
                cur_qubit.ReadoutFrequency = dpkt['fr']
                cur_qubit.ReadoutQi = dpkt['Qi_dia_corr']
                cur_qubit.ReadoutQc = dpkt['Qc_dia_corr']
                cur_qubit.ReadoutQl = dpkt['Ql']
            if self._param_centre:
                self._param_centre.Value = dpkt['fr']

        if not self._dont_plot:
            dpkt['fig'].show()
            dpkt['fig'].savefig(self._file_path + 'fitted_plot.png')
