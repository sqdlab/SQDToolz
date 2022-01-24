from calendar import c
from sqdtoolz.Variable import*
import json

import importlib.resources as pkg_resources
from sqdtoolz import ExperimentSpecifications


class ExperimentSpecification:
    class _key_value_item:
        def __init__(self, exp_spec, prop_name):
            self._exp_spec = exp_spec
            self._prop_name = prop_name

        @property
        def Value(self):
            return self._exp_spec._cur_mappings[self._prop_name]['Value']
        @Value.setter
        def Value(self, val):
            self._exp_spec._cur_mappings[self._prop_name]['Value'] = val


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
        assert entry_name in self._cur_mappings, f"Entry \'{entry_name}\' does not exist and must first be added via the \'add\' function."
        if isinstance(dest_obj, VariableBase):
            dest_prop_name = 'Value'
        self._cur_mappings[entry_name]['Destination'] = self._lab._resolve_sqdobj_tree(dest_obj)
        self._cur_mappings[entry_name]['Property'] = dest_prop_name

    def __getitem__(self, key):
        assert key in self._cur_mappings, f"Entry \'{key}\' does not exist and must first be added via the \'add\' function."
        return self._key_value_item(self, key)
    
    def commit_entries(self):
        for cur_entry in self._cur_mappings:
            if len(self._cur_mappings[cur_entry]['Destination']) == 0:
                continue
            obj = self._lab._get_resolved_obj(self._cur_mappings[cur_entry]['Destination'])
            if obj != None:
                setattr(obj, self._cur_mappings[cur_entry]['Property'], self._cur_mappings[cur_entry]['Value'])

    def _get_targets(self):
        ret_targets = []
        for cur_entry in self._cur_mappings:
            if len(self._cur_mappings[cur_entry]['Destination']) == 0:
                continue
            cur_obj_type = self._cur_mappings[cur_entry]['Destination'][0][1]
            if cur_obj_type == 'VAR':
                ret_targets += self._lab._get_resolved_obj(self._cur_mappings[cur_entry]['Destination'])._get_written_targets()
            else:
                ret_targets += [(self._cur_mappings[cur_entry]['Destination'], self._cur_mappings[cur_entry]['Property'])]
        return ret_targets

    def __str__(self):
        cur_str = ""
        cur_str = f"Name: {self.Name}\n"
        cur_str = f"Entries:\n"
        for cur_key in self._cur_mappings:
            cur_str += f"\t{cur_key}: {self._cur_mappings[cur_key]['Value']}"
            if len(self._cur_mappings[cur_key]['Destination']) > 0:
                cur_str += f", {self._cur_mappings[cur_key]['Destination'] + [self._cur_mappings[cur_key]['Property']]}"
            cur_str += f"\n"
        return cur_str
    
    def _get_current_config(self):
        return {
            'Name' : self._name,
            'Entries' : self._cur_mappings
        }
    
    def _set_current_config(self, config_dict):
        self._cur_mappings = config_dict['Entries']
