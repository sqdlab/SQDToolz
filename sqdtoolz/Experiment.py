from typing import List
import numpy as np
import time
import json
from sqdtoolz.Variable import VariablePropertyOneManyTransient

import matplotlib.pyplot as plt

from sqdtoolz.Utilities.FileIO import*

class Experiment:
    def __init__(self, name, expt_config):
        '''
        '''
        self._name = name
        self._expt_config = expt_config
        self.last_rec_params = None
        self._cur_filewriters = {}
        self._file_path = None

    @property
    def Name(self):
        return self._name

    def _init_data_file(self, filename):
        if self._data_file_index >= 0:
            data_file_name = f'{filename}{self._data_file_index}'
        else:
            data_file_name = filename
        data_file = FileIOWriter(self._file_path + data_file_name + '.h5', store_timestamps=self._store_timestamps)
        self._cur_filewriters[data_file_name] = data_file
        return data_file, data_file_name + '.h5'

    def retrieve_last_aux_dataset(self, dset_name):
        assert self._file_path != None, f"Must run experiment first before any datasets, let alone {dset_name}, are generated."
        fname = self._file_path + dset_name + '.h5'
        assert os.path.exists(fname), f"The dataset {dset_name} was not generated in the last experiment run and thus, does not exist."
        return FileIOReader(fname)

    def _init_extra_rec_params(self):
        #Should return a list of strings
        return []

    def _init_aux_datafiles(self):
        pass

    def _mid_process(self):
        pass

    def _post_process(self, data):
        return
        #An example...
        file_path = data.folder_path + '/data_proc.h5'
        data_file = FileIOWriter(file_path)
        data_pkt = {
                    'parameters' : ['frequency', 'power'],
                    'data' : {
                        'amplitude' : np.zeros((5,4)),
                        'phase' : np.zeros((5,4))
                    },
                    'parameter_values' : {'frequency' : np.arange(5)}
                }
        data_file.push_datapkt(data_pkt)
        data_file.close()

    def _run(self, file_path, sweep_vars=[], **kwargs):
        self.last_rec_params = None
        self._file_path = file_path
        delay = kwargs.get('delay', 0.0)
        ping_iteration = kwargs.get('ping_iteration')
        kill_signal = kwargs.get('kill_signal')
        ping_iteration(reset=True)
        disable_progress_bar = kwargs.get('disable_progress_bar', False)
        callback_iteration = kwargs.get('callback_iteration', None)

        self._data_file_index = kwargs.get('data_file_index', -1)
        self._store_timestamps = kwargs.get('store_timestamps', True)

        data_file, data_file_name = self._init_data_file('data')
        
        rec_params = kwargs.get('rec_params')
        rec_params_extra = self._init_extra_rec_params()
        if len(rec_params) + len(rec_params_extra) > 0:
            rec_data_file, rec_param_file_name = self._init_data_file('rec_params')

        self._init_aux_datafiles()

        if not kwargs.get('skip_init_instruments', False):
            self._expt_config.init_instruments()

        waveform_updates = kwargs.get('update_waveforms', None)
        if waveform_updates != None:
            self._expt_config.update_waveforms(waveform_updates)

        assert isinstance(sweep_vars, list), "Sweeping variables must be given as a LIST of TUPLEs: [(VAR1, range1), (VAR2, range2), ...]"
        self._cur_names = []
        self._sweep_grids = None
        if len(sweep_vars) == 0:
            if not kill_signal():
                self._expt_config.prepare_instruments()
                if not kill_signal():
                    data = self._expt_config.get_data()
                    data_file.push_datapkt(data, sweep_vars)
                    if len(rec_params) > 0:
                        rec_data_file.push_datapkt(self._prepare_rec_params(rec_params, rec_params_extra), sweep_vars)
                    self._cur_ind_coord = 0
                    self._sweep_shape = [1]
                    self._mid_process()
                    time.sleep(delay)
            #################################
        else:
            sweep_vars2 = []
            sweepEx = {}
            for ind_var, cur_var in enumerate(sweep_vars):
                if len(cur_var) == 2:
                    assert isinstance(cur_var[1], np.ndarray), "The second argument in each sweeping-variable tuple must be a Numpy Array."
                    assert cur_var[1].size > 0, f"The sweeping array for sweeping-variable {ind_var} is empty. If using arange, check the bounds!"
                    sweep_vars2 += [(cur_var[0], cur_var[1])]
                else:
                    assert isinstance(cur_var[0], str) and isinstance(cur_var[1], list) and isinstance(cur_var[2], np.ndarray), "One-many sweeping arguments must be given as the tuple: (name, list of VARs, ND-array)"
                    assert len(cur_var[2].shape) == 2, f"The array for sweeping parameter {cur_var[0]} must be 2D."
                    assert cur_var[2].shape[1] == len(cur_var[1]), f"The array for one-many sweeping parameter {cur_var[0]} must have {len(cur_var[1])} columns."
                    var_amalg = VariablePropertyOneManyTransient(cur_var[0], cur_var[1], cur_var[2])
                    sweep_vars2 += [(var_amalg, np.arange(cur_var[2].shape[0]))]
                    sweepEx[cur_var[0]] = {'vars' : cur_var[1], 'var_vals' : cur_var[2]}
            
            self._cur_names = [v[0].Name for v in sweep_vars2]
            assert len(self._cur_names) == len(set(self._cur_names)), "All assigned sweeping variable names must be unique."

            if not kill_signal():
                sweep_arrays = [x[1] for x in sweep_vars2]
                self._sweep_shape = [x[1].size for x in sweep_vars2]
                self._sweep_grids = np.meshgrid(*sweep_arrays)
                self._sweep_grids = np.array(self._sweep_grids)
                axes = np.arange(len(self._sweep_grids.shape))
                try:
                    axes[2] = 1
                    axes[1] = 2
                except IndexError:
                    pass
                self._sweep_grids = np.transpose(self._sweep_grids, axes=axes).reshape(len(sweep_arrays),-1).T
                
                #sweep_vars2 is given as a list of tuples formatted as (parameter, sweep-values in an numpy-array)
                for ind_coord, cur_coord in enumerate(self._sweep_grids):
                    self._cur_ind_coord = ind_coord
                    #Set the values
                    for ind, cur_val in enumerate(cur_coord):
                        sweep_vars2[ind][0].set_raw(cur_val)

                    if kill_signal():
                        break
                    
                    #Now prepare the instrument
                    # self._expt_config.check_conformance() #TODO: Write this
                    self._expt_config.prepare_instruments()
                    time.sleep(delay)

                    if kill_signal():
                        break

                    data = self._expt_config.get_data()
                    data_file.push_datapkt(data, sweep_vars2, sweepEx)
                    if len(rec_params) > 0:
                        rec_data_file.push_datapkt(self._prepare_rec_params(rec_params, rec_params_extra), sweep_vars2, sweepEx)
                    self._sweep_vars = sweep_vars2
                    self._mid_process()
                    if not disable_progress_bar:
                        ping_iteration((ind_coord+1)/self._sweep_grids.shape[0])
                    if callback_iteration != None:
                        callback_iteration()

        #Close all data files
        for cur_file in self._cur_filewriters:
            self._cur_filewriters[cur_file].close()
        self._cur_filewriters.clear()
        
        if len(rec_params) > 0:
            self.last_rec_params = FileIOReader(file_path + rec_param_file_name)
        self._expt_config.makesafe_instruments()
        self._sweep_grids = None
        self._cur_names = []

        return FileIOReader(file_path + data_file_name)

    def _prepare_rec_params(self, rec_params, rec_params_extra):
        ret_data = {
                'parameters' : [],
                'data' : { f'{cur_rec_param[2]}' : np.array([getattr(cur_rec_param[0], cur_rec_param[1])]) for cur_rec_param in rec_params }
            }
        for cur_param in rec_params_extra:
            ret_data['data'][cur_param] = np.array([np.nan])
        return ret_data


    def save_config(self, save_dir, name_time_diag, name_expt_params, sweep_queue = [], file_index = 0):
        #Save a PNG of the Timing Plot
        lePlot = self._expt_config.plot()
        lePlot.savefig(save_dir + name_time_diag + '.png')
        plt.close(lePlot)

        dict_expt_params = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__,
            'Config' : self._expt_config.Name,
            'Sweeps' : sweep_queue,
            'FileIndex' : file_index
        }
        with open(save_dir + name_expt_params, 'w') as outfile:
            json.dump(dict_expt_params, outfile, indent=4)

    def _has_completed_iteration(self, var_name):
        assert var_name in self._cur_names, f"Variable {var_name} not found in the list of sweeping variables in this experiment."
        cur_ind = self._cur_names.index(var_name)
        inds = np.unravel_index(self._cur_ind_coord, self._sweep_shape)
        for m in range(cur_ind+1, len(self._sweep_shape)):
            if self._sweep_shape[m] != inds[m] + 1:
                return False
        return True

    def _query_current_array_iteration(self, datafilename, var_name):
        #Consider: VAR1, VAR2, VAR3, VAR4 with the current iteration being 2, 4, 5, 7
        #For VAR2, this function returns: data[2][4][:][:] but removing the superfluous initial indices
        assert var_name in self._cur_names, f"Variable {var_name} is not in the list of sweeping variables."
        var_ind = self._cur_names.index(var_name)
        inds = np.unravel_index(self._cur_ind_coord, self._sweep_shape)
        inds = list(inds)
        if var_ind + 1 < len(inds):
            for m in range(var_ind+1,len(inds)):
                inds[m] = np.arange(self._sweep_shape[m])
        ret_data = self._cur_filewriters[datafilename].query_data(inds)
        if var_ind == len(ret_data.shape)-1:
            return np.ndarray.flatten(ret_data)
        return ret_data.reshape(ret_data.shape[var_ind+1:])

    def _push_data_mid_iteration(self, datafilename, last_sweep_var, data_pkt):
        assert last_sweep_var in self._cur_names, f"Variable {last_sweep_var} is not in the list of sweeping variables."
        var_ind = self._cur_names.index(last_sweep_var)
        self._cur_filewriters[datafilename].push_datapkt(data_pkt, self._sweep_vars[:var_ind+1])

    def _retrieve_current_sweep_values(self):
        if not isinstance(self._sweep_grids, np.ndarray):
            return {}
        return {x : self._sweep_grids[self._cur_ind_coord][ind] for ind, x in enumerate(self._cur_names)}
