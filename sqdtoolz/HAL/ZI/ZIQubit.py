from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.HAL.ZI.ZIbase import ZIbase
import laboneq.simple as lbeqs
from laboneq_applications.qpu_types.tunable_transmon import TunableTransmonQubit

class ZIQubit(HALbase, ZIbase):
    def __init__(self, qubit_name, lab, instr_zi_boxes, zi_instr_phys_drive:tuple[str, str], zi_instr_phys_measure:tuple[str, str], zi_instr_phys_acquire:tuple[str, str], zi_phys_flux=("",""), zi_type="TunableTransmonQubit"):
        HALbase.__init__(self, qubit_name)
        
        lab._register_HAL(self)
        self._instr_zi = lab._get_instrument(instr_zi_boxes)
        self._zi_instr_phys_drive = zi_instr_phys_drive
        self._zi_instr_phys_measure = zi_instr_phys_measure
        self._zi_instr_phys_acquire = zi_instr_phys_acquire
        self._zi_instr_phys_flux = zi_phys_flux

        allowed_qubit_types = ["TunableTransmonQubit"]
        assert zi_type in allowed_qubit_types, f"Qubit type must be any of: {allowed_qubit_types}"

        self._setup_zi_connections()
        self._setup_zi_qubit(zi_type)

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict['Name'], lab, config_dict['instrument'],
                   config_dict['ZI_phys_drive'],
                   config_dict['ZI_phys_measure'],
                   config_dict['ZI_phys_acquire'],
                   config_dict.get('ZI_phys_flux', ("",""),
                   config_dict['ZI_qubit_type']))

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        elif '_param_mappings' in self.__dict__ and name in self._param_mappings:
            return getattr(self._zi_qubit.parameters, self._param_mappings[name])
        else:
            raise AttributeError(f"The ZIQubit object does not have an attribute/property '{name}'")

    def __setattr__(self, name, value):
        if '_param_mappings' in self.__dict__ and name in self._param_mappings:
            return setattr(self._zi_qubit.parameters, self._param_mappings[name], value)
        else:
            self.__dict__[name] = value

    def _setup_zi_connections(self):
        #Collate required connections
        conns = []
        conns.append((self._zi_instr_phys_measure[0], lbeqs.create_connection(to_signal=f"{qubit_name}/measure", ports=self._zi_instr_phys_measure[1], type="iq"), "measure"))
        conns.append((self._zi_instr_phys_acquire[0], lbeqs.create_connection(to_signal=f"{qubit_name}/acquire", ports=self._zi_instr_phys_acquire[1], type="acquire"), "acquire"))
        conns.append((self._zi_instr_phys_drive[0], lbeqs.create_connection(to_signal=f"{qubit_name}/drive", ports=self._zi_instr_phys_drive[1], type="iq"), "drive"))
        if self._zi_phys_flux[0] != "":
            conns.append((self._zi_phys_flux[0], lbeqs.create_connection(to_signal=f"{qubit_name}/flux", ports=self._zi_phys_flux[1], type="rf"), "flux"))

        #Initialise or redo connections
        for cur_connection in conns:
            #Check if connection already exists by this name
            found = -1
            if isinstance(self._instr_zi.device_setup.instrument_by_uid(cur_connection[0]).connections, (list, tuple)):
                for m,conns_in_device in enumerate(self._instr_zi.device_setup.instrument_by_uid(cur_connection[0]).connections):
                    if len(conns_in_device.remote_path) > 23 and conns_in_device.remote_path[23:]==cur_connection[1].uid:
                        found = m
                        break
            #Remove connection if it already exists
            if found != -1:
                cur_conn = self._instr_zi.device_setup.instrument_by_uid(cur_connection[0]).connections.pop(m)
                #Ignore the / and logical_signal_groups/ in the beginning. There shouldn't be anything but the line-name left; e.g. LabOneQ doesn't allow Qubits/Qubit1/measure
                self._instr_zi.device_setup.logical_signal_groups[qubit_name].logical_signals.pop(cur_connection[2])
            #
            self._instr_zi.device_setup.add_connections(cur_connection[0], cur_connection[1])

    def _setup_zi_qubit(self, qubit_type):
        #Only recreate the ZI Qubit object if the qubit type has changed or doesn't exist yet
        if hasattr(self, "qubit_type"):
            if self._qubit_type != qubit_type:
                print(f"Warning: The qubit type for {qubit_name} has changed from {self._qubit_type} to {qubit_type}. The qubit parameters will now be erased and reset!")  #TODO: Maybe look into transferrable ones later?
                self._qubit_type = qubit_type
            else:
                return
        else:
            self._qubit_type = qubit_type

        if self._qubit_type == "TunableTransmonQubit":
            self._zi_qubit = TunableTransmonQubit.from_device_setup(self._instr_zi.device_setup, qubit_uids=[self.Name])[0]
            self._zi_qubit.parameters.ge_drive_pulse["sigma"] = 0.25
            self._zi_qubit.parameters.readout_range_out = -10

            self._param_mappings = {
                'DriveLO':'drive_lo_frequency',
                'DriveGE':'resonance_frequency_ge',
                'DriveEF':'resonance_frequency_ef',
                'DriveGEAmplitudeX':'ge_drive_amplitude_pi',
                'DriveGEAmplitudeXon2':'ge_drive_amplitude_pi2',
                'DriveGETime':'ge_drive_length',
                'DriveGEPulse':'ge_drive_pulse',
                'DriveEFAmplitudeX':'ef_drive_amplitude_pi',
                'DriveEFAmplitudeXon2':'ef_drive_amplitude_pi2',
                'DriveEFTime':'ef_drive_length',
                'DriveEFPulse':'ef_drive_pulse',
                'ReadoutLO':'readout_lo_frequency',
                'ReadoutFrequency':'readout_resonator_frequency',
                'ReadoutAmplitude':'readout_amplitude',
                'ReadoutTime':'readout_length',
                'ReadoutPad':'readout_integration_delay',
                'ResetTime':'reset_delay_length',
                'T1GE':'ge_T1',
                'T2GE':'ge_T2',
                'T2*GE':'ge_T2_star',
                'T1EF':'ef_T1',
                'T2EF':'ef_T2',
                'T2*EF':'ef_T2_star'
            }

            #Setup some default values
            #TODO: Review if this even needs to be done?
            self.ReadoutAmplitude = 0.1
            self.ResetTime = 10e-6
            self.ReadoutLO = 7e9

            self._zi_qops = TunableTransmonOperations()

    def get_ZI_parameters(self):
        return self._zi_qubit, self._zi_qops

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_zi,
            'Type' : self.__class__.__name__,
            'ManualActivation' : self.ManualActivation,
            'ZI_phys_drive' : self._zi_instr_phys_drive,
            'ZI_phys_measure' : self._zi_instr_phys_measure,
            'ZI_phys_acquire' : self._zi_instr_phys_acquire,
            'ZI_phys_flux' : self._zi_instr_phys_flux,
            'ZI_qubit_type' : self._qubit_type
            }
        for cur_param in self._param_mappings:
            ret_dict[cur_param] = getattr(self, cur_param)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a ZI-Qubit with a configuration that is of type ' + dict_config['Type']
        self.ManualActivation = dict_config.get('ManualActivation', False)

        self._zi_instr_phys_drive = dict_config['ZI_phys_drive']
        self._zi_instr_phys_measure = dict_config['ZI_phys_measure']
        self._zi_instr_phys_acquire = dict_config['ZI_phys_acquire']
        self._zi_instr_phys_flux = dict_config['ZI_phys_flux']
        self._qubit_typ = dict_config['ZI_qubit_type']

        self._setup_zi_connections()
        self._setup_zi_qubit(dict_config['ZI_qubit_type'])
