import numpy as np
from sqdtoolz.Experiment import *
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.WaveformGeneric import *
from sqdtoolz.HAL.WaveformSegments import *
from sqdtoolz.Utilities.DataFitting import *
from sqdtoolz.Experiments.Experimental.ExpCalibGE import *
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
import json

class ExpGateBenchmarks(Experiment):   
    def __init__(self, name, expt_config, qubit_gate_obj, **kwargs):
        super().__init__(name, expt_config)

        # assert isinstance(qubit_gate_obj, QubitGatesBase), "qubit_gate_obj must be a QubitGates object (e.g. TransmonGates)"
        self._qubit_gate_obj = qubit_gate_obj

        self._param_avg_gate_error = kwargs.get('param_avg_gate_error', None)   #TODO: Set this
        self._rb_seed = kwargs.get('rb_seed', 88)
        
        #Calculate default load time via T1 of qubit or default to 80e-6
        def_load_time = self._qubit_gate_obj.get_qubit_SPEC()['GE T1'].Value * 6
        if def_load_time == 0:
            def_load_time = 80e-6
        #Override the load-time if one is specified explicitly
        self.load_time = kwargs.get('load_time', def_load_time)
        
        self.readout_time = kwargs.get('readout_time', 2e-6)
        
        self.normalise_reps = kwargs.get('normalise_reps', 10)
        
        self._gate_seqs = [
            ['I'],
            ['X'],
            ['X/2'],
            ['-X/2'],
            ['Y'],
            ['Y/2'],
            ['-Y/2'],
            ['X', 'X'],
            ['Y', 'Y'],
            ['X', 'Y'],
            ['Y', 'X'],
            ['X/2', 'X/2'],
            ['Y/2', 'Y/2'],
            ['X/2', 'Y/2'],
            ['Y/2', 'X/2'],
            ['H'],
            ['H', 'X/2'],
            ['H', 'Y/2']
        ]

        self._rng = np.random.default_rng(seed = self._rb_seed)
        
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."
        
        self._setup_progress_bar(**kwargs)
        self._expt_config.init_instruments()
        
        data_file = FileIOWriter(file_path + 'data.h5')
        varTrial = VariableInternalTransient('TrialNum')

        all_seqs = {}
        for m, cur_seq in enumerate(self._gate_seqs):
            cur_seq = self._gate_seqs[m]
            final_data = self._qubit_gate_obj.run_circuit(cur_seq, self._expt_config, self.load_time, self.readout_time)
            data_file.push_datapkt(final_data, [(varTrial, np.arange(len(self._gate_seqs)))])
            all_seqs[m] = cur_seq
            self._update_progress_bar((m+1)/len(self._gate_seqs))
        with open(file_path + 'Benchmark_Sequences.json', 'w') as outfile:
            json.dump(all_seqs, outfile, indent=4)
        data_file.close()

        self._qubit_gate_obj.calib_normalisation(self._expt_config, self.load_time, self.readout_time, file_path)

        self._file_path = file_path

        return FileIOReader(file_path + 'data.h5')

    def _post_process(self, data):
        arr = data.get_numpy_array()
        probs = self._qubit_gate_obj.normalise_data(arr)

        expPops = []
        for seq in self._gate_seqs:
            rotMats = [self._qubit_gate_obj.get_rotation_from_Pauli_Matrix(x) for x in seq]
            if len(rotMats) > 1:
                rotMats.reverse()
                rotFinal = np.linalg.multi_dot(rotMats)
            else:
                rotFinal = rotMats[0]
            finalPop = np.abs( (rotFinal @ np.array([0, 1]))[0] )**2
            expPops.append(finalPop)

        fig, ax = plt.subplots(1); fig.set_figwidth(15)

        tickLabels = ['$'+','.join(x)+'$' for x in self._gate_seqs]
        ax.bar(tickLabels, probs, alpha=0.5)
        ax.hlines(expPops, np.arange(len(self._gate_seqs))-0.4,np.arange(len(self._gate_seqs))+0.4, 'k')
        # ax.set_xticks(ax.get_xticks())
        ax.set_ylabel('Excited State Probability')
        ax.set_xticklabels(tickLabels, rotation=90)
        ax.grid()

        fig.show()
        fig.savefig(self._file_path + 'Benchmarks.png')

        return data
