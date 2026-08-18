import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIResFluxSweep import ExpZIResFluxSweep
from sqdtoolz.Experiments.Experimental.ExpZIRes import ExpZIRes
from sqdtoolz.Experiments.Experimental.ExpZIQubitSpec import ExpZIQubitSpec
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ExpZIRabi import ExpZIRabi
from sqdtoolz.Experiments.Experimental.ExpZIRamsey import ExpZIRamsey
from sqdtoolz.Experiments.Experimental.ExpZIT1 import ExpZIT1
from sqdtoolz.Experiments.Experimental.ExpZICalibX import ExpZICalibX
from sqdtoolz.Experiments.Experimental.ExpZIDragScaling import ExpZIDragScaling
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from laboneq.dsl.experiment import pulse_library
from sqdtoolz.HAL.ZI import ZIPulses
import matplotlib.pyplot as plt
import matplotlib.gridspec
from pathlib import Path

class ExpZISingleQubitTuneup:
    def __init__(self, name, expt_config, hal_QPU, qubit_id, **kwargs):
        self._name = name
        self._expt_config = expt_config
        self._qpu = hal_QPU
        self._qubit_id = qubit_id
        
        self._qubit = self._qpu.get_qubit_obj(self._qubit_id)

        self._qubit_spec_LO_power = kwargs.pop('qubit_spec_LO_power', -20)
        self._qubit_time_domain_LO_power = kwargs.pop('qubit_time_domain_LO_power', 10)

        self._res_trough = kwargs.pop('res_is_trough', True)
        self._flux_range = kwargs.pop('flux_range', None)
        
        self._individual_plots = kwargs.pop('individual_plots', False)
        self._update_live = kwargs.pop('update_params_live', True)
        self._enable_ZI_log_messages = kwargs.pop('enable_ZI_log_messages', False)
        #
        if 'res_freq_range' in kwargs:
            self._res_freq_range = kwargs.pop('res_freq_range')
            assert not 'res_freq_span' in kwargs, "Do not supply 'res_freq_span' if supplying 'res_freq_range'"
            assert not 'res_freq_points' in kwargs, "Do not supply 'res_freq_points' if supplying 'res_freq_range'"
        else:
            freq_span = kwargs.pop('res_freq_span', 10e6)
            freq_points = kwargs.pop('res_freq_points', 1001)
            self._res_freq_range = np.linspace(self._qubit.ReadoutFrequency - freq_span/2, self._qubit.ReadoutFrequency + freq_span/2, freq_points)
        #
        if 'qubit_freq_range' in kwargs:
            self._qubit_freq_range = kwargs.pop('qubit_freq_range')
            assert not 'qubit_freq_span' in kwargs, "Do not supply 'qubit_freq_span' if supplying 'qubit_freq_range'"
            assert not 'qubit_freq_points' in kwargs, "Do not supply 'qubit_freq_points' if supplying 'qubit_freq_range'"
        else:
            freq_span = kwargs.pop('qubit_freq_span', 100e6)
            freq_points = kwargs.pop('qubit_freq_points', 1001)
            self._qubit_freq_range = np.linspace(self._qubit.DriveGE - freq_span/2, self._qubit.DriveGE + freq_span/2, freq_points)
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
        self._assume_detuned_above = kwargs.pop('ramsey_assume_detuned_above', True)
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
        
        # fine tuneup
        self._ramsey_fine_detuning = kwargs.pop('ramsey_fine_detuning', 0.125e6)
        if 'ramsey_fine_times' in kwargs:
            self._ramsey_fine_times = kwargs.pop('ramsey_fine_times')
            assert not 'ramsey_fine_max' in kwargs, "Do not supply 'ramsey_fine_max' if supplying 'ramsey_fine_times'"
            assert not 'ramsey_fine_points' in kwargs, "Do not supply 'ramsey_fine_points' if supplying 'ramsey_fine_times'"
        else:
            max_fine_time = kwargs.pop('ramsey_fine_max', 60e-6)
            max_fine_points = kwargs.pop('ramsey_fine_points', 120)
            self._ramsey_fine_times = np.linspace(0, max_fine_time, max_fine_points)
        #
        self._q_scalings = kwargs.pop('drag_q_scalings', np.linspace(0.00, 0.05, 51))
        self._num_gates_calibX_short = kwargs.pop('num_gates_calibX_short', 200)
        self._num_gates_calibX_long = kwargs.pop('num_gates_calibX_long', 1000)
        self._reverse_parity_calibX = kwargs.pop('reverse_parity_calibX', False)
        self._only_every_n_short = kwargs.pop('only_every_n_short', 3)
        self._only_every_n_long = kwargs.pop('only_every_n_long', 11)

        self._kwargs = kwargs

    def run(self, lab):
        fig = plt.figure(layout="constrained"); fig.set_figwidth(12); fig.set_figheight(12)
        gs = matplotlib.gridspec.GridSpec(5, 2, figure=fig)
        fig.suptitle(f"Tuneup {self._qubit_id}", fontsize=16, fontweight='bold')
        #
        lab.group_open(self._name)
        #
        #FLUX SWEEP
        #
        if not self._flux_range is None:
            exp = ExpZIResFluxSweep(f'res_flux_sweep_{self._qubit_id}', self._expt_config, self._qpu, self._qubit_id,  frequencies=self._res_freq_range, flux_range=self._flux_range, is_trough=self._res_trough, dont_show_plot=not self._individual_plots)
            lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
            exp.update_qubit()
            #
            leData = exp.retrieve_last_aux_dataset(self._qubit_id)
            fitted_data = np.load(exp._file_path + 'fitted_data.npy', allow_pickle=True).item()
            ax = fig.add_subplot(gs[0, 0])
            arr = leData.get_numpy_array()
            flux_vals,freq_vals = leData.param_vals
            ampl = np.sqrt(arr[:,:,0]**2 + arr[:,:,1]**2)
            ExpZIResFluxSweep.plot_fitted_results(ax, self._qubit_id, freq_vals, flux_vals, ampl, fitted_data)
        ##############################
        #
        #RESONATOR SPECTROSCOPY
        #
        if not self._flux_range is None:
            ax = fig.add_subplot(gs[1, 0])
        else:
            ax = fig.add_subplot(gs[0:2, 0])
        exp = ExpZIRes(f'res_spec_{self._qubit_id}', self._expt_config, self._qpu, self._qubit_id, frequencies=self._res_freq_range, is_trough=self._res_trough, fit_type="Default", dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        assert self._qubit.ReadoutFrequency < np.max(self._res_freq_range) and self._qubit.ReadoutFrequency > np.min(self._res_freq_range), "The fitted readout frequency was outside the scanned frequency range."
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        fitted_data = np.load(exp._file_path + 'fitted_data.npy', allow_pickle=True).item()
        arr = leData.get_numpy_array(); ax.grid()
        freq_vals = leData.param_vals[0]
        ampl = np.sqrt(arr[:,0]**2 + arr[:,1]**2)
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(freq_vals)
        ax.plot(freq_vals/norm_fac, ampl**2, 'kx')
        ax.plot(freq_vals/norm_fac, fitted_data['squared_amplitude'], 'r')
        ax.set_title(f'Resonator Frequency: {Miscellaneous.get_units(self._qubit.ReadoutFrequency,5)}Hz')
        ax.set_xlabel(f'Resonator Frequency ({norm_prefix}Hz)')
        ax.set_ylabel('Squared Amplitude')
        ##############################
        #
        #QUBIT SPECTROSCOPY
        #
        #TODO: Second -30dBm smaller spanned qubit spec.
        self._qubit.DrivePower = self._qubit_spec_LO_power
        exp = ExpZIQubitSpec(f'qubit_spec_{self._qubit_id}', self._expt_config, self._qpu, self._qubit_id,
                             is_trough = not self._res_trough,  #TODO: Think about whether this is true in general...
                             frequencies=[self._qubit_freq_range], ZI_plot=self._individual_plots, update=self._update_live, dont_plot=True, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[0:2, 1]); ax.grid()
        fitted_data = np.load(exp._file_path + 'fitted_data.npy', allow_pickle=True).item()
        arr = leData.get_numpy_array()
        freq_vals = leData.param_vals[0]
        ampl = np.sqrt(arr[:,0]**2 + arr[:,1]**2)
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(freq_vals)
        ax.plot(freq_vals/norm_fac, ampl**2, 'kx')
        ax.plot(freq_vals/norm_fac, fitted_data['squared_amplitude'], 'r')
        ax.set_title(f'Qubit Frequency: {Miscellaneous.get_units(lab.HAL(self._qubit_id).DriveGE,5)}Hz')
        ax.set_xlabel(f'Frequency ({norm_prefix}Hz)')
        ax.set_ylabel('Squared Amplitude')
        ##############################
        #
        #RABI
        #
        self._qubit.DrivePower = self._qubit_time_domain_LO_power
        self._qubit.DriveGEAmplitudeX = 1.0
        self._qubit.DriveGEAmplitudeXon2 = 0.5  
        exp = ExpZIRabi(f'rabi_pre_cal_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], amplitudes=[self._rabi_ampls], update=self._update_live, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots, use_cal_traces=False)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        exp = ExpZIRabi(f'rabi_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], amplitudes=[self._rabi_ampls], update=self._update_live, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[2, :])
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
        exp = ExpZIRamsey(f'ramsey_fast_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], delays=[self._ramsey_fast_times], detunings=[self._ramsey_fast_detuning], ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[3, 0])
        fitted_data = np.load(exp._file_path + f"fitted_data_{self._qubit_id}.npy", allow_pickle=True).item()
        arr = leData.get_numpy_array()
        data_x = leData.param_vals[0]
        ExpZIRamsey.plot_fitted_results(ax, data_x, fitted_data['amplitude_raw'], self._qubit_id, fitted_data, True)
        sigFigs = 4
        ax.set_title(f"Ramsey Δ={Miscellaneous.get_units(self._ramsey_fast_detuning,4)}Hz, f={Miscellaneous.get_units(fitted_data['frequency'],4)}Hz")
        exp.update_qubits() #TODO: Add error-checking here to slam brakes if necessary
        #
        #Slow
        exp = ExpZIRamsey(f'ramsey_slow_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], delays=[self._ramsey_slow_times], detunings=[self._ramsey_slow_detuning], ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[3, 1])
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
        exp = ExpZIT1(f'T1_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], delays=[self._t1_times], ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[4, :])
        fitted_data = np.load(exp._file_path + f'fitted_data_{self._qubit_id}.npy', allow_pickle=True).item()
        arr = leData.get_numpy_array()
        data_x = leData.param_vals[0]
        ExpZIT1.plot_fitted_results(ax, data_x, fitted_data['amplitude_raw'], fitted_data, True)
        ax.set_title(f"T1: {Miscellaneous.get_units(fitted_data['T1'],4)}s")
        exp.update_qubits()
        ##############################
        lab.group_close()

        fig.savefig(str(Path(exp._file_path).parent) + '/Overview.png')
        fig.show()

    def run_fine_tuneup(self, lab):
        fig = plt.figure(layout="constrained"); fig.set_figwidth(12); fig.set_figheight(12)
        gs = matplotlib.gridspec.GridSpec(4, 3, figure=fig)
        fig.suptitle(f"Fine tuneup {self._qubit_id}", fontsize=16, fontweight='bold')
        
        lab.group_open(self._name)
        ##############################
        #
        #FINE AND SLOW RAMSEY
        #
        print("Re-tuning Ramsey...")
        exp = ExpZIRamsey(f'ramsey_fine_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], delays=[self._ramsey_fine_times], detunings=[self._ramsey_fine_detuning], ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, disable_ZI_logging=not self._enable_ZI_log_messages)
        #
        leData = exp.retrieve_last_aux_dataset(self._qubit_id)
        ax = fig.add_subplot(gs[0, 0:3])
        fitted_data = np.load(exp._file_path + f"fitted_data_{self._qubit_id}.npy", allow_pickle=True).item()
        arr = leData.get_numpy_array()
        data_x = leData.param_vals[0]
        ExpZIRamsey.plot_fitted_results(ax, data_x, fitted_data['amplitude_raw'], self._qubit_id, fitted_data, True)
        sigFigs = 4
        ax.set_title(f"Ramsey Δ={Miscellaneous.get_units(self._ramsey_slow_detuning,4)}Hz, f={Miscellaneous.get_units(fitted_data['frequency'],4)}Hz, T2*={Miscellaneous.get_units(fitted_data['T2*'],4)}s")
        exp.update_qubits(assume_detuned_above=self._assume_detuned_above) if self._update_live else 0
        ##############################
        #
        #DRAG OPTIMISATION
        #
        print("Calibrating Drag pulses...")
        ax_p = fig.add_subplot(gs[1, 2])
        if self._qubit.DriveGEPulse['function']=='drag':
            p_prev = pulse_library.drag(uid="prev_pulse", beta=self._qubit.DriveGEPulse['beta'], sigma=self._qubit.DriveGEPulse['sigma'], length=self._qubit.DriveGETime)
            ZIPulses.plot_pulse(p_prev, ax=ax_p, label='Previous pulse', color='tab:blue', show_plot=False)
        else:
            self._qubit.DriveGEPulse['function'] = 'drag'
            prev_pulse = None
        exp = ExpZIDragScaling(f'drag_scaling_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], q_scalings=[self._q_scalings], update=self._update_live, ZI_plot=self._individual_plots, dont_show_plot=not self._individual_plots)
        lab.run_single(exp)
        ax = fig.add_subplot(gs[1, 0:2])
        ExpZIDragScaling.plot_fitted_results(ax, exp._data['beta'], exp._data)
        # get new DRAG pulse
        new_pulse = self._qubit.DriveGEPulse
        p_new = pulse_library.drag(uid="new_pulse", beta=new_pulse['beta'], sigma=new_pulse['sigma'], length=self._qubit.DriveGETime)
        ZIPulses.plot_pulse(p_new, ax=ax_p, label='New pulse', color='tab:orange', show_plot=False)
        ax_p.set_title('Pulse viewer')
        ##############################
        # 
        #X CALIB
        #
        #short
        print("Calibrating X Gates...")
        exp = ExpZICalibX(f'CalibX_short_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], calib_denominator=1, only_every_n=self._only_every_n_short, num_gates=self._num_gates_calibX_short, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, skip_timing_diagrams=True)
        prev_angle = exp._prev_angle
        exp.update_qubits(reverse_parity=self._reverse_parity_calibX) if self._update_live else 0
        if self._qubit.DriveGEAmplitudeX > 1:
            self._qubit.DriveGEAmplitudeX = 1
        ax1 = fig.add_subplot(gs[2, 0])
        ExpZICalibX.plot_fitted_results(ax1, exp._fit_data[0]['data'], exp._fit_data[0]['qubit_name'])
        #long
        exp = ExpZICalibX(f'CalibX_long_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], calib_denominator=1, only_every_n=self._only_every_n_long, num_gates=self._num_gates_calibX_long, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, skip_timing_diagrams=True)
        cur_angle = exp._prev_angle
        if abs(180-cur_angle) > abs(180-prev_angle):
            exp.update_qubits(reverse_parity=not self._reverse_parity_calibX) if self._update_live else 0
        else:
            exp.update_qubits(reverse_parity=self._reverse_parity_calibX) if self._update_live else 0
        if self._qubit.DriveGEAmplitudeX > 1:
            self._qubit.DriveGEAmplitudeX = 1

        exp = ExpZICalibX(f'CalibX_long_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], calib_denominator=1, only_every_n=self._only_every_n_long, num_gates=self._num_gates_calibX_long, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, skip_timing_diagrams=True)
        if self._kwargs.pop('assert_gate_calibration', True):
            assert abs(180-cur_angle) < 0.1, "Gate Calibration Failed, Try manually for now"
        #TODO: If we reach this error should code in some edge case automation
        ax2 = fig.add_subplot(gs[2, 1:3], sharey=ax1)
        ExpZICalibX.plot_fitted_results(ax2, exp._fit_data[0]['data'], exp._fit_data[0]['qubit_name'])
        ##############################
        #
        #X/2 CALIB
        #
        #short
        print("Calibrating Xon2 Gates...")
        exp = ExpZICalibX(f'CalibXon2_short_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], calib_denominator=2, only_every_n=self._only_every_n_short, num_gates=self._num_gates_calibX_short, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, skip_timing_diagrams=True)
        prev_angle = exp._prev_angle
        exp.update_qubits(reverse_parity=self._reverse_parity_calibX) if self._update_live else 0
        if self._qubit.DriveGEAmplitudeXon2 > 1:
            self._qubit.DriveGEAmplitudeXon2 = 1
        ax1 = fig.add_subplot(gs[3, 0])
        ExpZICalibX.plot_fitted_results(ax1, exp._fit_data[0]['data'], exp._fit_data[0]['qubit_name'])
        #long
        exp = ExpZICalibX(f'CalibXon2_long_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], calib_denominator=2, only_every_n=self._only_every_n_long, num_gates=self._num_gates_calibX_long, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, skip_timing_diagrams=True)
        cur_angle = exp._prev_angle
        if abs(90-cur_angle) > abs(90-prev_angle):
            exp.update_qubits(reverse_parity=not self._reverse_parity_calibX) if self._update_live else 0
        else:
            exp.update_qubits(reverse_parity=self._reverse_parity_calibX) if self._update_live else 0
        if self._qubit.DriveGEAmplitudeXon2 > 1:
            self._qubit.DriveGEAmplitudeXon2 = 1
            exp.update_qubits(reverse_parity=self._reverse_parity_calibX)
        exp = ExpZICalibX(f'CalibXon2_long_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], calib_denominator=2, only_every_n=self._only_every_n_long, num_gates=self._num_gates_calibX_long, dont_show_plot=not self._individual_plots)
        lab.run_single(exp, skip_timing_diagrams=True)
        cur_angle = exp._prev_angle
        if self._kwargs.pop('assert_gate_calibration', True):
            assert abs(90-cur_angle) < 0.1, "Gate Calibration Failed, Try manually for now"
        #TODO: If we reach this error should code in some edge case automation
        ax2 = fig.add_subplot(gs[3, 1:3], sharey=ax1)
        ExpZICalibX.plot_fitted_results(ax2, exp._fit_data[0]['data'], exp._fit_data[0]['qubit_name'])

        lab.group_close()

        fig.savefig(str(Path(exp._file_path).parent) + '/FinetuneOverview.png')
        fig.show()
