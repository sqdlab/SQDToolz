from typing import List
import numpy as np
import time
import json
from sqdtoolz.Variable import VariablePropertyOneManyTransient
from sqdtoolz.ExperimentSweeps import ExperimentSweepBase

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

    @property
    def ConfigName(self):
        return self._expt_config.Name

    def _init_data_file(self, filename, fileio_options = {}):
        if self._data_file_index >= 0:
            data_file_name = f'{filename}{self._data_file_index}'
        else:
            data_file_name = filename
        if data_file_name in self._cur_filewriters:
            return
        data_file = FileIOWriter(self._file_path + data_file_name + '.h5', store_timestamps=self._store_timestamps, **fileio_options)
        self._cur_filewriters[data_file_name] = data_file
        return data_file, data_file_name + '.h5'

    def retrieve_last_aux_dataset(self, dset_name):
        assert self._file_path != None, f"Must run experiment first before any datasets, let alone {dset_name}, are generated."
        fname = self._file_path + dset_name + '.h5'
        assert os.path.exists(fname), f"The dataset {dset_name} was not generated in the last experiment run and thus, does not exist."
        return FileIOReader(fname)

    def _setup_progress_bar(self, **kwargs):
        self._ping_iteration = kwargs.get('ping_iteration')
        self._ping_iteration(reset=True)
        self._disable_progress_bar = kwargs.get('disable_progress_bar', False)

    def _update_progress_bar(self, pct_complete):
        if not self._disable_progress_bar:
            self._ping_iteration(pct_complete)

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
        kill_signal = kwargs.get('kill_signal')
        self._abort_gracefully = kwargs.get('kill_signal_send')     #Used in mid_process to abort...
        self._setup_progress_bar(**kwargs)

        self._data_file_index = kwargs.get('data_file_index', -1)
        self._store_timestamps = kwargs.get('store_timestamps', True)

        init_data_file_options = {}
        rev_ind = kwargs.get('reverse_index', -1)
        rev_suffix = kwargs.get('reverse_variable_suffix', '_reverse')
        assert not (len(sweep_vars) == 0 and rev_ind >= 0), "Cannot reverse indices when no sweeping variables are given."  #Although the one below covers this, it's nicer to have a more specific error message...
        assert rev_ind < len(sweep_vars), "Index for reversing variable does not fall within the list of given sweeping variables."
        if rev_ind >= 0:
            init_data_file_options['add_reverse_channels'] = True
            init_data_file_options['reverse_channel_suffix'] = rev_suffix
        if 'aux_sweep' in kwargs:
            assert rev_ind < 0, "Cannot use reverse_index if using aux_sweep."
            aux_sweep = kwargs.pop('aux_sweep')
            assert isinstance(aux_sweep, (list, tuple)), "The aux_sweep parameter must be specified as a 3-tuple: (name, index, array)"
            assert len(aux_sweep) == 3, "The aux_sweep parameter must be specified as a 3-tuple: (name, index, array)"
            assert isinstance(aux_sweep[0], str), "The first element in aux_sweep must be a string denoting the name of the dataset."
            assert isinstance(aux_sweep[1], int), "The second element in aux_sweep must be the index of the list of sweeping parameters to augment."
            assert isinstance(aux_sweep[2], np.ndarray), "The third element in aux_sweep must be the a numpy array."
            assert len(aux_sweep[2].shape) == 1, "The numpy array for aux_sweep must be a 1D array."
            data_file_aux, data_file_name_aux = self._init_data_file('data_' + aux_sweep[0], init_data_file_options)
            #
            aux_sweep = (aux_sweep[0], aux_sweep[1], aux_sweep[2], data_file_aux, data_file_name_aux)
        else:
            aux_sweep = []            
        data_file, data_file_name = self._init_data_file('data', init_data_file_options)
        
        rec_params = kwargs.get('rec_params')
        rec_params_extra = self._init_extra_rec_params()
        if len(rec_params) + len(rec_params_extra) > 0:
            rec_data_file, rec_param_file_name = self._init_data_file('rec_params', init_data_file_options)

        self._init_aux_datafiles()

        if not kwargs.get('skip_init_instruments', False):
            self._expt_config.init_instruments(data_file_path=file_path, data_file_index=self._data_file_index)

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
                    cur_raw_data = self._expt_config.get_data()
                    self._data = cur_raw_data.pop('data')
                    for x in cur_raw_data:
                        self._init_data_file(x)
                        self._cur_filewriters[x].push_datapkt(cur_raw_data[x], sweep_vars)
                    data_file.push_datapkt(self._data, sweep_vars)
                    if len(rec_params) > 0:
                        rec_data_file.push_datapkt(self._prepare_rec_params(rec_params, rec_params_extra), sweep_vars)
                    self._cur_ind_coord = 0
                    self._sweep_shape = [1]
                    self._mid_process()
                    self._data = None
                    time.sleep(delay)
            #################################
        else:
            sweep_vars2 = []
            sweepEx = {}
            assert rev_ind == -1 or rev_ind >= 0, "The parameter reverse_index must be supplied as a non-negative indexing integer."
            for ind_var, cur_var in enumerate(sweep_vars):
                assert isinstance(cur_var, tuple) or isinstance(cur_var, list), "Sweeping variables must be given as a LIST of TUPLEs: [(VAR1, range1), (VAR2, range2), ...]"
                if len(cur_var) == 2:
                    assert isinstance(cur_var[1], np.ndarray), "The second argument in each sweeping-variable tuple must be a Numpy Array."
                    assert cur_var[1].size > 0, f"The sweeping array for sweeping-variable {ind_var} is empty. If using arange, check the bounds!"
                    sweep_vars2 += [(cur_var[0], cur_var[1])]
                else:
                    assert isinstance(cur_var[0], str) and isinstance(cur_var[1], list) and isinstance(cur_var[2], np.ndarray), "One-many sweeping arguments must be given as the tuple: (name, list of VARs, ND-array)"
                    assert len(cur_var[2].shape) == 2, f"The array for sweeping parameter {cur_var[0]} must be 2D."
                    assert cur_var[2].shape[1] == len(cur_var[1]), f"The array for one-many sweeping parameter {cur_var[0]} must have {len(cur_var[1])} columns."
                    if len(aux_sweep) > 0:
                        assert aux_sweep[1] != ind_var, "The variable index for aux_sweep does not support many-one variables."
                    var_amalg = VariablePropertyOneManyTransient(cur_var[0], cur_var[1], cur_var[2])
                    sweep_vars2 += [(var_amalg, np.arange(cur_var[2].shape[0]))]
                    sweepEx[cur_var[0]] = {'vars' : cur_var[1], 'var_vals' : cur_var[2]}
            
            self._cur_names = [v[0].Name for v in sweep_vars2]
            assert len(self._cur_names) == len(set(self._cur_names)), "All assigned sweeping variable names must be unique."

            if not kill_signal():
                sweep_arrays = [x[1] for x in sweep_vars2]
                if rev_ind >= 0:
                    sweep_arrays[rev_ind] = np.concatenate([sweep_arrays[rev_ind], sweep_arrays[rev_ind][::-1]])
                if len(aux_sweep) > 0:
                    sweep_arrays[aux_sweep[1]] = np.concatenate([sweep_arrays[aux_sweep[1]], aux_sweep[2]])
                self._sweep_shape = [x.size for x in sweep_arrays]
                self._sweep_grids = np.meshgrid(*sweep_arrays)
                self._sweep_grids = np.array(self._sweep_grids)
                axes = np.arange(len(self._sweep_grids.shape))
                try:
                    axes[2] = 1
                    axes[1] = 2
                except IndexError:
                    pass
                self._sweep_grids = np.transpose(self._sweep_grids, axes=axes).reshape(len(sweep_arrays),-1).T
                
                #Setup permutations on the sweeping orders:        
                sweep_orders = kwargs.get('sweep_orders', [])
                assert not (len(sweep_orders) > 0 and rev_ind >= 0), "Cannot supply reverse_index and sweep_orders simultaneously."
                assert not (len(sweep_orders) > 0 and len(aux_sweep) > 0), "Cannot supply aux_sweep and sweep_orders simultaneously."
                swp_order = np.arange(self._sweep_grids.shape[0])
                for cur_order in sweep_orders:
                    assert isinstance(cur_order, ExperimentSweepBase), "The argument sweep_orders must be specified as a list of ExpSwp* (i.e. ExperimentSweepBase) objects."
                    swp_order = cur_order.get_sweep_indices(swp_order, self._sweep_shape)

                #sweep_vars2 is given as a list of tuples formatted as (parameter, sweep-values in an numpy-array)
                for m in range(self._sweep_grids.shape[0]):
                    ind_coord = swp_order[m]
                    cur_coord = self._sweep_grids[swp_order[m]]

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

                    #TODO: Consider letting other datasets also be temporarily accessible to mid_proces?
                    cur_raw_data = self._expt_config.get_data()
                    self._data = cur_raw_data.pop('data')
                    for x in cur_raw_data:
                        self._init_data_file(x, init_data_file_options)
                        aux_file = self._init_data_file(x+'_'+aux_sweep[0], init_data_file_options)[0] if len(aux_sweep) > 0 else None
                        self._store_datapkt(cur_raw_data[x], sweep_vars2, sweepEx, rev_ind, ind_coord, self._cur_filewriters[x], aux_file, aux_sweep) #TODO: Update documentation on ACQ Data Format - i.e. for auxiliary pieces...
                    #
                    self._store_datapkt(self._data, sweep_vars2, sweepEx, rev_ind, ind_coord, data_file, None, aux_sweep)
                    #
                    if len(rec_params) > 0:
                        if len(aux_sweep) > 0:
                            ret_val = self._init_data_file('rec_params_'+aux_sweep[0], init_data_file_options)
                            if isinstance(ret_val, (list, tuple)):
                                aux_file, rec_param_aux_file_name = ret_val
                        else:
                            aux_file = None
                        self._store_datapkt(self._prepare_rec_params(rec_params, rec_params_extra), sweep_vars2, sweepEx, rev_ind, ind_coord, rec_data_file, aux_file, aux_sweep)
                    self._sweep_vars = sweep_vars2
                    self._mid_process()
                    self._data = None
                    self._update_progress_bar((ind_coord+1)/self._sweep_grids.shape[0])

        #Close all data files
        for cur_file in self._cur_filewriters:
            self._cur_filewriters[cur_file].close()
        self._cur_filewriters.clear()
        
        if len(rec_params) > 0:
            self.last_rec_params = FileIOReader(file_path + rec_param_file_name)
            if len(aux_sweep) > 0:
                self.last_rec_params_aux = FileIOReader(file_path + rec_param_aux_file_name)
        self._expt_config.makesafe_instruments()
        self._sweep_grids = None
        self._cur_names = []

        if len(aux_sweep) > 0:
            self.last_data_aux = FileIOReader(file_path + data_file_name_aux)   #TODO: Document storage of FileIOReaders via attributes in Experiment

        return FileIOReader(file_path + data_file_name)


    def _store_datapkt(self, data_pkt, sweep_vars2, sweepEx, rev_ind, ind_coord, primary_file, aux_file, aux_sweep):
        store_pkt, store_ind = self._reverse_datapkt(data_pkt, sweep_vars2, rev_ind, ind_coord)
        store_pkt, datafile, store_ind, sweep_vars = self._settle_aux_datafile(data_pkt, primary_file, aux_file, sweep_vars2, aux_sweep, store_ind)
        datafile.push_datapkt(store_pkt, sweep_vars, sweepEx, dset_ind=store_ind) #TODO: Update documentation on ACQ Data Format - i.e. for auxiliary pieces...

    def _reverse_datapkt(self, datapkt, sweep_vars, rev_ind, ind_coord):
        if rev_ind < 0:
            return datapkt, ind_coord
        sweep_inds = list(np.unravel_index(ind_coord, self._sweep_shape))
        store_shape = [x[1].size for x in sweep_vars]
        num_swp_pts_on_reverse_var = sweep_vars[rev_ind][1].size
        if sweep_inds[rev_ind] < num_swp_pts_on_reverse_var:
            store_ind = np.ravel_multi_index(sweep_inds, store_shape)
            return datapkt, store_ind
        #
        le_channels = [x for x in datapkt['data']]
        for cur_ch in le_channels:
            datapkt['data'][cur_ch + '_reverse'] = datapkt['data'].pop(cur_ch)
        sweep_inds[rev_ind] = self._sweep_shape[rev_ind]-1 - sweep_inds[rev_ind]
        store_ind = np.ravel_multi_index(sweep_inds, store_shape)
        return datapkt, store_ind
    
    def _settle_aux_datafile(self, datapkt, datafile, datafile_aux, sweep_vars, aux_sweep_params, ind_coord):
        if len(aux_sweep_params) == 0:
            return datapkt, datafile, ind_coord, sweep_vars
        sweep_inds = list(np.unravel_index(ind_coord, self._sweep_shape))
        store_shape = [x[1].size for x in sweep_vars]
        num_swp_pts_on_main_var = sweep_vars[aux_sweep_params[1]][1].size
        if sweep_inds[aux_sweep_params[1]] < num_swp_pts_on_main_var:
            store_ind = np.ravel_multi_index(sweep_inds, store_shape)
            return datapkt, datafile, store_ind, sweep_vars
        #
        store_shape[aux_sweep_params[1]] = aux_sweep_params[2].size
        sweep_inds[aux_sweep_params[1]] = sweep_inds[aux_sweep_params[1]] - num_swp_pts_on_main_var
        store_ind = np.ravel_multi_index(sweep_inds, store_shape)
        if datafile_aux == None:
            datafile_aux = aux_sweep_params[3]
        leVars = [[v[0], v[1]*1] for v in sweep_vars]
        leVars[aux_sweep_params[1]][1] = aux_sweep_params[2]*1
        return datapkt, datafile_aux, store_ind, leVars


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
        if lePlot != None:
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

    def _query_current_iteration_data(self):
        return self._data

    def _push_data_mid_iteration(self, datafilename, last_sweep_var, data_pkt):
        if isinstance(last_sweep_var, str):
            assert last_sweep_var in self._cur_names, f"Variable {last_sweep_var} is not in the list of sweeping variables."
            var_ind = self._cur_names.index(last_sweep_var)
            self._cur_filewriters[datafilename].push_datapkt(data_pkt, self._sweep_vars[:var_ind+1])
        elif last_sweep_var == None:
            self._cur_filewriters[datafilename].push_datapkt(data_pkt, self._sweep_vars)
        else:
            assert False, 'The parameter \'last_sweep_var\' must be given as a string or None.'

    def _retrieve_current_sweep_values(self):
        if not isinstance(self._sweep_grids, np.ndarray):
            return {}
        return {x : self._sweep_grids[self._cur_ind_coord][ind] for ind, x in enumerate(self._cur_names)}
