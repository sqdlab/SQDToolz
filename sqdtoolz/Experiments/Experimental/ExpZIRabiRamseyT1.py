import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIResFluxSweep import ExpZIResFluxSweep
from sqdtoolz.Experiments.Experimental.ExpZIRes import ExpZIRes
from sqdtoolz.Experiments.Experimental.ExpZIQubitSpec import ExpZIQubitSpec
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ExpZIRabi import ExpZIRabi
from sqdtoolz.Experiments.Experimental.ExpZIRamsey import ExpZIRamsey
from sqdtoolz.Experiments.Experimental.ExpZIT1 import ExpZIT1
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import matplotlib.pyplot as plt
import matplotlib.gridspec
from pathlib import Path

class ExpZIRabiRamseyT1:
    def __init__(self, name, expt_config, hal_QPU, qubit_id, states='ge', **kwargs):
        self._name = name
        self._expt_config = expt_config
        self._qpu = hal_QPU
        self._qubit_id = qubit_id
        
        self._qubit = self._qpu.get_qubit_obj(self._qubit_id)

        assert states in ['ge', 'ef'], "Supply 'states' as either 'ge' or 'ef'."
        self._states = states

        self._qubit_spec_LO_power = kwargs.pop('qubit_spec_LO_power', -20)
        self._qubit_time_domain_LO_power = kwargs.pop('qubit_time_domain_LO_power', 10)

        self._ef_frequency = kwargs.pop('ef_guess', self._qubit.DriveEF)

        self._res_trough = kwargs.pop('res_is_trough', True)
        
        self._individual_plots = kwargs.pop('individual_plots', False)
        self._update_live = kwargs.pop('update_params_live', True)
        self._enable_ZI_log_messages = kwargs.pop('enable_ZI_log_messages', False)
        self._assume_detuned_above = kwargs.pop('ramsey_assume_detuned_above', True)
        #
        if 'rabi_amplitudes' in kwargs:
            self._rabi_ampls = kwargs.pop('rabi_amplitudes')
            assert not 'rabi_points' in kwargs, "Do not supply 'rabi_points' if supplying 'rabi_amplitudes'"
        else:
            self._rabi_ampls = np.linspace(0,1,kwargs.pop('rabi_points',30))
        #
        self._ramsey_fast_detuning = kwargs.pop('ramsey_fast_detuning', 2e6)
        if 'ramsey_fast_times' in kwargs:
            self._ramsey_fast_times = kwargs.pop('ramsey_fast_times')
            assert not 'ramsey_fast_max' in kwargs, "Do not supply 'ramsey_fast_max' if supplying 'ramsey_fast_times'"
            assert not 'ramsey_fast_points' in kwargs, "Do not supply 'ramsey_fast_points' if supplying 'ramsey_fast_times'"
        else:
            max_fast_time = kwargs.pop('ramsey_fast_max', 2e-6)
            max_fast_points = kwargs.pop('ramsey_fast_points', 40)
            self._ramsey_fast_times = np.linspace(0,max_fast_time, max_fast_points)
        #
        self._ramsey_slow_detuning = kwargs.pop('ramsey_slow_detuning', 0.125e6)
        if 'ramsey_slow_times' in kwargs:
            self._ramsey_slow_times = kwargs.pop('ramsey_slow_times')
            assert not 'ramsey_slow_max' in kwargs, "Do not supply 'ramsey_slow_max' if supplying 'ramsey_slow_times'"
            assert not 'ramsey_slow_points' in kwargs, "Do not supply 'ramsey_slow_points' if supplying 'ramsey_slow_times'"
        else:
            max_slow_time = kwargs.pop('ramsey_slow_max', 60e-6)
            max_slow_points = kwargs.pop('ramsey_slow_points', 60)
            self._ramsey_slow_times = np.linspace(0,max_slow_time, max_slow_points)
        #
        if 't1_times' in kwargs:
            self._t1_times = kwargs.pop('t1_times')
            assert not 't1_max' in kwargs, "Do not supply 't1_max' if supplying 't1_times'"
            assert not 't1_points' in kwargs, "Do not supply 't1_points' if supplying 't1_times'"
        else:
            max_t1_time = kwargs.pop('t1_max', 100e-6)
            max_t1_points = kwargs.pop('t1_points', 40)
            self._t1_times = np.linspace(0,max_t1_time, max_t1_points)

    def run(self, lab):
        fig = plt.figure(layout="constrained"); fig.set_figwidth(12); fig.set_figheight(8)
        gs = matplotlib.gridspec.GridSpec(3, 2, figure=fig)
        if self._states=='ge':
            freq = self._qubit.DriveGE
        else:
            freq = self._qubit.DriveEF
        fig.suptitle(f"{self._qubit_id}: {self._states} characterisation ($f={freq*1e-9:.3f}$ GHz)", fontsize=16, fontweight='bold')
        #
        lab.group_open(self._name)
        ##############################
        #
        #RABI
        #
        self._qubit.DrivePower = self._qubit_time_domain_LO_power
        if self._states=='ge':
            self._qubit.DriveGEAmplitudeX = 1.0
            self._qubit.DriveGEAmplitudeXon2 = 0.5  
        else:
            self._qubit.DriveEFAmplitudeX = 1.0
            self._qubit.DriveEFAmplitudeXon2 = 0.5  
        exp = ExpZIRabi(f'rabi_pre_cal_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], amplitudes=[self._rabi_ampls], transition=self._states, 
                        cal_states=self._states, update=self._update_live, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots, use_cal_traces=False)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        exp = ExpZIRabi(f'rabi_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], amplitudes=[self._rabi_ampls], transition=self._states, 
                        cal_states=self._states, update=self._update_live, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[0, :])
        fitted_data = np.load(exp._file_path + f'fitted_data_{self._qubit_id}.npy', allow_pickle=True).item()
        arr = leData.get_numpy_array()
        data_x = leData.param_vals[0]
        ExpZIRabi.plot_fitted_results(ax, data_x, fitted_data['amplitude_raw'], fitted_data, True)
        sigFigs = 4
        ax.set_title(f"Rabi amplitudes: X={fitted_data['amp_X']:.{sigFigs}g}, X/2={fitted_data['amp_Xon2']:.{sigFigs}g}")
        ##############################
        #
        #RAMSEY
        #
        #Fast
        exp = ExpZIRamsey(f'ramsey_fast_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], delays=[self._ramsey_fast_times], 
                          detunings=[self._ramsey_fast_detuning], transition=self._states, cal_states=self._states, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[1, 0])
        fitted_data = np.load(exp._file_path + f"fitted_data_{self._qubit_id}.npy", allow_pickle=True).item()
        arr = leData.get_numpy_array()
        data_x = leData.param_vals[0]
        ExpZIRamsey.plot_fitted_results(ax, data_x, fitted_data['amplitude_raw'], self._qubit_id, fitted_data, True)
        sigFigs = 4
        ax.set_title(f"Ramsey Δ={Miscellaneous.get_units(self._ramsey_fast_detuning,4)}Hz, f={Miscellaneous.get_units(fitted_data['frequency'],4)}Hz")
        exp.update_qubits() #TODO: Add error-checking here to slam brakes if necessary
        #
        #Slow
        exp = ExpZIRamsey(f'ramsey_slow_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], delays=[self._ramsey_slow_times], 
                          detunings=[self._ramsey_slow_detuning], transition=self._states, cal_states=self._states, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[1, 1])
        fitted_data = np.load(exp._file_path + f"fitted_data_{self._qubit_id}.npy", allow_pickle=True).item()
        arr = leData.get_numpy_array()
        data_x = leData.param_vals[0]
        ExpZIRamsey.plot_fitted_results(ax, data_x, fitted_data['amplitude_raw'], self._qubit_id, fitted_data, True)
        sigFigs = 4
        ax.set_title(f"Ramsey Δ={Miscellaneous.get_units(self._ramsey_slow_detuning,4)}Hz, f={Miscellaneous.get_units(fitted_data['frequency'],4)}Hz, T2*={Miscellaneous.get_units(fitted_data['T2*'],4)}s")
        exp.update_qubits(assume_detuned_above=self._assume_detuned_above) #TODO: Add error-checking here to slam brakes if necessary
        ##############################
        #
        #T1
        #
        exp = ExpZIT1(f'T1_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], delays=[self._t1_times], transition=self._states, 
                      cal_states=self._states, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[2, :])
        fitted_data = np.load(exp._file_path + f'fitted_data_{self._qubit_id}.npy', allow_pickle=True).item()
        arr = leData.get_numpy_array()
        data_x = leData.param_vals[0]
        ExpZIT1.plot_fitted_results(ax, data_x, fitted_data['amplitude_raw'], fitted_data, True)
        ax.set_title(f"T1: {Miscellaneous.get_units(fitted_data['T1'],4)}s")
        exp.update_qubits()
        ##############################
        lab.group_close()

        fig.savefig(str(Path(exp._file_path).parent) + f'/Overview_{self._states}.png')
        fig.show()
