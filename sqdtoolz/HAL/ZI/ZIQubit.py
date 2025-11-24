from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.HAL.ZI.ZIbase import ZIbase
import laboneq.simple as lbeqs
from laboneq_applications.qpu_types.tunable_transmon import TunableTransmonQubit, TunableTransmonOperations

class ZIQubit(HALbase, ZIbase):
    def __init__(self, qubit_name, lab, instr_zi_boxes, zi_instr_phys_drive:tuple[str, str], zi_instr_phys_measure:tuple[str, str], zi_instr_phys_acquire:tuple[str, str], zi_phys_flux=("",""), zi_type="TunableTransmonQubit"):
        HALbase.__init__(self, qubit_name)
        
        lab._register_HAL(self)
        self._instr_id = instr_zi_boxes
        self._instr_zi = lab._get_instrument(instr_zi_boxes)
        self._zi_instr_phys_drive = zi_instr_phys_drive
        self._zi_instr_phys_measure = zi_instr_phys_measure
        self._zi_instr_phys_acquire = zi_instr_phys_acquire
        self._zi_instr_phys_flux = zi_phys_flux

        allowed_qubit_types = ["TunableTransmonQubit"]
        assert zi_type in allowed_qubit_types, f"Qubit type must be any of: {allowed_qubit_types}"

        self._flux_dc = 0
        self._flux_cal_obj = None

        self._setup_zi_connections()
        self._setup_zi_qubit(zi_type)


    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict['Name'], lab, config_dict['instrument'],
                   config_dict['ZI_phys_drive'],
                   config_dict['ZI_phys_measure'],
                   config_dict['ZI_phys_acquire'],
                   config_dict.get('ZI_phys_flux', ("","")),
                   config_dict['ZI_qubit_type'])

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        elif '_param_mappings' in self.__dict__ and name in self._param_mappings:
            if name == 'FluxDC':
                if self._flux_cal_obj != None:
                    return self._flux_cal_obj.voltage_offset
                else:
                    return self._flux_dc
            return getattr(self._zi_qubit.parameters, self._param_mappings[name])
        elif '_param_mappings_local' in self.__dict__ and name in self._param_mappings_local:
            return self._param_mappings_local[name]
        else:
            raise AttributeError(f"The ZIQubit object does not have an attribute/property '{name}'")

    def __setattr__(self, name, value):
        if '_param_mappings' in self.__dict__ and name in self._param_mappings:
            if name == 'ReadoutPower':
                assert value >= -30 and value <= 10 and value % 5 == 0, "ReadoutPower must be within [-30dBm,10dBm] in steps of 5dB"
            if name == 'DrivePower':
                assert value >= -30 and value <= 10 and value % 5 == 0, "DrivePower must be within [-30dBm,10dBm] in steps of 5dB"
            if name == 'FluxDC':
                self._flux_dc = value
                if self._zi_instr_phys_flux != "":
                    setattr(self._zi_qubit.parameters, self._param_mappings[name], value)
                    self._instr_zi.device_setup.set_calibration(self._zi_qubit.calibration())
                    lbeqs.Session(self._instr_zi.device_setup).connect(do_emulation=False)
            setattr(self._zi_qubit.parameters, self._param_mappings[name], value)
        elif '_param_mappings_local' in self.__dict__ and name in self._param_mappings_local:
            self._param_mappings_local[name] = value
        else:
            self.__dict__[name] = value

    def _setup_zi_connections(self):
        #Collate required connections
        conns = []
        qubit_name = self.Name
        conns.append((self._zi_instr_phys_measure[0], lbeqs.create_connection(to_signal=f"{qubit_name}/measure", ports=self._zi_instr_phys_measure[1], type="iq"), "measure"))
        conns.append((self._zi_instr_phys_acquire[0], lbeqs.create_connection(to_signal=f"{qubit_name}/acquire", ports=self._zi_instr_phys_acquire[1], type="acquire"), "acquire"))
        conns.append((self._zi_instr_phys_drive[0], lbeqs.create_connection(to_signal=f"{qubit_name}/drive", ports=self._zi_instr_phys_drive[1], type="iq"), "drive"))
        if self._zi_instr_phys_flux[0] != "":
            conns.append((self._zi_instr_phys_flux[0], lbeqs.create_connection(to_signal=f"{qubit_name}/flux", ports=self._zi_instr_phys_flux[1], type="rf"), "flux"))

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

        #For the flux line, just initialise it so that voltage offsets can be set etc...
        if self._zi_instr_phys_flux[0] != "":
            self._instr_zi.device_setup.set_calibration(lbeqs.Calibration({self._instr_zi.device_setup.logical_signal_groups[f"{qubit_name}"].logical_signals["flux"].path: lbeqs.SignalCalibration(delay_signal=0, voltage_offset=0.0) }))

    def _setup_zi_qubit(self, qubit_type):
        #Only recreate the ZI Qubit object if the qubit type has changed or doesn't exist yet
        if hasattr(self, "_qubit_type"):
            if self._qubit_type != qubit_type:
                qubit_name = self.Name
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

            self._param_mappings_local = {
                'ReadoutQi': 1,
                'ReadoutQc': 1,
                'ReadoutQl': 1
            }

            self._param_mappings = {
                'DriveLO':'drive_lo_frequency',
                'DrivePower':'drive_range',
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
                'ReadoutPower':'readout_range_out',
                'ReadoutFrequency':'readout_resonator_frequency',
                'ReadoutAmplitude':'readout_amplitude',
                'ReadoutTime':'readout_length',
                'ReadoutPad':'readout_integration_delay',
                'ResetTime':'reset_delay_length',
                'T1GE':'ge_T1',
                'T2GE':'ge_T2',
                'T2GE_star':'ge_T2_star',
                'T1EF':'ef_T1',
                'T2EF':'ef_T2',
                'T2EF_star':'ef_T2_star',
                'FluxDC': 'flux_offset_voltage'
            }

            #Setup some default values
            #TODO: Review if this even needs to be done?
            self.ReadoutAmplitude = 0.1
            self.ResetTime = 10e-6
            self.ReadoutLO = 7e9
            self.ReadoutPower = -10
            #TODO: Check again; it appears these need to be set for otherwise it's a NoneType and throws an error upon experiment execution...
            self.DriveLO = 5e9
            self.DriveGE = 5.2e9
            self.DriveEF = 5.1e9
            self.ReadoutFrequency = 7.0e9

            self._zi_qops = TunableTransmonOperations()

    def get_ZI_parameters(self):
        return self._zi_qubit, self._zi_qops

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
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
        for cur_param in self._param_mappings_local:
            ret_dict[cur_param] = getattr(self, cur_param)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config.pop('Type') == self.__class__.__name__, 'Cannot set configuration to a ZI-Qubit with a configuration that is of type ' + dict_config['Type']
        self.ManualActivation = dict_config.pop('ManualActivation', False)
        dict_config.pop('instrument')
        dict_config.pop('Name')

        self._zi_instr_phys_drive = dict_config.pop('ZI_phys_drive')
        self._zi_instr_phys_measure = dict_config.pop('ZI_phys_measure')
        self._zi_instr_phys_acquire = dict_config.pop('ZI_phys_acquire')
        self._zi_instr_phys_flux = dict_config.pop('ZI_phys_flux')
        self._qubit_type = dict_config.pop('ZI_qubit_type')

        self._setup_zi_connections()
        self._setup_zi_qubit(self._qubit_type)
        
        for cur_param in dict_config:
            setattr(self, cur_param, dict_config[cur_param])
