import qcodes as qc
from sqdtoolz.Parameter import*
from datetime import datetime
from pathlib import Path
import json

class Laboratory:
    def __init__(self, instr_config_file, save_dir):
        self._params = {}
        if instr_config_file == "":
            self.station = qc.Station()
        else:
            self.station = qc.Station(config_file=instr_config_file)
        #TODO: Add initialiser for load last file in save_dir thing...

        #Convert Windows backslashes into forward slashes (should be compatible with MAC/Linux then...)
        self._save_dir = save_dir.replace('\\','/')

    def add_parameter(self, param_name):
        self._params[param_name] = VariableInternal(param_name)
        return self._params[param_name]

    def add_parameter_property(self, param_name, sqdObj, prop_name):
        self._params[param_name] = VariableProperty(param_name, sqdObj, prop_name)
        return self._params[param_name]

    def get_parameter(param_name):
        assert param_name in self._params, f"Parameter name {param_name} does not exist."
        return self._params[param_name]

    def add_instrument(self, instrObj):
        self.station.add_component(instrObj)

    def get_instrument(instrID):
        assert instrID in station.components, f"Instrument by the name {instrID} has not been loaded."
        return station.components[instrID]
    
    def run_single(self, expt_obj, sweep_vars=[]):
        #Get time-stamp
        folder_time_stamp = datetime.now().strftime("%Y-%m-%d/%H%M%S-" + expt_obj.Name + "/")
        #Create the nested directory structure if it does not exist...
        cur_exp_path = self._save_dir + folder_time_stamp
        Path(cur_exp_path).mkdir(parents=True, exist_ok=True)

        #TODO: Write the sweeping code to appropriately nest folders or perform data-passing
        ret_vals = expt_obj._run(sweep_vars)
        #Save data and experiment configurations
        expt_obj.save_data(cur_exp_path, ret_vals)
        expt_obj.save_config(cur_exp_path)
        #
        expt_obj._post_process(ret_vals)

        with open(cur_exp_path + 'instrument_configuration.txt', 'w') as outfile:
            json.dump(self.station.snapshot_base(), outfile, indent=4)

        return ret_vals
