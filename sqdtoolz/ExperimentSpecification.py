from sqdtoolz.Variable import*
import json

import importlib.resources as pkg_resources
from sqdtoolz import ExperimentSpecifications


class ExperimentSpecification:
    def __init__(self, name, lab, init_specs = ""):
        self._name = name
        self._lab = lab
        if lab._register_SPEC(self):
            self._cur_mappings = {}
        if init_specs != "":
            data = pkg_resources.read_text(ExperimentSpecifications, init_specs + '.json')
            data = json.loads(data)
            for cur_key in data:
                self.add(cur_key, data[cur_key])

    def __new__(cls, *args, **kwargs):
        if len(args) == 0:
            name = kwargs.get('name', '')
        else:
            name = args[0]
        assert isinstance(name, str) and name != '', "Name parameter was not passed or does not exist as the first argument in the ExperimentSpecification initialisation?"
        if len(args) < 2:
            lab = kwargs.get('lab', None)
        else:
            lab = args[1]
        assert lab.__class__.__name__ == 'Laboratory' and lab != None, "Lab parameter was not passed or does not exist as the second argument in the ExperimentSpecification initialisation?"

        prev_exists = lab.SPEC(name)
        if prev_exists:
            return prev_exists
        else:
            return super(cls.__class__, cls).__new__(cls)
    
    @property
    def Name(self):
        return self._name

    @property
    def Parent(self):
        return None

    def add(self, entry_name, value, dest_obj = None, dest_prop_name = ""):
        self._cur_mappings[entry_name] = {'Value' : value, 'Destination' : self._lab._resolve_sqdobj_tree(dest_obj), 'Property' : dest_prop_name}
    
    def set_destination(self, entry_name, dest_obj, dest_prop_name = ""):
        if isinstance(dest_obj, VariableBase):
            dest_prop_name = 'Value'
        self._cur_mappings[entry_name]['Destination'] = self._lab._resolve_sqdobj_tree(dest_obj)
        self._cur_mappings[entry_name]['Property'] = dest_prop_name

    def __getitem__(self, key):
        assert key in self._cur_mappings, f"Entry \'{key}\' does not exist and must first be added via the \'add\' function."
        return self._cur_mappings[key]['Value']
    
    def __setitem__(self, key, value):
        assert key in self._cur_mappings, f"Entry \'{key}\' does not exist and must first be added via the \'add\' function."
        self._cur_mappings[key]['Value'] = value
    
    def commit_entries(self):
        for cur_entry in self._cur_mappings:
            if len(self._cur_mappings[cur_entry]['Destination']) == 0:
                continue
            obj = self._lab._get_resolved_obj(self._cur_mappings[cur_entry]['Destination'])
            if obj != None:
                setattr(obj, self._cur_mappings[cur_entry]['Property'], self._cur_mappings[cur_entry]['Value'])
    
    def _get_current_config(self):
        return {
            'Name' : self._name,
            'Entries' : self._cur_mappings
        }
    
    def _set_current_config(self, config_dict):
        self._cur_mappings = config_dict['Entries']
