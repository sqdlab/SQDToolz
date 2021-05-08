import h5py
import os.path
import json
import numpy as np

class FileIOWriter:
    def __init__(self, filepath):
        self._filepath = filepath
        self._hf = None

    def _init_hdf5(self, sweep_vars, data_pkt):
        if self._hf == None:
            if os.path.isfile(self._filepath):
                self._hf = h5py.File(self._filepath, 'a', libver='latest')
                self._hf.swmr_mode = True
            else:
                self._hf = h5py.File(self._filepath, 'w', libver='latest')
                
                #Write down the indexing parameters (i.e. independent variables)
                grp_params = self._hf.create_group('parameters')
                #Assumes uniformity - TODO: Look into padding with NaNs if the inner data packets change in shape (e.g. different repetitions etc...)
                for m, cur_param in enumerate(sweep_vars):
                    grp_params.create_dataset(cur_param[0].Name, data=np.hstack([m,cur_param[1]]))
                offset = len(sweep_vars)
                #
                random_dataset = next(iter(data_pkt['data'].values()))
                if np.isscalar(random_dataset):
                    param_sizes = (1,)
                else:
                    param_sizes = random_dataset.shape
                #
                for m, cur_param in enumerate(data_pkt['parameters']):
                    if 'parameter_values' in data_pkt and cur_param in data_pkt['parameter_values']:
                        assert data_pkt['parameter_values'][cur_param].size == param_sizes[m], f"The dataset parameter {cur_param} has {data_pkt['parameter_values'][cur_param].size} values, while the corresponding array index is of size {param_sizes[m]}."
                        grp_params.create_dataset(cur_param, data=np.hstack([m+offset,data_pkt['parameter_values'][cur_param]]))
                    else:
                        grp_params.create_dataset(cur_param, data=np.hstack([m+offset,np.arange(param_sizes[m])]))
                
                #Write down the measurement output channels (i.e. dependent variables)
                grp_meas = self._hf.create_group('measurements')
                self._meas_chs = []
                for m, cur_meas_ch in enumerate(data_pkt['data'].keys()):
                    grp_meas.create_dataset(cur_meas_ch, data=np.hstack([m]))
                    self._meas_chs += [cur_meas_ch]

                if len(param_sizes) == 0:
                    self._datapkt_size = 1
                else:
                    self._datapkt_size = np.prod(list(param_sizes))

                data_array_shape = [x[1].size for x in sweep_vars] + list(param_sizes)
                arr_size = np.prod(data_array_shape)
                arr = np.zeros((arr_size, len(data_pkt['data'].keys())))
                arr[:] = np.nan
                self._dset = self._hf.create_dataset("data", data=arr, compression="gzip")
                self._dset_ind = 0
                
                self._hf.swmr_mode = True

    def push_datapkt(self, data_pkt, sweep_vars):
        self._init_hdf5(sweep_vars, data_pkt)

        self._dset[self._dset_ind*self._datapkt_size : (self._dset_ind+1)*self._datapkt_size] = np.vstack([data_pkt['data'][x].flatten() for x in self._meas_chs]).T
        self._dset_ind += 1
        self._dset.flush()
    
    def close(self):
        if self._hf:
            self._hf.close()
            self._hf = None

class FileIOReader:
    def __init__(self, filepath):
        self._filepath = filepath
        self.hdf5_file = h5py.File(filepath, 'r', libver='latest', swmr=True)
        self.dset = self.hdf5_file["data"]

        #Extract the independent variables (the group "parameters" holds the 1D arrays representing the individual parameter values)
        self.param_names = [x for x in self.hdf5_file["parameters"].keys()]

        #Extract the independent variables (the group "parameters" holds the 1D arrays representing the individual parameter values)
        self.dep_params = [None]*len(self.hdf5_file["measurements"].keys())
        for cur_key in self.hdf5_file["measurements"].keys():
            cur_ind = self.hdf5_file["measurements"][cur_key][0]
            self.dep_params[cur_ind] = cur_key

        temp_param_names = self.param_names[:]
        self.param_vals = [None]*len(temp_param_names) 
        for cur_param in temp_param_names:
            cur_ind = int(self.hdf5_file["parameters"][cur_param][0])
            self.param_names[cur_ind] = cur_param
            self.param_vals[cur_ind] = self.hdf5_file["parameters"][cur_param][1:]

    def get_numpy_array(self):
        cur_shape = [len(x) for x in self.param_vals] + [len(self.dep_params)]
        return self.dset[:].reshape(tuple(x for x in cur_shape))

