from sqdtoolz.HAL.HALbase import HALbase
from sqdtoolz.HAL.ZI.ZIbase import ZIbase
import laboneq.simple as lbeqs
from laboneq_applications.qpu_types.tunable_transmon import TunableTransmonQubit
import numpy as np

class ZIACQ(HALbase, ZIbase):
    def __init__(self, qubit_name, lab, instr_zi_boxes):
        HALbase.__init__(self, qubit_name)
        
        self._instr_id = instr_zi_boxes
        self._instr_zi = lab._get_instrument(instr_zi_boxes)
        if lab._register_HAL(self):
            #Options inspired by: https://github.com/zhinst/laboneq-applications/blob/main/src/laboneq_applications/experiments/qubit_spectroscopy.py
            #Options listed here: https://docs.zhinst.com/labone_q_user_manual/core/functionality_and_concepts/03_sections_pulses/concepts/04_averaging_sweeping.html
            self._zi_opts = {
                'count': 1024,
                'averaging_mode': "DEFAULT",
                'acquisition_type': "DEFAULT",
                #TODO: Consider adding RepetitionMode.FASTEST. For now 0 implies AUTO and >0 implies CONSTANT RepetitionTime
                'repetition_mode': lbeqs.RepetitionMode.AUTO,
                'repetition_time': 5e-6
            }
        self._cur_workflow = None

    @classmethod
    def fromConfigDict(cls, config_dict, lab):
        return cls(config_dict['Name'], lab, config_dict['instrument'])

    @property
    def NumRepetitions(self):
        return self._zi_opts['count']
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps: int):
        self._zi_opts['count'] = int(num_reps)

    @property
    def RepetitionTime(self):
        if self._zi_opts['repetition_mode'] == lbeqs.RepetitionMode.AUTO:
            return 0
        elif self._zi_opts['repetition_mode'] == lbeqs.RepetitionMode.CONSTANT:
            return self._zi_opts['repetition_time']
    @RepetitionTime.setter
    def RepetitionTime(self, rep_time: float):
        if rep_time == 0.0:
            self._zi_opts['repetition_mode'] = lbeqs.RepetitionMode.AUTO
        else:
            self._zi_opts['repetition_mode'] = lbeqs.RepetitionMode.CONSTANT
            self._zi_opts['repetition_time'] = float(rep_time)

    @property
    def AveragingOrder(self):
        if self._zi_opts['averaging_mode'] == lbeqs.AveragingMode.SEQUENTIAL:
            return "AverageBeforeSweep"
        elif self._zi_opts['averaging_mode'] == lbeqs.AveragingMode.CYCLIC:
            return "SweepBeforeAverage"
        elif self._zi_opts['averaging_mode'] == "DEFAULT":
            return "DEFAULT"
    @AveragingOrder.setter
    def AveragingOrder(self, averaging_mode: str):
        if averaging_mode == "AverageBeforeSweep":
            self._zi_opts['averaging_mode'] = lbeqs.AveragingMode.SEQUENTIAL
        elif averaging_mode == "SweepBeforeAverage":
            self._zi_opts['averaging_mode'] = lbeqs.AveragingMode.CYCLIC
        elif averaging_mode == "DEFAULT":
            self._zi_opts['averaging_mode'] = "DEFAULT"
        else:
            assert False, "AveragingOrder must be \'AverageBeforeSweep\', \'SweepBeforeAverage\' or \'DEFAULT\'"

    @property
    def AcquisitionMode(self):
        if self._zi_opts['acquisition_type'] == lbeqs.AcquisitionType.INTEGRATION:
            return "INTEGRATION"
        elif self._zi_opts['acquisition_type'] == lbeqs.AcquisitionType.RAW:
            return "RAW"
        elif self._zi_opts['acquisition_type'] == lbeqs.AcquisitionType.SPECTROSCOPY:
            return "SPECTROSCOPY"
        elif self._zi_opts['acquisition_type'] == lbeqs.AcquisitionType.SPECTROSCOPY_PSD:
            return "SPECTROSCOPY_PSD"
        elif self._zi_opts['acquisition_type'] == lbeqs.AcquisitionType.DISCRIMINATION:
            return "DISCRIMINATION"
        elif self._zi_opts['acquisition_type'] == "DEFAULT":
            return "DEFAULT"
    @AcquisitionMode.setter
    def AcquisitionMode(self, averaging_mode: str):
        if averaging_mode == "INTEGRATION":
            self._zi_opts['acquisition_type'] = lbeqs.AcquisitionType.INTEGRATION 
        elif averaging_mode == "RAW":
            self._zi_opts['acquisition_type'] = lbeqs.AcquisitionType.RAW 
        elif averaging_mode == "SPECTROSCOPY":
            self._zi_opts['acquisition_type'] = lbeqs.AcquisitionType.SPECTROSCOPY 
        elif averaging_mode == "SPECTROSCOPY_PSD":
            self._zi_opts['acquisition_type'] = lbeqs.AcquisitionType.SPECTROSCOPY_PSD 
        elif averaging_mode == "DISCRIMINATION":
            self._zi_opts['acquisition_type'] = lbeqs.AcquisitionType.DISCRIMINATION 
        elif averaging_mode == "DEFAULT":
            self._zi_opts['acquisition_type'] = "DEFAULT"
        else:
            assert False, "AcquisitionMode must be \'INTEGTRATION\', \'RAW\', \'SPECTROSCOPY\' (HW frequency sweep), \'SPECTROSCOPY_PSD\', \'DISCRIMINATION\' or \'DEFAULT\'"

    def get_ZI_parameters(self):
        return {x:self._zi_opts[x] for x in self._zi_opts if self._zi_opts[x] != "DEFAULT"}

    def _get_current_config(self):
        ret_dict = {
            'Name' : self.Name,
            'instrument' : self._instr_id,
            'Type' : self.__class__.__name__,
            'ManualActivation' : self.ManualActivation
            }
        self.pack_properties_to_dict(['NumRepetitions', 'RepetitionTime', 'AveragingOrder', 'AcquisitionMode'], ret_dict)
        return ret_dict

    def _set_current_config(self, dict_config, lab):
        assert dict_config['Type'] == self.__class__.__name__, 'Cannot set configuration to a ZI-Qubit with a configuration that is of type ' + dict_config['Type']
        self.ManualActivation = dict_config.get('ManualActivation', False)

        self.NumRepetitions = dict_config['NumRepetitions']
        self.RepetitionTime = dict_config['RepetitionTime']
        self.AveragingOrder = dict_config['AveragingOrder']
        self.AcquisitionMode = dict_config['AcquisitionMode']

        self._cur_workflow = None   #This will be called in init_instruments

    def get_data(self):
        assert self._cur_workflow != None, "ZIACQ must not be in a CONFIG run in a non-ZI compatible experiment. For example, ExpZIqubit would be fine."
        workflow_results = self._cur_workflow.run()
        datasets = [x for x in workflow_results.output.data._prefixes]
        #Basically store in secondary datasets while leaving data.h5 blank...
        ret_val = {'data': {
                    'parameters' : ['r'],
                    'data' : {'a':np.array([0])},
                    'misc' : {}
                }}
        for cur_dataset in datasets:
            cur_res = workflow_results.output.data[datasets[0]].result
            ret_val[cur_dataset] = {
                    'parameters' : cur_res.axis_name,
                    'data' : {},
                    'parameter_values': {}
                }
            for m,cur_axis in enumerate(cur_res.axis_name):
                ret_val[cur_dataset]['parameter_values'][cur_axis] = cur_res.axis[m]
            if cur_res.data.dtype == np.complex128:
                ret_val[cur_dataset]['data'] = {'real': np.real(cur_res.data), 'imag': np.imag(cur_res.data)}  #TODO: Need to revisit this for discriminated datasets?
            else:
                ret_val[cur_dataset]['data'] = {'values': cur_res}

        return ret_val


    def _get_ZI_session(self):
        return lbeqs.Session(self._instr_zi.device_setup)

