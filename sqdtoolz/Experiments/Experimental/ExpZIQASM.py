import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.WaveformGeneric import *
from sqdtoolz.HAL.WaveformSegments import *
from sqdtoolz.Utilities.DataFitting import *
from sqdtoolz.Experiments.Experimental.ExpCalibGE import *
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
import json
from sqdtoolz.Experiments.Experimental.ZI import oqasm_scheduled_qubits
from sqdtoolz.Utilities.QubitGates import QubitGatesBase
from sqdtoolz.Utilities.OpenQASM.ParserOpenQASM import ParserOpenQASM
from sqdtoolz.Utilities.OpenQASM.ScheduleParametersSoftQPUZI import ScheduleParametersSoftQPUZI
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import os
from pathlib import Path
import shutil
from sqdtoolz.Utilities.FileIO import FileIOReader

class ExpZIQASM(ExpZIqubit):   
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, qasm_file_path, **kwargs):
        """
        NOTE: The physical qubit identifiers $0,$1,$2... in OpenPulse are mapped to the qubit_ids!
        """
        self._qubit_datasets = qubit_ids

        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False

        kwargs['coordinate_system'] = kwargs.get('coordinate_system', 'RH')
        assert kwargs['coordinate_system'] in ['LH', 'RH'], "The 'coordinate_system' must be either LH or RH for left/right handed."

        self._poqasm = ParserOpenQASM(qasm_file_path, kwargs.pop('source_dirs', []), measure_label='QMEAS')
        self._final_qreg_phys_mapping = self._poqasm._qreg_phys_mapping #Copy over the default qreg to physical qubit mapping

        self._qregs = self._poqasm.get_qubit_registers()
        num_qasm_qubits = len(self._qregs)
        assert num_qasm_qubits <= len(qubit_ids), f"The QASM script needs {num_qasm_qubits} while only {len(qubit_ids)} qubits have been specified."
        
        super().__init__(name, expt_config, oqasm_scheduled_qubits, hal_QPU, qubit_ids, **kwargs)

    def get_qubit_regs(self):
        return self._poqasm.get_qubit_registers()

    def set_qubit_reg_to_ZI_mappings(self, mapping:dict):
        """
        Given as key-value pairs where key is a key from get_qubit_regs and value is the name (only string-based name allowed here) of the ZI-Qubit object...
        """
        num_qasm_qubits = len(self._qregs)
        assert num_qasm_qubits == len(mapping), f"The QASM script has {num_qasm_qubits} qubits that need to be mapped onto the hardware, the provided mapping specifies {len(mapping)} qubits."
        
        leQubitNames = [self._hal_QPU.get_qubit_obj(x).Name for x in self._qubit_ids] #Still allowing integer/string-based indexing on the qubit_ids...
        leQregs = self._poqasm.get_qubit_registers()

        self._final_qreg_phys_mapping = {}
        for m,cur_qubit_reg in enumerate(leQregs):
            assert cur_qubit_reg in mapping, f"The qubit register {cur_qubit_reg} not present in the supplied mapping."
            assert mapping[cur_qubit_reg] in leQubitNames, f"Qubit by name {mapping[cur_qubit_reg]} does not exist in the qubits supplied in qubit_ids when initialising ExpZIQASM..."
            cur_phys_index = leQubitNames.index( mapping[cur_qubit_reg] )
            self._final_qreg_phys_mapping[cur_qubit_reg] = cur_phys_index
        self._poqasm.set_qreg_physical_mapping(self._final_qreg_phys_mapping)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        self._poqasm.perform_parsing()

        leQubitNames = [self._hal_QPU.get_qubit_obj(x).Name for x in self._qubit_ids] #Still allowing integer/string-based indexing on the qubit_ids...

        mapping_physQid_QPUQubitindex = {}
        for cur_qreg in self._final_qreg_phys_mapping:
            mapping_physQid_QPUQubitindex[self._final_qreg_phys_mapping[cur_qreg]] = leQubitNames[self._final_qreg_phys_mapping[cur_qreg]]
        qasm_qubit_params = ScheduleParametersSoftQPUZI(self._hal_QPU,mapping_physQid_QPUQubitindex)
        #
        self._leSchedule = self._poqasm.create_schedule(qasm_qubit_params, flatten_blocks=True)

        # leTable = self._poqasm.tabulate_schedule(self._leSchedule, qasm_qubit_params)
        # for m in range(len(self._leScheduleBlocks['commands'])):
        self._poqasm.plot_schedule(self._leSchedule, qasm_qubit_params, file_path + 'compiled_qasm_schedule.html')

        self._poqasm.check_ZI_compatibility(self._leSchedule, qasm_qubit_params, **kwargs)

        #Store the script and the register/measurement mappings
        self._poqasm.save_main_script(file_path + 'main.qasm')
        json_data = {
            'declaredregs': self._poqasm._cregs,
            'measuremaps': [{'creg':x[0], 'cindex':x[1], 'measureid':self._leSchedule['meas_store_ids'][x]} for x in self._leSchedule['meas_store_ids']]
            }
        with open(file_path + 'measurement_mapping.json', 'w') as f:
            json.dump(json_data, f)

        #Because the output heavily depends on how the shaping of the measurement parameters, force the ACQ parameters to not be DEFAULT here...
        if 'override_ACQ_params' in kwargs:
            if 'AcquisitionMode' in kwargs['override_ACQ_params']:
                if not (kwargs['override_ACQ_params']['AcquisitionMode'] in ['DISCRIMINATION', 'INTEGRATION', 'RAW']):
                    kwargs['override_ACQ_params']['AcquisitionMode'] = 'DISCRIMINATION'
            else:
                kwargs['override_ACQ_params']['AcquisitionMode'] = 'DISCRIMINATION'
            #####
            if 'AveragingOrder' in kwargs['override_ACQ_params']:
                if kwargs['override_ACQ_params']['AveragingOrder'] == 'DEFAULT':
                    kwargs['override_ACQ_params']['AveragingOrder'] = 'SweepBeforeAverage'
            else:
                kwargs['override_ACQ_params']['AveragingOrder'] = 'SweepBeforeAverage'
        else:
            kwargs['override_ACQ_params'] = {'AcquisitionMode':'DISCRIMINATION', 'AveragingOrder':'SweepBeforeAverage'}

        self._args['openqasm_schedule'] = self._leSchedule
        super()._run(file_path, sweep_vars, **kwargs)

        acq_type = self._expt_config._hal_ACQ.AcquisitionMode
        avg_type = self._expt_config._hal_ACQ.AveragingOrder
        with open(file_path + 'measurement_params.json', 'w') as f:
            json.dump({'acq_type':acq_type, 'avg_type':avg_type, 'NumRepetitions':self._expt_config._hal_ACQ.NumRepetitions}, f)
        self.qasm_output = {}
        for cur_meas_output in self._leSchedule['meas_store_ids']:
            cur_fileioread = self.retrieve_last_aux_dataset(self._leSchedule['meas_store_ids'][cur_meas_output])
            arr = cur_fileioread.get_numpy_array()
            if acq_type == 'DISCRIMINATION':
                self.qasm_output[cur_meas_output] = arr[...,0].tolist()
            else: #For RAW or INTEGRATION, all values matter...
                self.qasm_output[cur_meas_output] = arr.tolist()
        pass

    def _post_process(self, data):
        os.remove(self._file_path+'data.h5')
        dest_folder = Path(self._file_path+"data")
        dest_folder.mkdir(exist_ok=True)
        # Find all .h5 files in the current directory and move them
        for file_path in Path(self._file_path).glob("*.h5"):
            # Skip if it is a directory matching the pattern
            if file_path.is_file():
                dest_path = dest_folder / file_path.name
                shutil.move(str(file_path), str(dest_path))



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
                    return []
                else:
                    return ['shot']
            case 'INTEGRATION':
                if self._meas_params['avg_type'] == 'SweepBeforeAverage':
                    return ['iq']
                else:
                    return ['shot','iq']
            case 'RAW':
                if self._meas_params['avg_type'] == 'SweepBeforeAverage':
                    return ['samples','iq']
                else:
                    return ['shot','samples','iq']

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
