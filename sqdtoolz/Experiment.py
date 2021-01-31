import qcodes as qc
from datetime import datetime
from pathlib import Path
import json

class Experiment:
    def __init__(self, instr_config_file, save_dir, name=""):
        '''
        '''

        if instr_config_file == "":
            self.station = qc.Station()
        else:
            self.station = qc.Station(config_file=instr_config_file)

        self._save_dir = save_dir
        self._name = name

        #List of digital delay generators
        self._DDGs = []
        #List of arbitrary waveform generators
        self._AWGs = []
        #List of acquisition devices
        self._ACQs = []
        
    def add_instrument(self, instrObj):
        self.station.add_component(instrObj)

    def run (self, timing_config, sweep_vars=[]):
        #Get time-stamp
        folder_time_stamp = datetime.now().strftime("%Y-%m-%d\\%H%M%S-" + self._name + "\\")
        #Create the nested directory structure if it does not exist...
        cur_exp_path = self._save_dir + folder_time_stamp
        Path(cur_exp_path).mkdir(parents=True, exist_ok=True)

        #sweep_vars is given as a list of tuples formatted as (parameter, sweep-values in an numpy-array)
        #TODO: Write for-loops for each sweeping variable...
        timing_config.prepare_instruments()
        data = timing_config.get_data()

        #TODO: think about different data-piece sizes: https://stackoverflow.com/questions/3386259/how-to-make-a-multidimension-numpy-array-with-a-varying-row-size

        #Save data
        with open(cur_exp_path + 'data.txt', 'w') as outfile:
            json.dump(data.tolist(), outfile, indent=4)
        with open(cur_exp_path + 'timing_configuration.txt', 'w') as outfile:
            json.dump(timing_config.save_config(), outfile, indent=4)
        with open(cur_exp_path + 'instrument_configuration.txt', 'w') as outfile:
            json.dump(self.station.snapshot_base(), outfile, indent=4)        

        return data


