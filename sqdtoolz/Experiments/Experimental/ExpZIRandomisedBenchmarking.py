import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.WaveformGeneric import *
from sqdtoolz.HAL.WaveformSegments import *
from sqdtoolz.Utilities.DataFitting import *
from sqdtoolz.Experiments.Experimental.ExpCalibGE import *
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
import json
from sqdtoolz.Experiments.Experimental.ZI import single_qubit_gates_sweep
from sqdtoolz.Experiments.Experimental.ZI import sinlge_qubit_gates_sweep_chunking
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
from sqdtoolz.Variable import VariableInternalTransient

class ExpZIBenchmarkRandomised(ExpZIqubit):   
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False

        kwargs['coordinate_system'] = kwargs.get('coordinate_system', 'RH')
        assert kwargs['coordinate_system'] in ['LH', 'RH'], "The 'coordinate_system' must be either LH or RH for left/right handed."

        self._fit_vals = []

        #extra_gate_seqs = kwargs.get('extra_gate_seqs', [])
        self._rb_seed = kwargs.get('rb_seed', 88)
        self._rng = np.random.default_rng(seed = self._rb_seed)

        self._sequence_lengths = kwargs.pop('sequence_lengths', [3,4,5,6,7,8,9,10,11,12])
        self._num_trials = kwargs.pop('num_trials',5)


        self._gate_set = ['X', 'X/2', '-X/2', 'Y', 'Y/2', '-Y/2']

    
        self._all_seqs = {}
        kwargs['gate_lists'] = []
        print("Generating gate sequences...")
        for seq_len in self._sequence_lengths:
            self._all_seqs[int(seq_len)] = {}
            for trial in range(self._num_trials):
                cur_seq = self._generate_sequence(seq_len)
                kwargs['gate_lists'].append([cur_seq]*len(qubit_ids))
                self._all_seqs[int(seq_len)][int(trial)] = [cur_seq]*len(qubit_ids)
        self._all_seqs_list = kwargs['gate_lists']
        print("Done.")
        super().__init__(name, expt_config, sinlge_qubit_gates_sweep_chunking, hal_QPU, qubit_ids, **kwargs)

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
                final_gate = QubitGatesBase.convert_Pauli_rotation_to_natural( *QubitGatesBase.compute_rotation_Pauli_Matrices(XReInv))
            except:
                continue
            if final_gate == 'Z' or final_gate == 'Z/2' or final_gate == '-Z/2':
                final_gate = 'I'
            gate_seq.append(final_gate)

            return gate_seq
        
    def _post_process(self, data):
        for ind_qubit, qubit_dataset in enumerate(self._qubit_datasets):          
            leData = self.retrieve_last_dataset(qubit_dataset)
            arr = leData.get_numpy_array()
            seqs = leData.param_vals[0]
            seq_lens = np.array(self._sequence_lengths)
            norm = ExpZIqubit.normalise_qubit_data(self.retrieve_last_dataset(qubit_dataset+'_calib'), self._transition)
            probs = norm.normalise_data(arr)
            mean_vals = []
            std_vals = []

            fig, axs = plt.subplots(ncols=2); fig.set_figwidth(12); axs[0].grid(); axs[1].grid()

            for m in range(len(self._sequence_lengths)):
                trial_probs = []
                xvals = []
                for k in range(self._num_trials):
                    cur_seq_index = m*self._num_trials + k
                    if probs[cur_seq_index] < 0.8: 
                        continue
                    trial_probs.append(probs[cur_seq_index])
                    xvals.append(self._sequence_lengths[m])
                cur_x = xvals
                cur_y = trial_probs
                axs[0].plot(cur_x, cur_y, 'kx', alpha = 0.3)
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
            axs[1].set_title(f"Error per Gate: {(error_per_gate*100):.6g}%")
            axs[1].legend(['Raw Data', 'Fitted Error line'])

            fig.show()
            fig.savefig(self._file_path + 'Summary.png')

        return data