import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIResFluxSweep import ExpZIResFluxSweep
from sqdtoolz.Experiments.Experimental.ExpZIRes import ExpZIRes
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ExpZIRabi import ExpZIRabi
from laboneq_applications.experiments import (qubit_spectroscopy,
    ramsey, 
    lifetime_measurement
)

class ExpZISingleQubitTuneup:
    def __init__(self, name, expt_config, hal_QPU, qubit_id, **kwargs):
        self._name = name
        self._expt_config = expt_config
        self._qpu = hal_QPU
        self._qubit_id = qubit_id
        
        self._qubit = self._qpu.get_qubit_obj(self._qubit_id)

        self._qubit_spec_LO_power = kwargs.pop('qubit_spec_LO_power', -5)
        self._qubit_time_domain_LO_power = kwargs.pop('qubit_time_domain_LO_power', 10)

        self._res_trough = kwargs.pop('res_is_trough', True)
        self._flux_range = kwargs.pop('flux_range',None)
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
        self._ramsey_fast_detuning = kwargs.pop('ramsey_fast_detuning', 1e6)
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
        lab.group_open(self._name)
        #
        if not self._flux_range is None:
            exp = ExpZIResFluxSweep(f'res_flux_sweep_{self._qubit_id}', self._expt_config, self._qpu, self._qubit_id,  frequencies=self._res_freq_range, flux_range=self._flux_range, is_trough=self._res_trough)
            lab.run_single(exp)
            exp.update_qubit()
        #
        exp = ExpZIRes(f'res_spec_{self._qubit_id}', self._expt_config, self._qpu, self._qubit_id, frequencies=self._res_freq_range, is_trough=self._res_trough, fit_type="Full")
        lab.run_single(exp)
        #
        #TODO: Second -30dBm smaller spanned qubit spec.
        self._qubit.DrivePower = self._qubit_spec_LO_power
        exp = ExpZIqubit(f'qubit_spec_{self._qubit_id}', self._expt_config, qubit_spectroscopy, self._qpu, [self._qubit_id], frequencies=[self._qubit_freq_range], ZI_plot=True, update=True)
        lab.run_single(exp)
        #
        self._qubit.DrivePower = self._qubit_time_domain_LO_power
        self._qubit.DriveGEAmplitudeX = 1.0
        self._qubit.DriveGEAmplitudeXon2 = 0.5
        exp = ExpZIRabi(f'rabi_pre_cal_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], amplitudes=[self._rabi_ampls], update=True, ZI_plot=True)
        lab.run_single(exp)
        exp = ExpZIRabi(f'rabi_{self._qubit_id}', self._expt_config, self._qpu, [self._qubit_id], amplitudes=[self._rabi_ampls], update=True, ZI_plot=True)
        lab.run_single(exp)
        #
        exp = ExpZIqubit(f'ramsey_fast_{self._qubit_id}', self._expt_config, ramsey, self._qpu, [self._qubit_id], delays=[self._ramsey_fast_times], detunings=[self._ramsey_fast_detuning], update=True, ZI_plot=True)
        lab.run_single(exp)
        exp = ExpZIqubit(f'ramsey_slow_{self._qubit_id}', self._expt_config, ramsey, self._qpu, [self._qubit_id], delays=[self._ramsey_slow_times], detunings=[self._ramsey_slow_detuning], update=True, ZI_plot=True)
        lab.run_single(exp)
        #
        exp = ExpZIqubit(f'T1_{self._qubit_id}', self._expt_config, lifetime_measurement, self._qpu, [self._qubit_id], delays=[self._t1_times], update=True, ZI_plot=True)
        lab.run_single(exp)
        #
        lab.group_close()


