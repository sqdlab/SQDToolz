import numpy as np
import time
import json

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

    def _post_process(self):
        pass

    def _run(self, sweep_vars=[]):
        param_names = [x[0].name for x in sweep_vars]
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
            data_all += [np.mean(data[0][0])]
        
        #data_all = np.concatenate(data_all)
        data_final = np.c_[sweep_grids, np.real(np.array(data_all))]
        data_final = np.c_[data_final, np.imag(np.array(data_all))]

        #TODO: think about different data-piece sizes: https://stackoverflow.com/questions/3386259/how-to-make-a-multidimension-numpy-array-with-a-varying-row-size

        return data
    
    def save_data(self, save_dir, data_final_array):
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
        self._expt_config.plot().savefig(save_dir + 'experiment_configuration.png')


#new_exp.run(tc, [(rabiWait, [0,1,2,3]), (vPower, [0,1,2,3])])

