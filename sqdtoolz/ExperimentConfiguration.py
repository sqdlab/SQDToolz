from sqdtoolz.HAL.TriggerPulse import*
from sqdtoolz.Utilities.TimingPlots import*
import numpy as np
import json

class ExperimentConfiguration:
    def __init__(self, name, lab, duration, list_HALs, hal_ACQ):
        self._name = name
        #Just register it to the labotarory - doesn't matter if it already exists as everything here needs to be reinitialised
        #to the new configuration anyway...
        lab._register_CONFIG(self)

        self._total_time = duration

        #Hard links are O.K. as the HAL objects won't get replaced on reinitialisation due to the design of __new__ in the Halbase
        #class. In addition, cold-restarts should have the strings properly instantiating the HALs once anyway. Nonetheless, the
        #update function will work with the laboratory class...
        self._lab = lab
        self._list_HALs = list_HALs[:]
        self._hal_ACQ = hal_ACQ

        self._dict_wfm_map = {'waveforms' : {}, 'digital' : {} }

        self._settle_currently_used_processors()
        
        self._init_config = self.save_config()

    def __new__(cls, *args, **kwargs):
        if len(args) == 0:
            name = kwargs.get('name', '')
        else:
            name = args[0]
        assert isinstance(name, str) and name != '', "Name parameter was not passed or does not exist as the first argument in the variable class initialisation?"
        if len(args) < 2:
            lab = kwargs.get('lab', None)
        else:
            lab = args[1]
        assert lab.__class__.__name__ == 'Laboratory' and lab != None, "Lab parameter was not passed or does not exist as the second argument in the variable class initialisation?"

        prev_exists = lab.CONFIG(name)
        if prev_exists:
            return prev_exists
        else:
            return super(cls.__class__, cls).__new__(cls)

    @property
    def Name(self):
        return self._name

    @property
    def RepetitionTime(self):
        return self._total_time
    @RepetitionTime.setter
    def RepetitionTime(self, len_seconds):
        self._total_time = len_seconds

    def _settle_currently_used_processors(self):
        self._proc_configs = []
        if self._hal_ACQ:
            self._proc = self._hal_ACQ.data_processor
            if self._proc:
                self._proc_configs = [self._proc]

    def get_config(self):
        return self._init_config

    def save_config(self, file_name = ''):
        cur_config = {'HALs' : [], 'PROCs' : [], 'RepetitionTime' : self.RepetitionTime, 'WaveformMapping' : self._dict_wfm_map}

        #Prepare the dictionary of HAL configurations
        for cur_hal in self._list_HALs + [self._hal_ACQ]:
            cur_config['HALs'].append(cur_hal._get_current_config())

        for cur_proc in self._proc_configs:
            cur_config['PROCs'].append(cur_proc._get_current_config())

        #Save to file if necessary
        if (file_name != ''):
            with open(file_name, 'w') as outfile:
                json.dump(cur_config, outfile, indent=4)
        return cur_config

    def update_config(self, conf):
        #TODO: Check if these checks here are probably overkill and possibly obsolete?
        for cur_dict in conf['HALs']:
            found_hal = False
            for cur_hal in self._list_HALs + [self._hal_ACQ]:
                if cur_hal.Name == cur_dict['Name']:
                    found_hal = True
                    cur_hal._set_current_config(cur_dict, self._lab)
                    break
            assert found_hal, f"HAL object {cur_dict['Name']} does not exist in the current ExperimentConfiguration object."
        self._settle_currently_used_processors()
        for cur_dict in conf['PROCs']:
            found_proc = False
            for cur_proc in self._proc_configs:
                if cur_proc.Name == cur_dict['Name']:
                    found_proc = True
                    cur_proc._set_current_config(cur_dict, self._lab)
                    break
            assert found_proc, f"PROC object {cur_dict['Name']} does not exist in the current ExperimentConfiguration object."
        self.RepetitionTime = conf['RepetitionTime']
        self._dict_wfm_map = conf['WaveformMapping'] 
        #
        self._init_config = conf

    def map_waveforms(self, map_dict):
        self._dict_wfm_map = map_dict
        #Convert marker objects into guids...
        if 'digital' in self._dict_wfm_map:
            for cur_dig in self._dict_wfm_map['digital']:
                self._dict_wfm_map['digital'][cur_dig] = self._lab._resolve_sqdobj_tree(self._dict_wfm_map['digital'][cur_dig])

    def update_waveforms(self, wfm_gen):
        #Settle the actual waveforms first
        for cur_wave in  wfm_gen.waveforms:
            assert cur_wave in self._dict_wfm_map['waveforms'], f"There is no mapping for waveform {cur_wave}"
            awg_hal = None
            for cur_hal in self._list_HALs:
                if self._dict_wfm_map['waveforms'][cur_wave] == cur_hal.Name:
                    awg_hal = cur_hal
                    break
            assert awg_hal != None, f"The AWG waveform HAL {self._dict_wfm_map['waveforms'][cur_wave]} does not exist in this Experiment Configuration."
            awg_hal.set_waveform_segments(wfm_gen.waveforms[cur_wave])
            awg_hal.null_all_markers()
        #Now settle the output markers
        for cur_dig in wfm_gen.digitals:
            assert cur_dig in self._dict_wfm_map['digital'], f"There is no mapping for digital waveform {cur_wave}"
            if 'refWaveform' in wfm_gen.digitals[cur_dig]:
                pass
                cur_mkr = self._lab._get_resolved_obj(self._dict_wfm_map['digital'][cur_dig])

                cur_mkr_awg = self._dict_wfm_map['digital'][cur_dig][0][0]
                cur_ref_awg = self._dict_wfm_map['waveforms'][ wfm_gen.digitals[cur_dig]['refWaveform'] ]
                if cur_mkr_awg == cur_ref_awg:
                    cur_mkr.set_markers_to_segments(wfm_gen.digitals[cur_dig]['segments'])
                else:
                    mkr_wfm = self._lab.HAL(cur_ref_awg)._get_marker_waveform_from_segments(wfm_gen.digitals[cur_dig]['segments'])
                    assert mkr_wfm.size == self._lab.HAL(cur_mkr_awg).NumPts, "When setting a marker on a given waveform using reference segments from another waveforms, the two waveforms must be the same size."
                    cur_mkr.set_markers_to_arbitrary(mkr_wfm)
            else:
                cur_trig = self._lab._get_resolved_obj(self._dict_wfm_map['digital'][cur_dig])
                cur_trig.set_markers_to_trigger()
                cur_trig.TrigPulseDelay = wfm_gen.digitals[cur_dig]['trig_delay']
                cur_trig.TrigPulseLength = wfm_gen.digitals[cur_dig]['trig_length']
                cur_trig.TrigPolarity = wfm_gen.digitals[cur_dig]['trig_polarity']

    def init_instruments(self):
        self.update_config(self._init_config)

    def prepare_instruments(self):
        for cur_hal in self._list_HALs:
            if not cur_hal.ManualActivation:
                cur_hal.activate()

        #TODO: Write rest of this with error checking
        list_hals = self._list_HALs + [self._hal_ACQ]
        for cur_hal in list_hals:
            #TODO: Write concurrence/change checks to better optimise AWG...
            cur_hal.prepare_initial()
        for cur_hal in list_hals:
            cur_hal.prepare_final()

    def makesafe_instruments(self):
        for cur_hal in self._list_HALs:
            if not cur_hal.ManualActivation:
                cur_hal.deactivate()

    def get_data(self):
        #TODO: Pack the data appropriately if using multiple ACQ objects (coordinating their starts/finishes perhaps?)
        cur_acq = self._hal_ACQ
        return cur_acq.get_data()

    def get_trigger_edges(self, obj_trigger_input):
        assert isinstance(obj_trigger_input, TriggerInput), "The argument obj_trigger_input must be a TriggerInput object; that is, a genuine digital trigger input."

        cur_trig_srcs = []
        cur_input = obj_trigger_input
        cur_trig = obj_trigger_input._get_instr_trig_src()
        while(cur_trig != None):
            assert not (cur_trig in cur_trig_srcs),  "There is a cyclic dependency on the trigger sources. Look carefully at the HAL objects in play."
            cur_trig_srcs += [(cur_trig, cur_input._get_instr_input_trig_edge())]
            cur_input = cur_trig
            if isinstance(cur_trig._get_parent_HAL(), TriggerInputCompatible):
                cur_trig = cur_trig._get_instr_trig_src()
            else:
                break   #The tree had ended and this device is the root source...
            
        #Now spawn the tree of trigger times
        #TODO: Add error-checking to ensure the times do not overlap...
        all_times = np.array([])
        cur_gated_segments = np.array([])
        for cur_trig in cur_trig_srcs[::-1]:    #Start from the top of the tree...
            #Get the trigger times emitted by the current source cur_trig[0] given the input polarity cur_trig[1]
            cur_times, cur_gated_segments = cur_trig[0].get_trigger_times(cur_trig[1])
            cur_times = np.array(cur_times)
            if (len(all_times) == 0):
                all_times = cur_times
            else:
                #Translate the current trigger edges by the previous trigger edges
                cur_gated_segments = np.concatenate( [cur_gated_segments + prev_time for prev_time in all_times] )
                all_times = np.concatenate( [cur_times + prev_time for prev_time in all_times] )
        return (all_times, cur_gated_segments)

    def plot(self):
        '''
        Generate a representation of the timing configuration with matplotlib.
        
        Output:
            (Figure) matplotlib figure showing the timing configuration
        '''

        if self._total_time < 2e-6:
            scale_fac = 1e9
            plt_units = 'ns'
        elif self._total_time < 2e-3:
            scale_fac = 1e6
            plt_units = 'us'
        elif self._total_time < 2:
            scale_fac = 1e3
            plt_units = 'ms'
        else:
            scale_fac = 1
            plt_units = 's'

        tp = TimingPlot()

        disp_objs = []
        for cur_hal in self._list_HALs + [self._hal_ACQ]:
            if isinstance(cur_hal, TriggerInputCompatible):
                disp_objs += cur_hal._get_all_trigger_inputs()
            elif isinstance(cur_hal, TriggerOutputCompatible):
                disp_objs += [cur_hal._get_trigger_output_by_id(x) for x in cur_hal._get_all_trigger_outputs()]

        for cur_obj in disp_objs[::-1]:
            if isinstance(cur_obj, TriggerInput):
                trig_times, seg_times = self.get_trigger_edges(cur_obj)
            else:
                #TODO: Flag the root sources in diagram?
                trig_times = np.array([0.0])
                seg_times = np.array([])
            cur_diag_info = cur_obj._get_timing_diagram_info()
            if cur_diag_info['Type'] == 'None':
                continue
            
            tp.goto_new_row(cur_obj.Name)

            if cur_diag_info['Type'] == 'BlockShaded':
                if cur_diag_info['TriggerType'] == 'Gated':
                    if seg_times.size == 0:
                        continue
                    for cur_trig_seg in seg_times:
                        cur_trig_start = cur_trig_seg[0] * scale_fac
                        cur_len = (cur_trig_seg[1]-cur_trig_seg[0]) * scale_fac
                        tp.add_rectangle(cur_trig_start, cur_trig_start + cur_len)
                else:
                    for cur_trig_time in trig_times:
                        cur_trig_start = cur_trig_time * scale_fac
                        cur_len = cur_diag_info['Period'] * scale_fac
                        tp.add_rectangle(cur_trig_start, cur_trig_start + cur_len)
            elif cur_diag_info['Type'] == 'DigitalSampled':
                for cur_trig_time in trig_times:
                    cur_trig_start = cur_trig_time * scale_fac
                    mkrs, sample_rate = cur_diag_info['Data']
                    assert mkrs.size > 0, "Digital sampled pulse waveform is empty when plotting the timing diagram. Ensure _get_timing_diagram_info properly returns \'Type\' as \'None\' if inactive/empty..."
                    tp.add_digital_pulse_sampled(mkrs, cur_trig_start, scale_fac/sample_rate)
            elif cur_diag_info['Type'] == 'DigitalEdges':
                for cur_trig_time in trig_times:
                    cur_trig_start = cur_trig_time * scale_fac
                    pts = cur_diag_info['Data']
                    assert len(pts) > 0 and pts[0][0] == 0.0, "Digital pulse waveform must be non-empty and start with t=0.0 when plotting the timing diagram."
                    tp.add_digital_pulse(pts, cur_trig_start, scale_fac)
            elif cur_diag_info['Type'] == 'AnalogueSampled':
                for cur_trig_time in trig_times:
                    cur_trig_start = cur_trig_time * scale_fac
                    #Loop over all the waveform segments
                    cur_seg_x = cur_trig_start
                    for cur_wfm_dict in cur_diag_info['Data']:
                        cur_dur = cur_wfm_dict['Duration']*scale_fac
                        tp.add_rectangle_with_plot(cur_seg_x, cur_seg_x + cur_dur, cur_wfm_dict['yPoints'])
                        cur_seg_x += cur_dur
            else:
                assert False, "The \'Type\' key in the dictionary returned on calling the function _get_timing_diagram_info is invalid."

        return tp.finalise_plot(self._total_time*scale_fac, plt_units, f'Configuration: {self.Name}')
