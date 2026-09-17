from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.HAL.ZI.QuantumElements.TunableTransmonCouplerFixed import TunableTransmonCouplerFixed
from sqdtoolz.Experiments.Experimental.ZI import phase_compensation_cz
from sqdtoolz.Experiment import Experiment
from matplotlib import pyplot as plt
from sqdtoolz.Utilities.DataFitting import DFitSinusoid
import numpy as np
from pathlib import Path

class ExpZIPhaseCompensation2Q(Experiment):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._name = name
        self._expt_config = expt_config
        self._hal_QPU = hal_QPU
        assert len(qubit_ids) > 1, "Must supply two coupled qubits, i.e. ['Q0', 'Q2']."
        assert self._expt_config._hal_ACQ.AcquisitionMode == "DISCRIMINATION", "Please set acquisition mode to 'DISCRIMINATION', e.g. lab.HAL('ZIacq').AcquisitionMode = 'DISCRIMINATION'."
        assert self._expt_config._hal_ACQ.AveragingOrder == "SingleShot", "Please set averaging order to 'SingleShot', e.g. lab.HAL('ZIacq').AveragingOrder = 'SingleShot'."
        self._qubit_ids = qubit_ids
        self._normalise_data = kwargs.pop('normalise_data', True)
        self._transition = kwargs.pop('states', 'ge')
        self._update = kwargs.pop('update_coupler', False)

        self._angles = kwargs.pop('rz_angles', np.linspace(0, 2*np.pi, 11))

        self.cur_coupler_obj = kwargs.pop('coupler_obj', None)
        self._coupler_name = kwargs.pop('coupler_name', None)

        # find coupler
        if self.cur_coupler_obj is None:
            self.cur_coupler_obj = hal_QPU.get_coupler_obj_from_qubits(qubit_ids[0], qubit_ids[1], TunableTransmonCouplerFixed)
        self._coupler_name = self.cur_coupler_obj.Name
        print(f"{self._coupler_name}")
        assert self.cur_coupler_obj is not None, "Supply either the name of the coupler 'coupler_name', or a list of coupled qubits in 'qubit_ids'."
        self._coupled_qubits = list(set(self.cur_coupler_obj.get_involved_qubits()))
        self._all_qubits = list(set(self._qubit_ids + self._coupled_qubits))

        # find main pulsed qubit
        flux_signal = self.cur_coupler_obj.signals.get('flux', [])
        main_qubit = next((q for q in self._coupled_qubits if q in flux_signal), None)
        assert main_qubit is not None, "Main qubit not found (matching signal 'flux')."
        self._main_qubit = main_qubit

        # find aux qubit
        flux_aux_signal = self.cur_coupler_obj.signals.get('flux_aux', [])
        aux_qubit = next((q for q in self._coupled_qubits if q in flux_aux_signal), None)
        if aux_qubit is None:
            print("Auxiliary qubit not found (matching signal 'flux_aux').")
        self._aux_qubit = aux_qubit

        self._kwargs = kwargs
        self.data = {}

    def run(self, lab):
        main_qubit = self._main_qubit
        aux_qubit = self._aux_qubit
        
        lab.group_open(self._name)
        print(f"Sweeping phase compensation on {main_qubit} (main)...")
        self.cur_coupler_obj.CompZAngle = None
        exp_main = ExpZIqubit(f'PhaseComp_{self.cur_coupler_obj.Name}_{main_qubit}_Main', self._expt_config, phase_compensation_cz, self._hal_QPU, self._all_qubits, 
                        rz_angles=self._angles, 
                        coupler_name=self._coupler_name,
                        main_or_aux='main',
                        **self._kwargs
                        )
        lab.run_single(exp_main, **self._kwargs)
        #
        data_main = exp_main.retrieve_last_dataset(main_qubit)
        self.data['main_shots'] = data_main.get_numpy_array()[:,:,0]
        self.data['main_pops'] = np.mean(self.data['main_shots'], axis=0)
        self.data['angles'] = data_main.param_vals[1]

        # aux qubit
        if aux_qubit is not None:
            print(f"Sweeping phase compensation on {aux_qubit} (auxiliary)...")
            self.cur_coupler_obj.CompZAngleAux = None
            exp_aux = ExpZIqubit(f'PhaseComp_{self.cur_coupler_obj.Name}_{aux_qubit}_Aux', self._expt_config, phase_compensation_cz, self._hal_QPU, self._all_qubits,
                            rz_angles=self._angles, 
                            coupler_name=self._coupler_name,
                            main_or_aux='aux',
                            **self._kwargs
                            )
            lab.run_single(exp_aux, **self._kwargs)
            #
            data_aux = exp_aux.retrieve_last_dataset(aux_qubit)
            self.data['aux_shots'] = data_aux.get_numpy_array()[:,:,0]
            self.data['aux_pops'] = np.mean(self.data['aux_shots'], axis=0)
        lab.group_close()
        self._file_path = str(Path(exp_aux._file_path).parent)
        

    def post_process(self):
        fit_angles = ExpZIPhaseCompensation2Q.plot_fitted_data(self.data, main_qubit_id=self._main_qubit, coupler_id=self._coupler_name, aux_qubit_id=self._aux_qubit, save_path=self._file_path)
        self.data['fit_angles'] = fit_angles
        if self._update:
            self.cur_coupler_obj.CompZAngle = self.data['fit_angles']['main']
            print(f"Updated {self._coupler_name}.CompZAngle to {self.data['fit_angles']['main']:.4f}")
            if self._aux_qubit is not None:
                self.cur_coupler_obj.CompZAngleAux = self.data['fit_angles']['aux']
                print(f"Updated {self._coupler_name}.CompZAngleAux to {self.data['fit_angles']['aux']:.4f}")

    @staticmethod
    def plot_fitted_data(data, main_qubit_id=None, coupler_id=None, aux_qubit_id=None, save_path=None):
        # plot setup (for main and aux, or just main)
        with_aux = False
        axs = []
        fit_angles = {}
        if data.get('aux_pops', None) is not None:
            with_aux = True
            fig, (ax_main, ax_aux) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
            axs = [ax_main, ax_aux]
        else:
            fig, (ax_main) = plt.subplots(1, 1, figsize=(12, 4))
            axs = [ax_main]
        if main_qubit_id is not None:
            ax_main.set_title(f"Main qubit ({main_qubit_id})")
        else:
            ax_main.set_title(f"Main qubit")
        if with_aux:
            if aux_qubit_id is not None:
                ax_aux.set_title(f"Auxiliary qubit ({aux_qubit_id})")
            else:
                ax_main.set_title("Auxiliary qubit")
        if coupler_id is not None:
            fig.suptitle(f"{coupler_id}: CZ phase compensation")
        else:
            fig.suptitle(f"CZ phase compensation")
        for ax in axs:
            ax.set_ylim([-0.1,1.1])
            ax.set_ylabel(r'Population')
            ax.grid(which='major', alpha=0.3)
            ax.axhline(0, color='tab:green', linestyle='--', linewidth=1, alpha=0.8, zorder=1)
            ax.axhline(1, color='tab:red', linestyle='--', linewidth=1, alpha=0.8, zorder=1)

        angles = np.asarray(data['angles'], dtype=float)
        angles_fine = np.linspace(data['angles'].min(), data['angles'].max(), 501)
        #
        dfit = DFitSinusoid()
        # main
        dpkt = dfit.get_fitted_plot(angles, data['main_pops'], axs=ax_main)
        main_func = dfit.get_plot_data_from_dpkt(angles_fine, dpkt)
        main_comp_angle = angles_fine[np.argmin(main_func)]
        ax_main.plot(main_comp_angle, np.min(main_func), 'go', label=fr"$\theta=${main_comp_angle:.4f} rad")
        fit_angles['main'] = main_comp_angle 
        ax_main.legend()
        # aux
        if with_aux:
            dpkt = dfit.get_fitted_plot(angles, data['aux_pops'], axs=ax_aux)
            aux_func = dfit.get_plot_data_from_dpkt(angles_fine, dpkt)
            aux_comp_angle = angles_fine[np.argmin(aux_func)]
            ax_aux.plot(aux_comp_angle, np.min(aux_func), 'go', label=fr"$\theta=${aux_comp_angle:.4f} rad")
            ax_aux.set_xlabel(r'$Rz(\theta)$ (radians)')
            ax_aux.legend()
            fit_angles['aux'] = aux_comp_angle
        else:
            ax_main.set_xlabel(r'$Rz(\theta)$ (radians)')
        if save_path is not None:
            fig.savefig(save_path + "/fitted_plot.png")

        return fit_angles