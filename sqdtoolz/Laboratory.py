import qcodes as qc
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Variable import*
from sqdtoolz.HAL.HALbase import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.HAL.GENvoltSource import*
from sqdtoolz.HAL.GENswitch import*
from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.ProcessorGPU import*
from datetime import datetime
from pathlib import Path
import json
import os
import time
import numpy as np

class Laboratory:
    def __init__(self, instr_config_file, save_dir):
        if instr_config_file == "":
            self._station = qc.Station()
        else:
            self._station = qc.Station(config_file=instr_config_file)
        self._instr_config_file = instr_config_file
        #TODO: Add initialiser for load last file in save_dir thing...

        #Convert Windows backslashes into forward slashes (should be compatible with MAC/Linux then...)
        self._save_dir = save_dir.replace('\\','/')
        self._group_dir = {'Dir':"", 'InitDir':"", 'SweepQueue':[]}

        self._hal_objs = {}
        self._processors = {}
        self._expt_configs = {}
        self._variables = {}
        self._waveform_transforms = {}
        self._activated_instruments = []

    def reload_yaml(self):
        #NOTE: This will update the snapshots and thus, change instrument state of already loaded instruments. But it is handy
        #to help load a new instrument into the QCoDeS station (when adding a new instrument in the YAML).
        if self._instr_config_file != "":
            self._station.load_config_file(self._instr_config_file)

    def _load_json_file(self, filepath):
        if os.path.isfile(filepath):
            with open(filepath) as json_file:
                data = json.load(json_file)
                return data
            return None
        return None

    def update_variables_from_last_expt(self, file_name = ''):
        if file_name == '':
            #TODO: Stress test this with say 100000 directories
            dirs = [x[0] for x in os.walk(self._save_dir)]  #Walk gives a tuple: (dirpath, dirnames, filenames)
            cur_dir = dirs[-1].replace('\\','/')
            if os.path.isfile(cur_dir + "/laboratory_parameters.txt"):
                filepath = cur_dir + "/laboratory_parameters.txt"
        else:
            filepath = file_name
        with open(filepath) as json_file:
            data = json.load(json_file)
            for cur_key in data.keys():
                cur_dict = data[cur_key]
                if cur_key in self._variables.keys():
                    self._variables[cur_key]._set_current_config(cur_dict)
                else:
                    self._variables[cur_key] = globals()[cur_dict['Type']].fromConfigDict(cur_key, cur_dict, self)

    def cold_reload_last_configuration(self):
        dirs = [x[0] for x in os.walk(self._save_dir)]  #Walk gives a tuple: (dirpath, dirnames, filenames)
        
        #Go through the directories in reverse chronological order (presuming data-stamped folders)
        for cur_cand_dir in dirs[::-1]:
            cur_dir = cur_cand_dir.replace('\\','/')
            #Check current candidate directory has the required files
            if not os.path.isfile(cur_dir + "/laboratory_configuration.txt"):
                continue
            if not os.path.isfile(cur_dir + "/experiment_configurations.txt"):
                continue
            if not os.path.isfile(cur_dir + "/laboratory_parameters.txt"):
                continue
            #If the files concurrently exist, then load the data...
            self.cold_reload_labconfig(self._load_json_file(cur_dir + "/laboratory_configuration.txt"))
            self.cold_reload_experiment_configurations(self._load_json_file(cur_dir + "/experiment_configurations.txt"))
            self.update_variables_from_last_expt(cur_dir + "/laboratory_parameters.txt")
            return
        assert False, "No valid previous experiment with all data files were found to be present."

    def cold_reload_experiment_configurations(self, config_dict):
        for cur_expt_config in config_dict:
            cur_keys = config_dict[cur_expt_config]['HALs']
            cur_types = [x['Type'] for x in cur_keys]
            cur_hals = [x['Name'] for x in cur_keys]
            if 'ACQ' in cur_types:
                ind = cur_types.index('ACQ')
                cur_hals.pop(ind)
                acq_obj = self.HAL(cur_keys[ind]['Name'])
            else:
                acq_obj = None
            cur_hals = [self.HAL(x) for x in cur_hals]
            new_expt_config = ExperimentConfiguration(cur_expt_config, self, 0, cur_hals, acq_obj)
            new_expt_config.update_config(config_dict[cur_expt_config])
    
    def cold_reload_labconfig(self, config_dict):
        for cur_instr in config_dict['ActiveInstruments']:
            self.load_instrument(cur_instr)
        #Create the HALs
        for dict_cur_hal in config_dict['HALs']:
            cur_class_name = dict_cur_hal['Type']
            globals()[cur_class_name].fromConfigDict(dict_cur_hal, self)
        #Load parameters (including trigger relationships) onto the HALs
        for dict_cur_hal in config_dict['HALs']:
            cur_hal_name = dict_cur_hal['Name']
            self._hal_objs[cur_hal_name]._set_current_config(dict_cur_hal, self)
        #Create and load the PROCs
        for dict_cur_proc in config_dict['PROCs']:
            cur_class_name = dict_cur_proc['Type']
            globals()[cur_class_name].fromConfigDict(dict_cur_proc, self)
        #Create and load the WFMTs
        for dict_cur_wfmt in config_dict['WFMTs']:
            cur_class_name = dict_cur_wfmt['Type']
            globals()[cur_class_name].fromConfigDict(dict_cur_wfmt, self)


    def _resolve_sqdobj_tree(self, sqdObj):
        resolution_tree = []
        cur_obj = sqdObj
        cur_parent = cur_obj.Parent  #Note that Parent is: (object reference to parent, metadata to find current object from parent object's POV)
        while (type(cur_parent) is tuple and cur_parent[0] != None):
            resolution_tree += [( cur_obj.Name, cur_parent[1] )]
            cur_obj = cur_parent[0]
            cur_parent = cur_obj.Parent
        if isinstance(cur_obj, HALbase):
            assert cur_obj.Name in self._hal_objs, f"It seems that {sqdObj.Name} is a part of some rogue unregistered HAL object."
            resolution_tree += [(cur_obj.Name, 'HAL')]
        elif isinstance(cur_obj, WaveformTransformation):
            assert cur_obj.Name in self._waveform_transforms, f"It seems that {sqdObj.Name} is a part of some rogue unregistered WaveformTransformation object."
            resolution_tree += [(cur_obj.Name, 'WFMT')]
        return resolution_tree[::-1]

    def _get_resolved_obj(self, res_list):
        ret_obj = None
        if res_list[0][1] == 'HAL':
            ret_obj = self.HAL(res_list[0][0])
        elif res_list[0][1] == 'WFMT':
            ret_obj = self.WFMT(res_list[0][0])
        #
        if ret_obj == None:
            return None
        
        if len(res_list) > 0:
            if ret_obj == None:
                return None
            for m in range(1,len(res_list)):
                ret_obj = ret_obj._get_child(res_list[m])
        return ret_obj

    def _register_HAL(self, hal_obj):
        if not (hal_obj.Name in self._hal_objs):
            self._hal_objs[hal_obj.Name] = hal_obj
            return True
        return False
    def HAL(self, hal_ID):
        if hal_ID in self._hal_objs:
            return self._hal_objs[hal_ID]
        else:
            return None

    def _register_PROC(self, proc):
        if not (proc.Name in self._processors):
            self._processors[proc.Name] = proc
            return True
        return False
    def PROC(self, proc_name):
        if proc_name in self._processors:
            return self._processors[proc_name]
        else:
            return None

    def _register_WFMT(self, wfmt):
        if not (wfmt.Name in self._waveform_transforms):
            self._waveform_transforms[wfmt.Name] = wfmt
            return True
        return False
    def WFMT(self, wfmt_name):
        if wfmt_name in self._waveform_transforms:
            return self._waveform_transforms[wfmt_name]
        else:
            return None

    def _register_VAR(self, hal_var):
        if not (hal_var.Name in self._variables):
            self._variables[hal_var.Name] = hal_var
            return True
        return False
    def VAR(self, param_name):
        if param_name in self._variables:
            return self._variables[param_name]
        else:
            return None

    def _register_CONFIG(self, expt_config):
        if not (expt_config.Name in self._expt_configs):
            self._expt_configs[expt_config.Name] = expt_config
            return True
        return False
    def CONFIG(self, expt_config_name):
        if expt_config_name in self._expt_configs:
            return self._expt_configs[expt_config_name]
        else:
            return None

    def add_instrument(self, instrObj):
        self._station.add_component(instrObj)
        self._activated_instruments += [instrObj.name]

    def load_instrument(self, instrID):
        # assert not (instrID in self._station.components), f"Instrument by the name {instrID} has already been loaded."
        if not (instrID in self._station.components):
            self._station.load_instrument(instrID)
            self._activated_instruments += [instrID]

    def _get_instrument(self, instrID):
        if type(instrID) is list:
            assert instrID[0] in self._station.components, f"Instrument by the name {instrID[0]} has not been loaded. Call load_instrument on it first."
            cur_instr_obj = self._station.components[instrID[0]]
            #Go through each submodule...
            for m in range(1, len(instrID)):
                assert instrID[m] in cur_instr_obj.submodules, f"The submodule {instrID[m]} does not exist."
                cur_instr_obj = cur_instr_obj.submodules[instrID[m]]
            return cur_instr_obj
        else:
            assert instrID in self._station.components, f"Instrument by the name {instrID} has not been loaded. Call load_instrument on it first."
            return self._station.components[instrID]


    def group_open(self, group_name):
        self._group_dir['Dir'] = group_name
        self._group_dir['InitDir'] = ""
        self._group_dir['SweepQueue'] = []

    def group_close(self):
        self._group_dir['Dir'] = ""
        self._group_dir['InitDir'] = ""
        self._group_dir['SweepQueue'] = []

    def _sweep_enqueue(self, var_name):
        self._group_dir['SweepQueue'].append(var_name)
    def _sweep_dequeue(self, var_name):
        self._group_dir['SweepQueue'].pop()

    def run_single(self, expt_obj, sweep_vars=[], **kwargs):
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
        self._prog_bar_str = ''
        ret_vals = expt_obj._run(cur_exp_path, sweep_vars, ping_iteration=self._update_progress_bar, **kwargs)
        #TODO: Add flag to get/save for live-plotting

        #Save the experiment configuration
        self.save_experiment_configs(cur_exp_path)
        #Save experiment-specific experiment-configuration data (i.e. timing diagram)
        expt_obj.save_config(cur_exp_path, 'timing_diagram', 'experiment_parameters.txt', self._group_dir['SweepQueue'])

        #Save instrument configurations (QCoDeS)
        self._save_instrument_config(cur_exp_path)
        #Save Laboratory Configuration
        self.save_laboratory_config(cur_exp_path)

        #Run postprocessing
        expt_obj._post_process(ret_vals)
        
        #Save Laboratory Parameters
        self.save_variables(cur_exp_path)

        return ret_vals

    def save_variables(self, cur_exp_path = '', file_name = 'laboratory_parameters.txt'):
        param_dict = {k:v._get_current_config() for (k,v) in self._variables.items()}
        with open(cur_exp_path + file_name, 'w') as outfile:
            # json.dump(param_dict, outfile)
            outfile.write(
                '{\n' +
                ',\n'.join(f"\"{x}\" : {json.dumps(param_dict[x])}" for x in param_dict.keys()) +
                '\n}\n')

    def save_experiment_configs(self, cur_exp_path, file_name = 'experiment_configurations.txt'):
        dict_expt_configs = {x : self._expt_configs[x].get_config() for x in self._expt_configs}
        with open(cur_exp_path + file_name, 'w') as outfile:
            json.dump(dict_expt_configs, outfile, indent=4)

    def save_laboratory_config(self, cur_exp_path, file_name = 'laboratory_configuration.txt'):
        #Prepare the dictionary of HAL configurations
        dict_hals = []
        for cur_hal in self._hal_objs:
            dict_hals.append(self._hal_objs[cur_hal]._get_current_config())

        #Prepare the dictionary of PROC configurations
        dict_procs = []
        for cur_proc in self._processors:
            dict_procs.append(self._processors[cur_proc]._get_current_config())

        #Prepare the dictionary of Waveform Transformations
        dict_wfmts = []
        for cur_wfmt in self._waveform_transforms:
            dict_wfmts.append(self._waveform_transforms[cur_wfmt]._get_current_config())

        param_dict = {
                    'ActiveInstruments' : self._activated_instruments,
                    'HALs' : dict_hals,
                    'PROCs': dict_procs,
                    'WFMTs': dict_wfmts
                    }
        if cur_exp_path != '':
            with open(cur_exp_path + file_name, 'w') as outfile:
                json.dump(param_dict, outfile, indent=4)
        return param_dict

    def _save_instrument_config(self, cur_exp_path):
        #Sometimes the configuration parameters use byte-values; those bytes need to be converted into strings
        #Code taken from: https://stackoverflow.com/questions/57014259/json-dumps-on-dictionary-with-bytes-for-keys
        def decode_dict(d):
            result = {}
            for key, value in d.items():
                if isinstance(key, bytes):
                    key = key.decode()
                if isinstance(value, bytes):
                    value = value.decode()
                elif isinstance(value, dict):
                    value = decode_dict(value)
                result.update({key: value})
            return result
        with open(cur_exp_path + 'instrument_configuration.txt', 'w') as outfile:
            raw_snapshot = self._station.snapshot_base()
            json.dump(decode_dict(raw_snapshot), outfile, indent=4)


    @staticmethod
    def _printProgressBar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 50, fill = '█', printEnd = "\r", prev_str=''):
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

        Adapted from: https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        #The \033[K%s is to erase the entire line instead of leaving stuff behind when the string gets smaller... Except that doesn't work in Jupyter
        #https://github.com/jupyter/notebook/issues/4749 - so back to using the manual erasure...
        print(' '*len(prev_str), end = printEnd)
        ret_str = f'\033[K%s\r{prefix} |{bar}| {percent}% {suffix}'
        print(ret_str, end = printEnd)
        # Print New Line on Complete
        if iteration == total: 
            print()
        return ret_str

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
        
        self._prog_bar_str = self._printProgressBar(int(val_pct*100), 100, suffix=f"{total_time}, {time_left}", prev_str=self._prog_bar_str)
