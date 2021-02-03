import qcodes as qc
from datetime import datetime
from pathlib import Path
import json
import numpy as np
import time

class Experiment:
    def __init__(self, instr_config_file, save_dir, name=""):
        '''
        '''

        if instr_config_file == "":
            self.station = qc.Station()
        else:
            self.station = qc.Station(config_file=instr_config_file)
        #TODO: Add initialiser for load last file in save_dir thing...

        #Convert Windows backslashes into forward slashes (should be compatible with MAC/Linux then...)
        self._save_dir = save_dir.replace('\\','/')
        self._name = name

        #List of digital delay generators
        self._DDGs = []
        #List of arbitrary waveform generators
        self._AWGs = []
        #List of acquisition devices
        self._ACQs = []
        
    def add_instrument(self, instrObj):
        self.station.add_component(instrObj)

    def run(self, timing_config, sweep_vars=[]):
        #Get time-stamp
        folder_time_stamp = datetime.now().strftime("%Y-%m-%d/%H%M%S-" + self._name + "/")
        #Create the nested directory structure if it does not exist...
        cur_exp_path = self._save_dir + folder_time_stamp
        Path(cur_exp_path).mkdir(parents=True, exist_ok=True)

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
            timing_config.prepare_instruments()
            data = timing_config.get_data()
            data_all += [np.mean(data[0][0])]
        
        #data_all = np.concatenate(data_all)
        data_final = np.c_[sweep_grids, np.real(np.array(data_all))]
        data_final = np.c_[data_final, np.imag(np.array(data_all))]

        #TODO: think about different data-piece sizes: https://stackoverflow.com/questions/3386259/how-to-make-a-multidimension-numpy-array-with-a-varying-row-size

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
        with open(cur_exp_path + 'data.dat', 'w') as outfile:
            np.savetxt(cur_exp_path + 'data.dat', data_final, delimiter='\t', header=final_str, fmt='%.15f')            
        # with open(cur_exp_path + 'timing_configuration.txt', 'w') as outfile:
        #     json.dump(timing_config.save_config(), outfile, indent=4)
        # with open(cur_exp_path + 'instrument_configuration.txt', 'w') as outfile:
        #     json.dump(self.station.snapshot_base(), outfile, indent=4)

        return data


#new_exp.run(tc, [(rabiWait, [0,1,2,3]), (vPower, [0,1,2,3])])

