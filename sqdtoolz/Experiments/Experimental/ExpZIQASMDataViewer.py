import os
from pathlib import Path
import shutil
from sqdtoolz.Utilities.FileIO import FileIOReader
import json
import numpy as np
from sqdtoolz.Utilities.FileJSON import SerialiseJSON
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import matplotlib.pyplot as plt

class ExpZIQASMDataViewer:
    def __init__(self, expziqasmdata_folder_path):
        self.data_folder = Path(expziqasmdata_folder_path)
        with open(self.data_folder / 'measurement_mapping.json', 'r') as f:
            meas_mapping = json.load(f)
        self._cregs = meas_mapping['declaredregs']
        self._creg_to_meas_mapping = {(x['creg'],x['cindex']):x['measureid'] for x in meas_mapping['measuremaps']}
        self._creg_to_qubit_mapping = {(x['creg'],x['cindex']):x['qubit'] for x in meas_mapping['measuremaps']}
        with open(self.data_folder / 'measurement_params.json', 'r') as f:
            self._meas_params = json.load(f)
        with open(self.data_folder / 'laboratory_configuration.txt') as json_file:
            lab_config = json.loads(json_file.read(), object_hook=SerialiseJSON.decode_hook)
        #Extract readout correction matrices if and only if it's in DISCRIMINATION mode...
        self._corr_matrices_regs = {}
        if self._meas_params['acq_type'] == 'DISCRIMINATION':
            self._corr_matrices = {}
            for cur_hal in lab_config['HALs']:
                # if Type
                if cur_hal['Type'] == 'ZIQubit':
                    if 'CorrectionMatrix' in cur_hal:
                        self._corr_matrices[cur_hal['Name']] = cur_hal['CorrectionMatrix']
            self._corr_matrices_regs = {}
            for cur_meas_mapping in meas_mapping['measuremaps']:
                if cur_meas_mapping['qubit'] in self._corr_matrices:
                    self._corr_matrices_regs[(cur_meas_mapping['creg'],cur_meas_mapping['cindex'])] = self._corr_matrices[cur_meas_mapping['qubit']]
                else:
                    self._corr_matrices_regs[(cur_meas_mapping['creg'],cur_meas_mapping['cindex'])] = None

    def _get_data(self, meas_id):
        file_path = self.data_folder / f'data/{meas_id}.h5'
        leData = FileIOReader(file_path)
        arr = leData.get_numpy_array()
        if self._meas_params['acq_type'] == 'DISCRIMINATION':
            arr = np.array(arr[...,0], dtype=int)
        if arr.size == 1:
            arr = float(arr)
        return arr

    def get_number_of_shots(self):
        return self._meas_params['NumRepetitions']

    def get_inner_slicing_vars(self):
        match self._meas_params['acq_type']:
            case 'DISCRIMINATION':
                if self._meas_params['avg_type'] == 'SweepBeforeAverage':
                    ret_val = []
                else:
                    ret_val = ['shot']
            case 'INTEGRATION':
                if self._meas_params['avg_type'] == 'SweepBeforeAverage':
                    ret_val = ['iq']
                else:
                    ret_val = ['shot','iq']
            case 'RAW':
                if self._meas_params['avg_type'] == 'SweepBeforeAverage':
                    ret_val = ['samples','iq']
                else:
                    ret_val = ['shot','samples','iq']
        if len(self._meas_params['Sweeps'])>0:
            ret_val = [x[0] for x in self._meas_params['Sweeps']] + ret_val
        return ret_val

    def get_data(self, classical_register_name:str, classical_register_index:int|None=None):
        """
        If classical_register_index is None, it returns all entries of the register.
        """
        assert classical_register_name in self._cregs, f"The classical register {classical_register_name} is not declared in the QASM script."
        if classical_register_index != None:
            assert classical_register_index >= 0 and classical_register_index < self._cregs[classical_register_name], f"Index {classical_register_index} out of range for register '{classical_register_name}' declared of size {self._cregs[classical_register_name]}."
            assert (classical_register_name, classical_register_index) in self._creg_to_meas_mapping, f"No measurement stored in register {classical_register_name}[{classical_register_index}]."
            cur_data = self._get_data(self._creg_to_meas_mapping[(classical_register_name, classical_register_index)])
        else:
            cur_data = [None]*self._cregs[classical_register_name]
            for cur_meas in self._creg_to_meas_mapping:
                if cur_meas[0] != classical_register_name:
                    continue
                cur_data[cur_meas[1]] = self._get_data(self._creg_to_meas_mapping[cur_meas])
        return cur_data

    def get_readout_correction_matrices(self, classical_register_name:str, classical_register_index:int|None=None):
        """
        Returns the matrices that will correct the vector of population counts/probabilities (0,1,(2)) when premultiplied.
        """
        assert self._meas_params['acq_type'] == 'DISCRIMINATION', "Can only get readout correction matrices if using readout DISCRIMINATION mode."
        assert classical_register_name in self._cregs, f"The classical register {classical_register_name} is not declared in the QASM script."
        if classical_register_index != None:
            assert classical_register_index >= 0 and classical_register_index < self._cregs[classical_register_name], f"Index {classical_register_index} out of range for register '{classical_register_name}' declared of size {self._cregs[classical_register_name]}."
            assert (classical_register_name, classical_register_index) in self._creg_to_meas_mapping, f"No measurement stored in register {classical_register_name}[{classical_register_index}]."
            cur_data = self._corr_matrices_regs[(classical_register_name, classical_register_index)]
        else:
            cur_data = [None]*self._cregs[classical_register_name]
            for cur_meas in self._creg_to_meas_mapping:
                if cur_meas[0] != classical_register_name:
                    continue
                cur_data[cur_meas[1]] = self._corr_matrices_regs[cur_meas]
        return cur_data

    def get_data_qubits(self, classical_register_name:str, classical_register_index:int|None=None):
        assert classical_register_name in self._cregs, f"The classical register {classical_register_name} is not declared in the QASM script."
        if classical_register_index != None:
            assert classical_register_index >= 0 and classical_register_index < self._cregs[classical_register_name], f"Index {classical_register_index} out of range for register '{classical_register_name}' declared of size {self._cregs[classical_register_name]}."
            assert (classical_register_name, classical_register_index) in self._creg_to_meas_mapping, f"No measurement stored in register {classical_register_name}[{classical_register_index}]."
            cur_data = self._creg_to_qubit_mapping[(classical_register_name, classical_register_index)]
        else:
            cur_data = [None]*self._cregs[classical_register_name]
            for cur_meas in self._creg_to_meas_mapping:
                if cur_meas[0] != classical_register_name:
                    continue
                cur_data[cur_meas[1]] = self._creg_to_qubit_mapping[cur_meas]
        return cur_data

    def plot_histograms(self, classical_register_name:str, classical_register_index:int|list[int]|None=None, num_qubit_states=2, apply_readout_correction=True, plot_2D_histogram=True):
        if classical_register_index is None:
            cur_data = self.get_data(classical_register_name)
            classical_register_index = np.arange(len(cur_data))
        else:
            if not isinstance(classical_register_index, (list,tuple)):
                classical_register_index = [classical_register_index]
            cur_data = []
            for cur_ind in classical_register_index:
                cur_data.append(self.get_data(classical_register_name, cur_ind))

        #Filter out registers that don't have data...
        final_data = []
        labels = []
        corr_matrices = []
        for m in range(len(cur_data)):
            if cur_data[m] is None:
               continue
            final_data.append(cur_data[m])
            cur_reg_ind = classical_register_index[m]
            labels.append(f"c[{cur_reg_ind}] ({self._creg_to_qubit_mapping[(classical_register_name, cur_reg_ind)]})")
            if hasattr(self, '_corr_matrices_regs'):
                corr_matrices.append(self._corr_matrices_regs[(classical_register_name, cur_reg_ind)])

        if plot_2D_histogram and len(final_data) == 2:
            # Count occurrences of each (a, b) pair
            counts = np.zeros((num_qubit_states, num_qubit_states), dtype=int)
            for x, y in zip(final_data[0], final_data[1]):
                counts[x, y] += 1
            fig, ax = plt.subplots(1)
            lePlot = ax.pcolor(counts, cmap='Blues', edgecolors='black')
            cbar = fig.colorbar(lePlot, ax=ax, label='Counts')
            ax.set_title('Populations')
            ax.set_xticks(np.arange(num_qubit_states) + 0.5, ['0', '1', '2'][:num_qubit_states])
            ax.set_yticks(np.arange(num_qubit_states) + 0.5, ['0', '1', '2'][:num_qubit_states])
            ax.set_xlabel(labels[1])
            ax.set_ylabel(labels[0])
        else:
            leProbs = []
            for m in range(len(final_data)):
                cur_probs = Miscellaneous.get_probability_of_basis_states([final_data[m]], num_qubit_states=num_qubit_states, correction_matrices=[corr_matrices[m]])
                leProbs.append(np.array(cur_probs))
            fig, axs = plt.subplots(nrows=len(leProbs)); fig.set_figheight(1*len(leProbs))
            for m in range(len(leProbs)):
                axs[m].bar(np.arange(num_qubit_states), leProbs[m], color='skyblue')
                axs[m].set_ylabel(labels[m])
                axs[m].set_xticks(np.arange(num_qubit_states))
                axs[m].set_ylim([0,1])
                axs[m].grid()
                if m < len(leProbs)-1:
                    axs[m].set_xticklabels([])
                else:
                    axs[m].set_xlabel("States")
            axs[0].set_title("Probability Distribution")
