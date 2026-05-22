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
from sqdtoolz.Utilities.QubitGates import QubitGatesBase

class ExpZIBenchmarkETH(ExpZIqubit):   
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False

        self._fit_vals = []

        extra_gate_seqs = kwargs.get('extra_gate_seqs', [])

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
        ] + extra_gate_seqs

        kwargs['gate_lists'] = []
        for cur_seq in self._gate_seqs:
            kwargs['gate_lists'].append([cur_seq]*len(qubit_ids))

        super().__init__(name, expt_config, single_qubit_gates_sweep, hal_QPU, qubit_ids, **kwargs)

    def _post_process(self, data):
        for ind_qubit, qubit_dataset in enumerate(self._qubit_datasets):          
            leData = self.retrieve_last_dataset(qubit_dataset)
            arr = leData.get_numpy_array()
            data_x = leData.param_vals[0]

            norm = ExpZIqubit.normalise_qubit_data(self.retrieve_last_dataset(qubit_dataset+'_calib'), self._transition)

            probs = norm.normalise_data(arr)

            expPops = []
            for seq in self._gate_seqs:
                rotMats = [QubitGatesBase.get_rotation_from_Pauli_Matrix(x) for x in seq]
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

            fig.savefig(self._file_path + f'Benchmarks_{qubit_dataset}.png')
            if not self._dont_show_plot:
                fig.show()

