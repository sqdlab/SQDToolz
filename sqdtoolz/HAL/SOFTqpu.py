from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.ExperimentSpecification import ExperimentSpecification
from sqdtoolz.HAL.ZI.ZIbase import ZIbase
from sqdtoolz.Variable import VariableInternalTransient
from sqdtoolz.Utilities.FileIO import FileIODatalogger, FileIOReader
from sqdtoolz.Utilities.FileJSON import SQDJSONEncoder
import time
import json
import os
import scipy.signal
import numpy as np
import laboneq.dsl.quantum
import pandas as pd

class SOFTqpu(HALbase, ZIbase):
    def __init__(self, hal_name, lab, **kwargs):
        #NOTE: the driver is presumed to be a single-pole many-throw switch (i.e. only one circuit route at a time).
        HALbase.__init__(self, hal_name)
        lab._register_HAL(self)
        self._lab=lab
        config_dict = kwargs.get('config_dict', {})        
        self._qubits = config_dict.get('Qubits', [])
        self._qubit_couplings = config_dict.get('QubitCouplings', [])

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict["Name"], lab, config_dict=config_dict)

    @property
    def NumQubits(self):
        return len(self._qubits)

    def add_qubit(self, hal_obj:HALbase|ExperimentSpecification):
        self._qubits.append(self._lab._resolve_sqdobj_tree(hal_obj))
    
    def add_qubit_coupling(self, qubit1: str|int, qubit2: str|int, hal_obj:HALbase):
        qubit1 = self._resolve_qubit_index(qubit1)
        qubit2 = self._resolve_qubit_index(qubit2)
        self._qubit_couplings.append((qubit1, qubit2, self._lab._resolve_sqdobj_tree(hal_obj)))

    def get_qubit_obj(self, qubit_id: str|int):
        return self._lab._get_resolved_obj(self._qubits[self._resolve_qubit_index(qubit_id)])
 
    def get_qubit_coupling_objs(self, qubit1: str|int, qubit2: str|int):
        qubit1 = self._resolve_qubit_index(qubit1)
        qubit2 = self._resolve_qubit_index(qubit2)
        ret_cpls = []
        for cur_cpl in self._qubit_couplings:
            if qubit1 == cur_cpl[0] and qubit2 == cur_cpl[1] or qubit1 == cur_cpl[1] and qubit2 == cur_cpl[0]:
                ret_cpls.append(self._lab._get_resolved_obj(cur_cpl[2]))
        return ret_cpls

    def get_ZI_parameters(self):
        leQubits = []
        leQelems = []
        leQops = []
        for m in range(len(self._qubits)):
            cur_qubit = self._lab._get_resolved_obj(self._qubits[m])
            assert isinstance(cur_qubit, ZIbase), f"The qubit on index {m} is not a ZI-compatible qubit HAL."
            qubit, qop = cur_qubit.get_ZI_parameters()
            leQubits.append(qubit)
            already_exists = False
            for cur_op in leQops:
                if type(cur_op) == type(qop):
                    already_exists = True
                    break
            if not already_exists:
                leQops.append(qop)
        leQcouplers = []
        for m in range(len(self._qubit_couplings)):
            cur_hal_cpl = self._lab._get_resolved_obj( self._qubit_couplings[m][2] )
            assert isinstance(cur_hal_cpl, ZIbase), f"The coupling on defined on index {m} is not a ZI-compatible qubit HAL."
            cpl, qop = cur_hal_cpl.get_ZI_parameters()
            leQcouplers.append(cpl)
            already_exists = False
            for cur_op in leQops:
                if cur_op.__name__ == qop.__name__: #These are classes - hence using __name__ as opposed to type...
                    already_exists = True
                    break
            if not already_exists:
                leQops.append(qop)
        leQPU = laboneq.dsl.quantum.QPU(leQubits + leQcouplers, quantum_operations=leQops)
        for m in range(len(self._qubit_couplings)):
            qubit1 = self._lab._get_resolved_obj(self._qubits[self._qubit_couplings[m][0]]).Name
            qubit2 = self._lab._get_resolved_obj(self._qubits[self._qubit_couplings[m][1]]).Name
            if isinstance(self._qubit_couplings[m][2], str):
                leQPU.topology.add_edge(self._qubit_couplings[m][2], qubit1, qubit2)
            else:
                cur_cpl = self._lab._get_resolved_obj(self._qubit_couplings[m][2])
                assert isinstance(cur_cpl, ZIbase), f"The qubit coupling {cur_cpl.Name} between qubits {qubit1} and {qubit2} is not a ZI-compatible qubit HAL."
                cpl, qop = cur_cpl.get_ZI_parameters()
                leQPU.topology.add_edge(cur_cpl.Name, qubit1, qubit2, quantum_element=cpl)
        return leQPU, leQubits, leQcouplers

    def save_config(self, lab, file_name='', store_local=True):
        #Not choosing to filter intrinsic parameters yet. Ultimately, many parameters can be ignored by the routines
        #like SingleQubitTuneup anyway. So it's up to those routines to decide what's mandatory and what's to be
        #overwritten... This will shift stuff like FluxDC, but again, recalibration will mandate those be checked
        #anyway... Most of the time cold_reload_last_configuration should be used - this is more for the case where
        #it's a fresh experiment and it's convenient to just slice out the qubit-only parameters...
        #
        #Anyway, the idea is to reuse the cold_reload_labconfig function to instantiate/initialise the parameters...
        #Thus, the code is written to be compatible/friendly to that while adding some extra parameters to aid in the
        #user API here...
        param_dict = {
                    'ActiveInstruments' : [],
                    'HALs' : [],
                    'PROCs': [],
                    'WFMTs': [],
                    'SPECs': [],
                    'Qubits': {},
                    'QubitCouplings': {}
                    }
        cur_index = 0
        for m in range(len(self._qubits)):
            cur_qubit = self._lab._get_resolved_obj(self._qubits[m])
            param_dict['HALs'].append(cur_qubit._get_current_config())
            param_dict['Qubits'][cur_qubit.Name] = cur_index
            cur_index += 1
        for m in range(len(self._qubit_couplings)):
            cur_hal_cpl = self._lab._get_resolved_obj( self._qubit_couplings[m][2] )
            param_dict['HALs'].append(cur_hal_cpl._get_current_config())
            param_dict['QubitCouplings'][cur_hal_cpl.Name] = cur_index
            cur_index += 1
        param_dict['HALs'].append(self._get_current_config())
        file_path = '' if store_local else lab._save_dir
        file_path += 'QPU_config.json' if file_name == '' else file_name
        with open(file_path, 'w') as outfile:
            json.dump(param_dict, outfile, indent=4, cls=SQDJSONEncoder)

    @staticmethod
    def load_config(lab, id='', file_path=''):
        """
        Function to initialise (instantiate if necessary) all qubits/couplers. If id is empty, all qubits/couplers are loaded/instantiated.
        """
        if file_path == '':
            assert os.path.exists('QPU_config.json'), "Cannot find configuration 'QPU_config.json' in the default path. Specify actual file name"
            file_path = 'QPU_config.json'
        else:
            assert os.path.exists(file_path), f"Cannot find configuration file '{file_path}'."
        loaded_dict = lab._load_json_file(file_path)
        if id != '':
            if id in loaded_dict['Qubits']:
                hal_index = loaded_dict['Qubits'][id]
            elif id in loaded_dict['QubitCouplings']:
                hal_index = loaded_dict['QubitCouplings'][id]
            else:
                assert False, f"There is no qubit or coupler named {id}."
            loaded_dict['HALs'] = [loaded_dict['HALs'][hal_index]]
        lab.cold_reload_labconfig(loaded_dict)

    def print_summary_ZIQubits(self):
        """
        Prints a Markdown Table of the ZI Qubits
        """
        leQubits = [self._lab._get_resolved_obj(x) for x in self._qubits]
        #Stick to the format here to add columns!
        data = {
                'Qubit': [x.Name for x in leQubits],
                r'$f_r$ (GHz)':                 [f'{x.ReadoutFrequency/1e9:.4g}' for x in leQubits],
                r'$f_q$ (GHz)':                 [f'{x.DriveGE/1e9:.4g}' for x in leQubits],
                r'$T_1$ (μs)':                  [f'{x.T1GE*1e6:.4g}' for x in leQubits],
                r'$T_2^*$ (μs)':                [f'{x.T2GE_star*1e6:.4g}' for x in leQubits],
                r'$T_2^{\text{Hahn}}$ (μs)':    [f'{x.T2GE*1e6:.4g}' for x in leQubits],
                r'$\chi$ (MHz)':                [f'{x.ChiGE/1e6:.4g}' for x in leQubits]
               }
        df = pd.DataFrame(data)
        print(df.to_markdown(index=False))

    def _resolve_qubit_index(self, qubit_id):
        if isinstance(qubit_id, int):
            assert qubit_id < len(self._qubits) and qubit_id >= 0, f"Qubit index {qubit_id} is out of range given the number of qubits."
            return qubit_id
        for m in range(len(self._qubits)):
            cur_qubit = self._lab._get_resolved_obj(self._qubits[m])
            if cur_qubit.Name==qubit_id:
                return m
        assert False, f"Qubit \"{qubit_id}\" does not exist."

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__,
            'Qubits': self._qubits,
            'QubitCouplings': self._qubit_couplings
            }
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a SoQPU with a configuration that is of type ' + dict_config['Type']
        self._qubits = dict_config.get('Qubits', [])
        self._qubit_couplings = dict_config.get('QubitCouplings', [])