class FileIODirectory:
    def __init__(self, filepath):
        cur_dir_path = os.path.dirname(filepath)
        dir_name = os.path.basename(cur_dir_path)
        assert dir_name[0:6].isdigit(), "The time-stamp is not present in this folder."

        self._main_dir = os.path.dirname(os.path.dirname(filepath))
        assert os.path.basename(self._main_dir)[0:6].isdigit(), "The time-stamp is not present in the parent folder."
        self._cur_dir_suffix = dir_name[6:]
        self._cur_file_name = os.path.basename(filepath)

        #Open the current file to get information on the data shape and sweeping parameters...
        #
        hdf5_file = h5py.File(filepath, 'r', libver='latest', swmr=True)
        #
        #TODO: Add error-checking on this when opening multiple files (i.e. check parameters and measurements...)
        #
        #Extract the independent variables (the group "parameters" holds the 1D arrays representing the individual parameter values)
        self.param_names = [x for x in hdf5_file["parameters"].keys()]
        #
        #Extract the independent variables (the group "parameters" holds the 1D arrays representing the individual parameter values)
        self.dep_params = [None]*len(hdf5_file["measurements"].keys())
        for cur_key in hdf5_file["measurements"].keys():
            cur_ind = hdf5_file["measurements"][cur_key][0]
            self.dep_params[cur_ind] = cur_key
        #
        temp_param_names = self.param_names[:]
        self.param_vals = [None]*len(temp_param_names) 
        for cur_param in temp_param_names:
            cur_ind = int(hdf5_file["parameters"][cur_param][0])
            self.param_names[cur_ind] = cur_param
            self.param_vals[cur_ind] = hdf5_file["parameters"][cur_param][1:]
        self._cur_data_shape = [len(x) for x in self.param_vals] + [len(self.dep_params)]
        #
        hdf5_file.close()

        #Extract variable sweeping parameters if relevant
        self._sweeping_vars = self._get_sweeping_vars(cur_dir_path)

        self._cur_data = None

        self._scan_directories()

    @classmethod
    def fromReader(cls, obj_FileIOReader):
        return cls(obj_FileIOReader._filepath)

    def _get_sweeping_vars(self, cur_folder):
        with open(cur_folder +'/' + 'experiment_parameters.txt') as json_file:
            data = json.load(json_file)
            return data['Sweeps']

    def _get_variable_vals(self, cur_folder, cur_vars):
        with open(cur_folder +'/' + 'laboratory_parameters.txt') as json_file:
            data = json.load(json_file)
            return [data[x]['Value'] for x in cur_vars]

    def _check_if_meshgrid(self, sweep_grid):
        unique_vals = []
        num_cols = sweep_grid.shape[1]
        for m in range(num_cols):
            u, ind = np.unique(sweep_grid[:,m], return_index=True)
            unique_vals += [u[np.argsort(ind)]]
        
        sweep_grids = np.meshgrid(*unique_vals)
        sweep_grids = np.array(sweep_grids).T.reshape(-1,num_cols)
        if np.array_equal(sweep_grid, sweep_grids):
            return unique_vals
        else:
            return None

    def _scan_directories(self):
        cur_dir_files = [x[0] for x in os.walk(self._main_dir)][1:]
        self._cur_data = None    #TODO: Remove this and use a modified check or rather the last one?
        can_gridify = True
        sweep_grid = []
        for cur_folder in cur_dir_files:
            #Check that the suffix of the folder name matches...
            if not os.path.basename(cur_folder).endswith(self._cur_dir_suffix):
                continue
            # #Check that the folder hasn't already been scanned
            # dir_name = os.path.basename(cur_folder)
            # if dir_name in [x[0] for x in self.dsets]:
            #     continue
            #Check that the h5 file exists...
            filepath = cur_folder +'/' + self._cur_file_name
            if not os.path.isfile(cur_folder +'/' + self._cur_file_name):
                continue
            
            hdf5_file = h5py.File(filepath, 'r', libver='latest', swmr=True)
            dset = hdf5_file["data"]
            #TODO: Add error-checking here...
            cur_data = dset[:].reshape(tuple(x for x in self._cur_data_shape))
            if type(self._cur_data) is np.ndarray:
                self._cur_data = np.concatenate([self._cur_data, [cur_data]])
            else:
                self._cur_data = np.array([cur_data])
            hdf5_file.close()

            if can_gridify:
                cur_sweep_vars = self._get_sweeping_vars(cur_folder)
                if self._sweeping_vars != cur_sweep_vars:
                    can_gridify = False
                else:
                    sweep_grid += [self._get_variable_vals(cur_folder, cur_sweep_vars)]
        new_param_vals = self._check_if_meshgrid(np.array(sweep_grid))
        if new_param_vals is not None:
            self.param_vals = new_param_vals + self.param_vals
            self.param_names = self._sweeping_vars + self.param_names
            self._cur_data = self._cur_data.reshape(tuple( [x.size for x in self.param_vals] + [len(self.dep_params)] ))
        else:
            #Just flatten any structure and give it as a single array...
            self.param_names = ['DirFileNo'] + self.param_names

    def get_numpy_array(self):
        return self._cur_data
