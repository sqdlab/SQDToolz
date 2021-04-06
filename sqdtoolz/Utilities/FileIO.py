import h5py
import os.path
import numpy as np

class FileIOWriter:
    def __init__(self, filepath):
        self._filepath = filepath
        self._hf = None

    def _init_hdf5(self, sweep_vars, data_pkt):
        if self._hf == None:
            if os.path.isfile(self._filepath):
                self._hf = h5py.File(self._filepath, 'a', libver='latest')
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
                param_sizes = random_dataset.shape
                for m, cur_param in enumerate(data_pkt['parameters']):
                    grp_params.create_dataset(cur_param, data=np.hstack([m+offset,np.arange(param_sizes[m])]))
                
                #Write down the measurement output channels (i.e. dependent variables)
                grp_meas = self._hf.create_group('measurements')
                self._meas_chs = []
                for m, cur_meas_ch in enumerate(data_pkt['data'].keys()):
                    grp_meas.create_dataset(cur_meas_ch, data=np.hstack([m]))
                    self._meas_chs += [cur_meas_ch]

                data_array_shape = [x[1].size for x in sweep_vars] + list(param_sizes)
                arr_size = np.prod(data_array_shape)
                self._datapkt_size = np.prod(list(param_sizes))

                arr = np.zeros((arr_size, len(data_pkt['data'].keys())))
                arr[:] = np.nan
                self._dset = self._hf.create_dataset("data", data=arr, compression="gzip")
                self._dset_ind = 0

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
        self._dep_params = [None]*len(self.hdf5_file["measurements"].keys())
        for cur_key in self.hdf5_file["measurements"].keys():
            cur_ind = self.hdf5_file["measurements"][cur_key][0]
            self._dep_params[cur_ind] = cur_key

        temp_param_names = self.param_names[:]
        self.param_vals = [None]*len(temp_param_names) 
        for cur_param in temp_param_names:
            cur_ind = int(self.hdf5_file["parameters"][cur_param][0])
            self.param_names[cur_ind] = cur_param
            self.param_vals[cur_ind] = self.hdf5_file["parameters"][cur_param][1:]

    def get_numpy_array(self):
        cur_shape = [len(x) for x in self.param_vals] + [len(self._dep_params)]
        return self.dset[:].reshape(tuple(x for x in cur_shape))
