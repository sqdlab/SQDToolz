import qcodes as qc
from sqdtoolz.Parameter import*
from datetime import datetime
from pathlib import Path
import json
import os

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
        self._group_dir = {'Dir':"", 'InitDir':""}

    def update_config_from_last_expt(self):
        #TODO: Stress test this with say 100000 directories
        dirs = [x[0] for x in os.walk(self._save_dir)]  #Walk gives a tuple: (dirpath, dirnames, filenames)
        last_dir = dirs[-1].replace('\\','/')
        if os.path.isfile(last_dir + "/laboratory_parameters.txt"):
            with open(last_dir + "/laboratory_parameters.txt") as json_file:
                data = json.load(json_file)
                for cur_param in data:
                    if cur_param in self._params:
                        self._params[cur_param].set_raw(data[cur_param])

    def add_parameter(self, param_name):
        self._params[param_name] = VariableInternal(param_name)
        return self._params[param_name]

    #TODO: combine with above
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
    
    def group_open(self, group_name):
        self._group_dir['Dir'] = group_name
        self._group_dir['InitDir'] = ""

    def group_close(self):
        self._group_dir['Dir'] = ""
        self._group_dir['InitDir'] = ""

    def run_single(self, expt_obj, sweep_vars=[]):
        #Get time-stamp
        if self._group_dir['Dir'] == "":
            folder_time_stamp = datetime.now().strftime(f"%Y-%m-%d/%H%M%S-" + expt_obj.Name + "/")
        else:
            if self._group_dir['InitDir'] == "":
                self._group_dir['InitDir'] = datetime.now().strftime(f"%Y-%m-%d/%H%M%S-{self._group_dir['Dir']}/")
            folder_time_stamp = self._group_dir['InitDir'] + datetime.now().strftime(f"%H%M%S-" + expt_obj.Name + "/")
        #Create the nested directory structure if it does not exist...
        cur_exp_path = self._save_dir + folder_time_stamp
        Path(cur_exp_path).mkdir(parents=True, exist_ok=True)

        #TODO: Write the sweeping code to appropriately nest folders or perform data-passing
        ret_vals = expt_obj._run(sweep_vars)
        #TODO: Add flag to get/save for live-plotting
        #Save data and experiment configurations
        expt_obj.save_data(cur_exp_path, ret_vals, sweep_vars=sweep_vars)
        expt_obj.save_config(cur_exp_path)
        #Save instrument configurations (QCoDeS)
        with open(cur_exp_path + 'instrument_configuration.txt', 'w') as outfile:
            json.dump(self.station.snapshot_base(), outfile, indent=4)
        #Save Laboratory Parameters
        param_dict = {k:v.get_raw() for (k,v) in self._params.items()}
        with open(cur_exp_path + 'laboratory_parameters.txt', 'w') as outfile:
            json.dump(param_dict, outfile, indent=4)
        
        expt_obj._post_process(ret_vals)

        return ret_vals
