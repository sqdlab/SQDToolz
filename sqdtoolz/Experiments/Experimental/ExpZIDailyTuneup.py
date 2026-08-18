import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZISingleQubitTuneup import ExpZISingleQubitTuneup
from sqdtoolz.Experiments.Experimental.ExpZIResOptimal import ExpZIResOptimal
from sqdtoolz.Experiments.Experimental.ExpZIBlobs import ExpZIBlobs
from sqdtoolz.Experiments.Experimental.ExpZIT1 import ExpZIT1
from sqdtoolz.HAL.ZI import ZIPulses
from sqdtoolz.HAL.SOFTqpu import SOFTqpu
import matplotlib.pyplot as plt
import matplotlib.gridspec
from pathlib import Path
from datetime import date

class ExpZIDailyTuneup:
    def __init__(self, name, expt_config, hal_QPU, qubit_id, **kwargs):
        assert isinstance(qubit_id, str), "Pass a single qubit_id as a string, i.e. 'Q0'."
        self._name = name
        self._expt_config = expt_config
        self._qpu = hal_QPU
        self._qubit_id = qubit_id
        self._qubit = self._qpu.get_qubit_obj(self._qubit_id)
        
        self._individual_plots = kwargs.get('individual_plots', False)
        self._update_live = kwargs.get('update_params_live', True)
        self._enable_ZI_log_messages = kwargs.get('enable_ZI_log_messages', False)
        self._save_config = kwargs.pop('save_config', False)
        self._print_summary = kwargs.pop('print_summary', False)
        self._config_file_name = kwargs.pop('config_file_name', '')
        self._save_summary_config_from_json = kwargs.pop('save_summary_config_from_json', True)
        self._summary_json_file = kwargs.pop('summary_json_file', f'{date.today():%Y%m%d}_QPUsummary.json')

        self._transition = kwargs.get('states', 'gef')
        assert self._transition in ['ge', 'ef', 'gef'], "Provides states as 'ge', 'ef', or 'gef'."
        self._res_trough = kwargs.pop('res_is_trough', True)
        self._update_readout_by_fidelity = kwargs.pop('update_qubits_by_fidelity', 'mean')
        assert self._update_readout_by_fidelity in ['g', 'e', 'f', 'Mean'], "Supply update_qubits_by_fidelity as 'g', 'e', 'f' or 'Mean'."
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

        ##############################
        #
        #FINE TUNING X GATES
        #
        exp = ExpZISingleQubitTuneup(f'DailyTuneup_{self._qubit_id}_FinetuneX', self._expt_config, self._qpu, self._qubit_id, **self._kwargs)
        exp.run_fine_tuneup(lab)

        ##############################
        #
        #TODO: 2QG FINE TUNING
        #

        ##############################
        #
        #READOUT RESONATOR
        #
        exp = ExpZIResOptimal(f'DailyTuneup_{self._qubit_id}_Readout', self._expt_config, self._qpu, [self._qubit_id], states=self._transition, frequencies=self._res_freq_range, ZI_plot=self._individual_plots, calc_single_shot_fidelities=True)
        lab.run_single(exp)
        if self._update_live:
            exp.update_qubits_by_fidelity(self._update_readout_by_fidelity)

        ##############################
        #
        #BLOBS
        #
        exp = ExpZIBlobs(f'DailyTuneup_{self._qubit_id}_Blobs', self._expt_config, self._qpu, [self._qubit_id], states=self._transition, ZI_plot=self._individual_plots)
        lab.run_single(exp)

        ##############################
        #
        #T1
        #
        exp = ExpZIT1(f'DailyTuneup_{self._qubit_id}_T1', self._expt_config, self._qpu, [self._qubit_id], ZI_plot=self._individual_plots)
        lab.run_single(exp)
        if self._update_live:
            exp.update_qubits()
        
        ##############################
        #
        #SAVE CONFIG, PRINT SUMMARY
        #
        if self._save_config:
            self._qpu.save_config(lab, file_name=self._config_file_name)
        if self._print_summary:
            self._qpu.print_summary_ZIQubits()
        if self._save_summary_config_from_json:
            json_file_path = self._config_file_name + 'QPU_config.json'
            SOFTqpu.create_summary_config_from_json(json_file_path=json_file_path, summary_output_json_file_path=self._summary_json_file)