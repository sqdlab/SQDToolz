import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZISingleQubitTuneup import ExpZISingleQubitTuneup
from sqdtoolz.Experiments.Experimental.ExpZIResOptimal import ExpZIResOptimal
from sqdtoolz.Experiments.Experimental.ExpZIBlobs import ExpZIBlobs
from sqdtoolz.Experiments.Experimental.ExpZIT1 import ExpZIT1
from sqdtoolz.HAL.ZI import ZIPulses
from sqdtoolz.HAL.ZI.QuantumElements import TunableTransmonCouplerFixed
from sqdtoolz.HAL.SOFTqpu import SOFTqpu
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ExpZIBellStateFidelity import ExpZIBellStateFidelity
from sqdtoolz.Experiments.Experimental.ExpZIFixedCouplerTuneup import ExpZIFixedCouplerTuneup
from sqdtoolz.Experiments.Experimental.ExpZIRandomisedBenchmarking import ExpZIRandomisedBenchmarking
from laboneq_applications.experiments import time_traces
import matplotlib.pyplot as plt
import matplotlib.gridspec
from pathlib import Path
import datetime
import shutil

class ExpZIDailyTuneup:
    def __init__(self, name, expt_config, hal_QPU, qubit_id, **kwargs):
        assert isinstance(qubit_id, str), "Pass a single qubit_id as a string, i.e. 'Q0'."
        self._name = name
        self._expt_config = expt_config
        self._qpu = hal_QPU
        self._qubit_id = qubit_id
        self._qubit = self._qpu.get_qubit_obj(self._qubit_id)

        self._tune_readout = kwargs.pop('tune_readout', True)
        self._individual_plots = kwargs.get('individual_plots', False)
        self._update_live = kwargs.get('update_params_live', True)
        self._enable_ZI_log_messages = kwargs.get('enable_ZI_log_messages', False)
        self._save_config = kwargs.pop('save_config', False)
        self._print_summary = kwargs.pop('print_summary', True)
        # self._config_file_name = kwargs.pop('config_file_name', '')
        self._save_summary_config_from_json = kwargs.pop('save_summary_config_from_json', True)
        self._summary_json_file = kwargs.pop('summary_json_file', f'{datetime.date.today():%Y%m%d}_QPUsummary.json')
        if self._save_config==False:
            self._save_summary_config_from_json=False

        self._skip_2qg = kwargs.pop('skip_2qg', False)
        self._transition = kwargs.get('states', 'gef')
        assert self._transition in ['ge', 'ef', 'gef'], "Provides states as 'ge', 'ef', or 'gef'."
        self._res_trough = kwargs.pop('res_is_trough', True)
        self._update_readout_by_fidelity = kwargs.pop('update_qubits_by_fidelity', 'mean')
        assert self._update_readout_by_fidelity in ['g', 'e', 'f', 'Mean', 'mean', 'G', 'E', 'F'], "Supply update_readout_by_fidelity as 'g', 'e', 'f' or 'Mean'."
        if 'res_freq_range' in kwargs:
            self._res_freq_range = kwargs.pop('res_freq_range')
            assert not 'res_freq_span' in kwargs, "Do not supply 'res_freq_span' if supplying 'res_freq_range'"
            assert not 'res_freq_points' in kwargs, "Do not supply 'res_freq_points' if supplying 'res_freq_range'"
        else:
            freq_span = kwargs.pop('res_freq_span', 10e6)
            freq_points = kwargs.pop('res_freq_points', 101)
            self._res_freq_range = np.linspace(self._qubit.ReadoutFrequency - 2*freq_span/3, self._qubit.ReadoutFrequency + freq_span/3, freq_points)

        self._kwargs = kwargs
    
    def run(self, lab):
        # TODO: parallelise for multiple qubits
        print(f"##############################")   
        print(f"#   TUNEUP {self._qubit_id}\n")

        self._expt_config._hal_ACQ.NumRepetitions = 1024; 
        self._expt_config._hal_ACQ.AveragingOrder = "DEFAULT"; 
        self._expt_config._hal_ACQ.AcquisitionMode = "DEFAULT"; 
        self._expt_config.commit()

        ##############################
        #
        #FINE TUNING X GATES
        #
        exp = ExpZISingleQubitTuneup(f'DailyTuneup_{self._qubit_id}_FinetuneX', self._expt_config, self._qpu, self._qubit_id, **self._kwargs)
        exp.run_fine_tuneup(lab)

        ##############################
        #
        #READOUT RESONATOR
        #
        if self._tune_readout:
            print(f'\nOptimising readout (GEF)...')
            exp = ExpZIResOptimal(f'DailyTuneup_{self._qubit_id}_Readout', self._expt_config, self._qpu, [self._qubit_id], states='gef', frequencies=self._res_freq_range, ZI_plot=self._individual_plots, calc_single_shot_fidelities=True)
            lab.run_single(exp)
            if self._update_live:
                prev = self._qubit.FidelityReadout
                prev_freq = self._qubit.ReadoutFrequency
                exp.update_qubits_by_fidelity(self._update_readout_by_fidelity, state_fidelity=self._transition)
                new = self._qubit.FidelityReadout
                new_freq = self._qubit.ReadoutFrequency
                print(f"\tf_r = {prev_freq*1e-9:.6f} GHz -> {new_freq*1e-9:.6f} GHz")
                print(f"\tF_r = {prev:.6f}% -> {new:.6f}%")
            ##############################
            #
            #OPTIMISE INTEGRATION WEIGHTS
            #
            print(f'\nOptimising integration weights...')
            exp = ExpZIqubit(f'DailyTuneup_{self._qubit_id}_TimeTraces', self._expt_config, time_traces, self._qpu, [self._qubit_id], states=self._transition, update=True, skip_ZI_analysis=False, ZI_plot=self._individual_plots)
            lab.run_single(exp)

            ##############################
            #
            #BLOBS
            #
            if self._update_live:
                print(f'\nGetting readout fidelity...')
                exp = ExpZIBlobs(f'DailyTuneup_{self._qubit_id}_Blobs', self._expt_config, self._qpu, [self._qubit_id], states=self._transition, ZI_plot=self._individual_plots)
                lab.run_single(exp)
                new = self._qubit.FidelityReadout
                print(f"\tF_r = {prev:.6g}% -> {new:.6g}%")

        ##############################
        #
        #T1
        #
        print(f'\nMeasuring T1...')
        prev = self._qubit.T1GE
        exp = ExpZIT1(f'DailyTuneup_{self._qubit_id}_T1', self._expt_config, self._qpu, [self._qubit_id], ZI_plot=self._individual_plots)
        lab.run_single(exp)
        if self._update_live:
            exp.update_qubits()
            new = self._qubit.T1GE
            print(f"\tT1 = {prev*1e6:.6g} us -> {new*1e6:.6g} us")
        
        ##############################
        #
        #2QG FINE TUNING
        #
        coupled_qubit = None
        prev = None
        if not self._skip_2qg:
            for q in [i[0][0] for i in self._qpu._qubits]:
                if q != self._qubit_id:
                    try:
                        c = self._qpu.get_coupler_obj_from_qubits(self._qubit_id, q, TunableTransmonCouplerFixed)
                        coupled_qubit = q
                        prevA = c.Amplitude
                        prevL = c.Length
                        break
                    except AssertionError:
                        continue
            if coupled_qubit is not None:
                print(f'\nTuning two qubit gates ({self._qubit_id}, {coupled_qubit})...')
                exp = ExpZIFixedCouplerTuneup(f'DailyTuneup_{self._qubit_id}{coupled_qubit}_2QG', self._expt_config, self._qpu, [self._qubit_id, coupled_qubit], fit_qubit=self._qubit_id, flux_amp_points=self._kwargs.get('chevron_amp_pts', 17), flux_amp_span=self._kwargs.get('chevron_amp_span', 0.03), update_params_live=self._update_live)
                exp.run(lab)
                newA = c.Amplitude
                newL = c.Length
                if self._update_live:
                    print(f"\tAmp   = {prevA:.6g} -> {newA:.6g}")
                    print(f"\tLength = {prevL*1e9:.6g} ns -> {newL*1e9:.6g} ns")

        ##############################
        #
        #1QG RANDOMISED BENCHMARKING
        #
        if not self._kwargs.get('skip_benchmarking', False):
            print(f'\nSingle qubit randomised benchmarking...')
            prev = self._qubit.Fidelity1QRB
            exp = ExpZIRandomisedBenchmarking(f'DailyTuneup_{self._qubit_id}_RB', self._expt_config, self._qpu, [self._qubit_id], sequence_lengths=self._kwargs.pop('rb_sequence_lengths', [2**2, 2**3, 2**4, 2**5, 2**6, 2**7]), num_trials=self._kwargs.pop('rb_num_trials', 6), update=self._update_live)
            lab.run_single(exp)
            new = self._qubit.Fidelity1QRB
            print(f"\tF_1QRB = {prev:.6g}% -> {new:.6g}%")

        ##############################
        #
        #2QG BELL STATE FIDELITY
        #
            if not self._skip_2qg and coupled_qubit is not None:
                print(f'\nBell state fidelity...')
                prev = c.FidelityBell
                exp = ExpZIBellStateFidelity(f'DailyTuneup_{self._qubit_id}{coupled_qubit}_BellState', self._expt_config, self._qpu, [self._qubit_id, coupled_qubit], update=self._update_live)
                exp.run(lab)
                exp.post_process()
                new = c.FidelityBell
                print(f"\tF_2QBell = {prev:.6g}% -> {new:.6g}%")

        ##############################
        #
        #SAVE CONFIG, PRINT SUMMARY
        #
        # markdown summary
        if self._print_summary:
            print(f" ")
            self._qpu.print_summary_ZIQubits()
        # if the config file already exists, back it up to /config_backups/
        if self._save_config:
            config_datestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
            config_filename = str(config_datestamp) + '_QPU_config.json'
            config_filepath = Path(config_filename)
            if config_filepath.exists():
                Path('/Config_backups').mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_filepath, Path('/Config_backups') / config_filename)
            self._qpu.save_config(lab, file_name=config_filename)
            print(f'\nSaved new config to {config_filename}.')
        # summary json for website update
        if self._save_summary_config_from_json:
            SOFTqpu.create_summary_config_from_json(json_file_path=config_filename, summary_output_json_file_path=self._summary_json_file)
            print(f'Saved summary .json to {self._summary_json_file}.')
        print(f"##############################\n\n")