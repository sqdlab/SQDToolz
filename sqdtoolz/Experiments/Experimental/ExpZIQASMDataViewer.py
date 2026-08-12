import os
from pathlib import Path
import shutil
from sqdtoolz.Utilities.FileIO import FileIOReader
import json

class ExpZIQASMDataViewer:
    def __init__(self, expziqasm_data_folder_path):
        self._data_folder = Path(expziqasm_data_folder_path)
        with open(self._data_folder / 'measurement_mapping.json', 'r') as f:
            meas_mapping = json.load(f)
        self._cregs = meas_mapping['declaredregs']
        self._creg_to_meas_mapping = {(x['creg'],x['cindex']):x['measureid'] for x in meas_mapping['measuremaps']}
        with open(self._data_folder / 'measurement_params.json', 'r') as f:
            self._meas_params = json.load(f)

    def _get_data(self, meas_id):
        file_path = self._data_folder / f'data/{meas_id}.h5'
        leData = FileIOReader(file_path)
        arr = leData.get_numpy_array()
        if self._meas_params['acq_type'] == 'DISCRIMINATION':
            arr = arr[...,0]
        if arr.size == 1:
            arr = float(arr)
        return arr

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
