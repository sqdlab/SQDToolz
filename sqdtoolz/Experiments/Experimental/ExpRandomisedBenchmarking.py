import numpy as np
from sqdtoolz.Experiment import *
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.WaveformGeneric import *
from sqdtoolz.HAL.WaveformSegments import *
from sqdtoolz.Utilities.DataFitting import *
from sqdtoolz.Experiments.Experimental.ExpCalibGE import *
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
import json

class ExpRandomisedBenchmarking(Experiment):
    '''
    A randomised benchmarking experiment.
    
    Inputs
    ---------
    name (str): Name of experiment directory for saving purposes
    expt_config (ExperimentConfiguration): custom experiment config
    qubit_gate_obj (QubitGatesBase): Qubit gates generation object
    sequence_lengths (np.array[int]): An array of benchmarking sequence lengths
    num_trials (int): The number of unique randomly generated circuits for each sequence length
    
    Outputs
    ---------
    Returns data, displays benchmarking plot, saves error per gate into SPEC_qubit
    '''
    
    def __init__(self, name, expt_config, qubit_gate_obj, sequence_lengths, num_trials, iq_indices=[0,1], **kwargs):
        super().__init__(name, expt_config)

        # assert isinstance(qubit_gate_obj, QubitGatesBase), "qubit_gate_obj must be a QubitGates object (e.g. TransmonGates)"
        self._qubit_gate_obj = qubit_gate_obj

        self._sequence_lengths = sequence_lengths
        self._num_trials = num_trials
        self._iq_indices= iq_indices
        self._param_avg_gate_error = kwargs.get('param_avg_gate_error', None)
        self._rb_seed = kwargs.get('rb_seed', 88)
        
        #Calculate default load time via T1 of qubit or default to 80e-6
        def_load_time = self._qubit_gate_obj.get_qubit_SPEC()['GE T1'].Value * 6
        if def_load_time == 0:
            def_load_time = 80e-6
        #Override the load-time if one is specified explicitly
        self.load_time = kwargs.get('load_time', def_load_time)
        
        self.readout_time = kwargs.get('readout_time', 2e-6)
        
        self.normalise_reps = kwargs.get('normalise_reps', 10)
        
        self._gate_set = ['X', 'X/2', '-X/2', 'Y', 'Y/2', '-Y/2']

        self._rng = np.random.default_rng(seed = self._rb_seed)
        
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."
        
        self._expt_config.init_instruments()
        
        data_file = FileIOWriter(file_path + 'data.h5')
        varSeq = VariableInternalTransient('SeqLen')
        varTrial = VariableInternalTransient('TrialNum')

        all_seqs = {}
        for seq_len in self._sequence_lengths:
            all_seqs[int(seq_len)] = {}
            for trial in range(self._num_trials):
                cur_seq = self._generate_sequence(seq_len)
                final_data = self._qubit_gate_obj.run_circuit(cur_seq, self._expt_config, self.load_time, self.readout_time)
                data_file.push_datapkt(final_data, [(varSeq, self._sequence_lengths), (varTrial, np.arange(self._num_trials))])
                all_seqs[int(seq_len)][int(trial)] = cur_seq
        with open(file_path + 'RB_Sequences.json', 'w') as outfile:
            json.dump(all_seqs, outfile, indent=4)
        data_file.close()

        data_fileC = FileIOWriter(file_path + 'dataCalib.h5')
        varInd = VariableInternalTransient('State')
        final_data = self._qubit_gate_obj.run_circuit(['I'], self._expt_config, self.load_time, self.readout_time)
        data_fileC.push_datapkt(final_data, [(varInd, np.arange(2))])
        final_data = self._qubit_gate_obj.run_circuit(['X'], self._expt_config, self.load_time, self.readout_time)
        data_fileC.push_datapkt(final_data, [(varInd, np.arange(2))])
        data_fileC.close()
        self._file_path = file_path

        self.file_io_read_calib = FileIOReader(file_path + 'dataCalib.h5')

        return FileIOReader(file_path + 'data.h5')

    def _post_process(self, data):
        arr = data.get_numpy_array()
        norm_obj = DataIQNormalise.calibrateFromFileIOReader(self.file_io_read_calib)

        seq_lens = data.param_vals[0]

        fig, axs = plt.subplots(ncols=2); fig.set_figwidth(12); axs[0].grid(); axs[1].grid()

        mean_vals = []
        std_vals = []
        for m in range(seq_lens.size):
            cur_x = [seq_lens[m]]*self._num_trials
            cur_y = norm_obj.normalise_data(arr[m])
            axs[0].plot(cur_x, cur_y, 'kx')
            mean_vals.append(np.mean(cur_y))
            std_vals.append(np.std(cur_y))
        mean_vals = np.array(mean_vals)
        std_vals = np.array(std_vals)

        axs[0].plot(seq_lens, mean_vals)
        axs[0].fill_between(seq_lens, mean_vals-std_vals, mean_vals+std_vals, alpha=0.5)
        axs[0].set_xlabel('Sequence Length')
        axs[0].set_ylabel('Excited State Probability')
        axs[0].set_title(f'Number of Trials per Sequence Length: {self._num_trials}')

        zProj = mean_vals - 0.5
        slope, intercept = np.polyfit(seq_lens, np.log(zProj), deg=1)
        error_per_gate = np.exp(slope)
        axs[1].plot(seq_lens, np.log(zProj), 'kx')
        axs[1].plot(seq_lens, seq_lens*slope+intercept, 'r-')
        axs[1].set_xlabel('Sequence Length')
        axs[1].set_ylabel(r'$\ell n(Z_{proj})$')
        axs[1].set_title(f"Error per Gate: {(error_per_gate*100):.4g}%")
        axs[1].legend(['Raw Data', 'Fitted Error line'])

        fig.show()
        return data

    def _generate_sequence(self, seq_len):
        #Keep trying to find random sequences that enable the final gate to be within the gate-set - e.g. X/2, Y will give a 45° rotation...
        while(True):
            rand_int_array = self._rng.integers(low=0, high=len(self._gate_set)-1, size=seq_len-1)
            gate_seq = [self._gate_set[i] for i in rand_int_array]
            gate_mats = [QubitGatesBase.get_rotation_from_Pauli_Matrix(g) for g in gate_seq]
            gate_mats.reverse()
            effective_gate = np.linalg.multi_dot(gate_mats)
            #Final state should be excited-state...
            XReInv = QubitGatesBase.get_rotation_from_Pauli_Matrix('X') @ np.linalg.inv(effective_gate)

            try:
                final_gate = QubitGatesBase.convert_Pauli_rotation_to_natural( *QubitGatesBase.compute_rotation_Pauli_Matrices(XReInv) )
            except:
                continue
            if final_gate == 'Z' or final_gate == 'Z/2' or final_gate == '-Z/2':
                final_gate = 'I'
            gate_seq.append(final_gate)

            return gate_seq
