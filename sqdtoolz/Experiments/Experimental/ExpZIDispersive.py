from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
import matplotlib
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
        self._fit_type = kwargs.pop('fit_type', 'Circlefit')  #Default, Fano, Full
        assert self._is_trough or (not self._is_trough and not self._fit_type=='Fano'), "Fano resonance fitting only supports troughs at the moment."
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')
        self._states = kwargs.get('states', 'ge')
        self._chi = kwargs.pop('chi', None)
        self._calc_thermal_photons = kwargs.pop('calc_thermal_photons', False)
        self._update_params = kwargs.get('update', True)

        assert self._fit_type in ['Circlefit', 'Minimum'], "Choose fit_type 'Circlefit' or 'Minimum'."

        super().__init__(name, expt_config, dispersive_shift, hal_QPU, qubit_ids, **kwargs)
    
    def _post_process(self, data):
        if self._states == 'ge':
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
                #
                pwr = self._hal_QPU.get_qubit_obj(qubit).ReadoutLineAttenuation_dB
                g_dpkt = ResonatorPowerSweep.single_circlefit(g_data_x, g_data_i, g_data_q, power_dBm=pwr, dont_plot=True, pass_fits=True)
                e_dpkt = ResonatorPowerSweep.single_circlefit(e_data_x, e_data_i, e_data_q, power_dBm=pwr, dont_plot=True, pass_fits=True)
                #
                if self._fit_type == "Circlefit":
                    if e_dpkt and g_dpkt:
                        chi = (e_dpkt['fr'] - g_dpkt['fr'])/2
                        target_f = e_dpkt['fr'] + chi
                    else:
                        chi = 0
                        target_f = None
                        print("Fit failed, so chi was not updated.")
                elif self._fit_type == "Minimum":
                    g_min_f = g_data_x[np.argmin(g_data_y)]
                    e_min_f = e_data_x[np.argmin(e_data_y)]
                    chi = (e_min_f - g_min_f)/2
                    target_f = e_min_f + chi
                #
                if self._calc_thermal_photons:
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
                    if target_f:
                        cur_qubit.ReadoutFrequency = target_f
                    if e_dpkt and g_dpkt:
                        cur_qubit.ChiGE = chi
                    if self._calc_thermal_photons:
                        cur_qubit.ReadoutKappa = kappa
                        cur_qubit.ThermalPhotonNum = float(np.atleast_1d(n_th)[0])
                if not self._dont_plot:
                    fig, ax = plt.subplots()
                    fig.set_figwidth(15)
                    ax.plot(g_data_x*1e-9, g_data_y, 'x', label=f"g ({g_dpkt['fr']*1e-9:.4f} GHz)", c='tab:blue')
                    ax.plot(e_data_x*1e-9, e_data_y, 'x', label=f"e ({e_dpkt['fr']*1e-9:.4f} GHz)", c='tab:orange')                
                    if e_dpkt and g_dpkt:
                        ax.plot(g_data_x*1e-9, np.absolute(g_dpkt['fit_data']), c='tab:blue', alpha=1)
                        ax.plot(e_data_x*1e-9, np.absolute(e_dpkt['fit_data']), c='tab:orange', alpha=1)
                        if self._fit_type == 'Circlefit':
                            ax.axvline(g_dpkt['fr']*1e-9, lw=2, ls='dashed', alpha=1, c='tab:blue')
                            ax.axvline(e_dpkt['fr']*1e-9, lw=2, ls='dashed', alpha=1, c='tab:orange')
                    if self._fit_type == "Minimum":
                        ax.axvline(g_min_f*1e-9, lw=2, ls='dashed', c='tab:blue', alpha=1)
                        ax.axvline(e_min_f*1e-9, lw=2, ls='dashed', c='tab:orange', alpha=1)
                    if chi != 0:
                        ax.set_title(f"{qubit} dispersive shift: " + r"$\chi_{ge}=$"+f"{chi*1e-6:.3f} MHz")
                    else:
                        ax.set_title(f"{qubit}")
                    ax.legend()
                    ax.set_xlabel("f (GHz)")
                    ax.set_ylabel(r"$|S_{21}|$")
                    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f'{x:.4f}'))
                    if not self._dont_show_plot:
                        fig.show()
                    fig.savefig(self._file_path + 'dispersive_shift_ge.png')