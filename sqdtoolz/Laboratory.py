import qcodes as qc
from sqdtoolz.Parameter import*
from datetime import datetime
from pathlib import Path
import json
import os
import time
import numpy as np

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

    def get_instrument(self, instrID):
        assert instrID in self.station.components, f"Instrument by the name {instrID} has not been loaded."
        return self.station.components[instrID]
    
    def group_open(self, group_name):
        self._group_dir['Dir'] = group_name
        self._group_dir['InitDir'] = ""

    def group_close(self):
        self._group_dir['Dir'] = ""
        self._group_dir['InitDir'] = ""

    def run_single(self, expt_obj, sweep_vars=[], **kwargs):
        delay = kwargs.get('delay', 0.0)

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
        self._time_stamp_begin = time.time()
        self._time_stamps = [(0,0),]
        ret_vals = expt_obj._run(cur_exp_path, sweep_vars, ping_iteration=self._update_progress_bar, delay=delay)
        #TODO: Add flag to get/save for live-plotting
        #Save experiment configurations
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

    @staticmethod
    def _printProgressBar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 50, fill = '█', printEnd = "\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)

        Taken from: https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
        # Print New Line on Complete
        if iteration == total: 
            print()

    def _update_progress_bar(self, val_pct):
        self._time_stamps += [(val_pct, time.time())]

        ts = np.array([x[1] for x in self._time_stamps])
        pcts = np.array([x[0] for x in self._time_stamps])
        
        dTs = ts - self._time_stamp_begin
        dTs[0] = 0
        dTs = dTs[1:]-dTs[:-1]
        #
        dPcts = pcts[1:]-pcts[:-1]
        #
        dTbydPs = dTs/dPcts

        #Take an exponential distribution of the dT/dP (i.e. recent ones have a higher weighting) when taking the average: <dT/dP>
        self._time_stamps[-1][0]
        init_weight = 0.5
        
        if val_pct > 0:
            total_weight = np.sum(0.5*np.exp(-pcts[1:] * np.log(init_weight)/val_pct))
            average_weight = np.sum(dTbydPs * 0.5*np.exp(-pcts[1:] * np.log(init_weight)/val_pct) / total_weight)
            #
            time_left = average_weight*(1-val_pct)
            if time_left > 60:
                time_left = f"Est. time left: {(time_left/60.0):.2f}mins"
            else:
                time_left = f"Est. time left: {time_left:.2f}s"
        else:
            time_left = ""

        total_time = ts[-1] - self._time_stamp_begin
        if total_time > 60:
            total_time = f"Total time: {(total_time/60.0):.2f}mins"
        else:
            total_time = f"Total time: {total_time:.2f}s"
        
        self._printProgressBar(int(val_pct*100), 100, suffix=f"{total_time}, {time_left}")
