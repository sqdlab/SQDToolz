from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Utilities.ResonatorTools import ResonatorPowerSweep
from laboneq_applications.experiments import dispersive_shift
from scipy.optimize import fsolve

class ExpZIDispersive(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        #TODO: pass states
        self._qubit_datasets = qubit_ids
        self._hal_QPU = hal_QPU
        self._dont_show_plot = kwargs.get('dont_show_plot', False)
        self._iq_indices = kwargs.pop('iq_indices', [0,1])
        self._is_trough = kwargs.pop('is_trough', False)
        self._fit_type = kwargs.pop('fit_type', 'Default')  #Default, Fano, Full
        #assert self._is_trough or (not self._is_trough and not self._fit_res_fano), "Fano resonance fitting only supports troughs at the moment."
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')
        self._chi = kwargs.pop('chi', None)
        self._calc_thermal_photons = kwargs.get('calc_thermal_photons', False)

        super().__init__(name, expt_config, dispersive_shift, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        for qubit in self._qubit_datasets:
            g_qubit_dataset = qubit + '_g'
            e_qubit_dataset = qubit + '_e'
            g_data = self.retrieve_last_dataset(g_qubit_dataset)
            e_data = self.retrieve_last_dataset(e_qubit_dataset)
            assert len(g_data.param_names), "The sweep should only be 1D."
            assert len(e_data.param_names), "The sweep should only be 1D."
            g_arr, e_arr = g_data.get_numpy_array(), e_data.get_numpy_array()
            g_data_x, e_data_x = g_data.param_vals[0], e_data.param_vals[0]
            g_data_i, e_data_i = g_arr[:,self._iq_indices[0]], e_arr[:,self._iq_indices[0]]
            g_data_q, e_data_q = g_arr[:,self._iq_indices[1]], e_arr[:,self._iq_indices[1]]
            g_data_y, e_data_y  = np.sqrt(g_arr[:,self._iq_indices[0]]**2 + g_arr[:,self._iq_indices[1]]**2),np.sqrt(e_arr[:,self._iq_indices[0]]**2 + e_arr[:,self._iq_indices[1]]**2)

            if self._fit_type == "Default":
                dfit = DFitPeakLorentzian()
                g_dpkt = ResonatorPowerSweep.single_circlefit(g_data_x, g_data_i, g_data_q, power_dBm=-100, dont_plot=self._dont_plot)
                e_dpkt = ResonatorPowerSweep.single_circlefit(e_data_x, e_data_i, e_data_q, power_dBm=-100, dont_plot=self._dont_plot)
                #Commit to parameters...
                chi = (e_dpkt['fr'] - g_dpkt['fr'])/2
                # if self._chi:
                #     self._chi.Value = (e_dpkt['fr'] - g_dpkt['fr'])/2
            if self._calc_thermal_photons:
                # chi = (lab.HAL('Qubit0').ChiGE)
                # T2 = lab.HAL('Qubit0').T2GE
                try:
                    Ql = self._hal_QPU.get_qubit_obj(qubit).ReadoutQl
                    omega_r = (self._hal_QPU.get_qubit_obj(qubit).ReadoutFrequency)*2*np.pi
                    kappa = 1/Ql/omega_r
                    T2 = self._hal_QPU.get_qubit_obj(qubit).T2GE
                except:
                    print(f"Could not calculate thermal photon number: T2GE measurement required first.")
                def nThermal_from_T2star(n):
                    eq1 = 1/T2 - 4*chi**2*n/(kappa)*(n+1)
                    return eq1
                n_th = fsolve(nThermal_from_T2star, 0.001)
                # print(f"Estimate thermal photons: {solution}")
            if self._update_params:
                cur_qubit = self._hal_QPU.get_qubit_obj(qubit)
                cur_qubit.ChiGE = (e_dpkt['fr'] - g_dpkt['fr'])/2
                if self._calc_thermal_photons:
                    cur_qubit.ReadoutKappa = kappa
                    cur_qubit.ThermalPhotonNum = n_th
            if not self._dont_plot:
                #TODO: combine ge plots
                g_dpkt['fig'].show()
                g_dpkt['fig'].savefig(self._file_path + 'fitted_plot.png')