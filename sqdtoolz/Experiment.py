import numpy as np
import time
import json

import matplotlib.pyplot as plt

from sqdtoolz.Utilities.FileIO import*

class Experiment:
    def __init__(self, name, expt_config):
        '''
        '''
        self._name = name
        self._expt_config = expt_config

    @property
    def Name(self):
        return self._name

    def _post_process(self, data):
        pass

    def _run(self, file_path, sweep_vars=[], **kwargs):
        delay = kwargs.get('delay', 0.0)
        ping_iteration = kwargs.get('ping_iteration')
        
        data_file_index = kwargs.get('data_file_index', -1)
        if data_file_index >= 0:
            data_file_name = f'data{data_file_index}.h5'
        else:
            data_file_name = 'data.h5'

        data_file = FileIOWriter(file_path + data_file_name)

        if not kwargs.get('skip_init_instruments', False):
            self._expt_config.init_instruments()

        waveform_updates = kwargs.get('update_waveforms', None)
        if waveform_updates != None:
            self._expt_config.update_waveforms(waveform_updates)

        if len(sweep_vars) == 0:
            self._expt_config.prepare_instruments()
            data = self._expt_config.get_data()
            data_file.push_datapkt(data, sweep_vars)
            time.sleep(delay)
        else:
            sweep_arrays = [x[1] for x in sweep_vars]
            sweep_grids = np.meshgrid(*sweep_arrays)
            sweep_grids = np.array(sweep_grids).T.reshape(-1,len(sweep_arrays))
            
            data_all = []
            #sweep_vars is given as a list of tuples formatted as (parameter, sweep-values in an numpy-array)
            for ind_coord, cur_coord in enumerate(sweep_grids):
                #Set the values
                for ind, cur_val in enumerate(cur_coord):
                    sweep_vars[ind][0].set_raw(cur_val)
                #Now prepare the instrument
                # self._expt_config.check_conformance() #TODO: Write this
                self._expt_config.prepare_instruments()
                time.sleep(delay)
                data = self._expt_config.get_data()
                data_file.push_datapkt(data, sweep_vars)
                ping_iteration((ind_coord+1)/sweep_grids.shape[0])
                #TODO: Add in a preprocessor?
                # data_all += [np.mean(data[0][0])]

        data_file.close()
        self._expt_config.makesafe_instruments()

        #TODO: think about different data-piece sizes: https://stackoverflow.com/questions/3386259/how-to-make-a-multidimension-numpy-array-with-a-varying-row-size

        #TODO: Should the return value be a list if there are a few saved files?
        return FileIOReader(file_path + data_file_name)

    def save_config(self, save_dir, name_time_diag, name_expt_params, sweep_queue = []):
        #Save a PNG of the Timing Plot
        lePlot = self._expt_config.plot()
        lePlot.savefig(save_dir + name_time_diag + '.png')
        plt.close(lePlot)

        dict_expt_params = {
            'Name' : self.Name,
            'Type' : self.__class__.__name__,
            'Config' : self._expt_config.Name,
            'Sweeps' : sweep_queue
        }
        with open(save_dir + name_expt_params, 'w') as outfile:
            json.dump(dict_expt_params, outfile, indent=4)
