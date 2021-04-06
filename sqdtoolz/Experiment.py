import numpy as np
import time
import json
import h5py
import os.path

import matplotlib.pyplot as plt

class Experiment:
    def __init__(self, name, expt_config):
        '''
        '''
        self._name = name
        self._expt_config = expt_config
        #List of digital delay generators
        self._DDGs = []
        #List of arbitrary waveform generators
        self._AWGs = []
        #List of acquisition devices
        self._ACQs = []

    @property
    def Name(self):
        return self._name

    def _post_process(self, data):
        pass

    def _run(self, file_path, sweep_vars=[]):
        self._hf = None

        sweep_arrays = [x[1] for x in sweep_vars]
        sweep_grids = np.meshgrid(*sweep_arrays)
        sweep_grids = np.array(sweep_grids).T.reshape(-1,len(sweep_arrays))
        
        data_all = []
        #sweep_vars is given as a list of tuples formatted as (parameter, sweep-values in an numpy-array)
        for cur_coord in sweep_grids:
            #Set the values
            for ind, cur_val in enumerate(cur_coord):
                sweep_vars[ind][0].set_raw(cur_val)
            #Now prepare the instrument
            # self._expt_config.check_conformance() #TODO: Write this
            self._expt_config.prepare_instruments()
            data = self._expt_config.get_data()
            self.update_file(file_path, data, sweep_vars)
            #TODO: Add in a preprocessor?
            # data_all += [np.mean(data[0][0])]
        
        #data_all = np.concatenate(data_all)
        # data_final = np.c_[sweep_grids, np.real(np.array(data_all))]
        # data_final = np.c_[data_final, np.imag(np.array(data_all))]

        if self._hf:
            self._hf.close()
            self._hf = None

        #TODO: think about different data-piece sizes: https://stackoverflow.com/questions/3386259/how-to-make-a-multidimension-numpy-array-with-a-varying-row-size

        return None#data_final
    
    def update_file(self, save_dir, data_pkt, sweep_vars):
        if self._hf == None:
            if os.path.isfile(save_dir + 'data.h5'):
                self._hf = h5py.File(save_dir + 'data.h5', 'a', libver='latest')
            else:
                self._hf = h5py.File(save_dir + 'data.h5', 'w', libver='latest')
                
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
        
        self._dset[self._dset_ind*self._datapkt_size : (self._dset_ind+1)*self._datapkt_size] = np.vstack([data_pkt['data'][x].flatten() for x in self._meas_chs]).T
        self._dset_ind += 1
        self._dset.flush()


    def save_data(self, save_dir, data_final_array, **kwargs):
        #TODO: Make a Data storage module for data saving (e.g. HDF5, CSV, IntensitySlice etc...)
        sweep_vars = kwargs.get('sweep_vars', [])

        param_names = [x[0].Name for x in sweep_vars]
        final_str = f"Timestamp: {time.asctime()} \n"
        col_num = 1
        for cur_param in param_names:
            final_str += "Column " + str(col_num) + ":\n"
            final_str += "\tname: " + cur_param + "\n"
            final_str += "\ttype: coordinate\n"
            col_num += 1
        final_str += "Column " + str(col_num) + ":\n"
        final_str += "\tname: real(analog)\n"
        final_str += "\ttype: value\n"
        col_num += 1
        final_str += "Column " + str(col_num) + ":\n"
        final_str += "\tname: imag(analog)\n"
        final_str += "\ttype: value"

        #Save data
        np.savetxt(save_dir + 'data.dat', data_final_array, delimiter='\t', header=final_str, fmt='%.15f')

    def save_config(self, save_dir):
        #Save the experiment configuration
        with open(save_dir + 'experiment_configuration.txt', 'w') as outfile:
            json.dump(self._expt_config.save_config(), outfile, indent=4)
        #Save a PNG of the Timing Plot
        lePlot = self._expt_config.plot()
        lePlot.savefig(save_dir + 'experiment_configuration.png')
        plt.close(lePlot)


#new_exp.run(tc, [(rabiWait, [0,1,2,3]), (vPower, [0,1,2,3])])

