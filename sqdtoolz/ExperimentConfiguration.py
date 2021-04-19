from sqdtoolz.HAL.TriggerPulse import*
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import json

class ExperimentConfiguration:
    def __init__(self, duration, list_HALs, hal_ACQ):
        self._total_time = duration
        self._list_HALs = list_HALs[:]
        self._hal_ACQ = hal_ACQ
        
        #Trigger relations formatted as tuples of the form: destination HAL or channel-HAL object, source Trigger object, input polarity on destination HAL object
        self._cur_trig_rels = self._get_current_trigger_relations()

    @property
    def RepetitionTime(self):
        return self._total_time
    @RepetitionTime.setter
    def RepetitionTime(self, len_seconds):
        self._total_time = len_seconds

    def _get_current_trigger_relations(self):
        trig_src_list = [x for x in self._list_HALs if isinstance(x, TriggerOutputCompatible)]
        trig_dest_list = [x for x in self._list_HALs + [self._hal_ACQ] if isinstance(x, TriggerInputCompatible)]

        def check_and_add_trig_src_to_list(cur_dest):
            cur_trig_src = cur_dest._get_instr_trig_src()
            if cur_trig_src:
                #TODO: Make the TriggerOutput objects have a __str__ to get the actual trigger source as a string
                assert cur_trig_src._get_parent_HAL() in trig_src_list, f"The trigger source \"{cur_trig_src._get_parent_HAL().Name}\" does not exist in the current ExperimentConfiguration!"
                check_and_add_trig_src_to_list.trig_rels += [(cur_dest, cur_trig_src, cur_dest._get_instr_input_trig_edge())]
        check_and_add_trig_src_to_list.trig_rels = []

        for cur_dest_trig in trig_dest_list:
            for cur_trig_input in cur_dest_trig._get_all_trigger_inputs():
                check_and_add_trig_src_to_list(cur_trig_input)

        return check_and_add_trig_src_to_list.trig_rels

    def save_config(self, file_name = ''):
        #Prepare the dictionary of HAL configurations
        retVal = []
        #Get the dictionaries for the DDGs
        for cur_ddg in self._list_DDGs:
            retVal.append(cur_ddg._get_current_config())
        #Get the dictionaries for the AWGs
        for cur_awg in self._list_AWGs:
            retVal.append(cur_awg._get_current_config())
        #Get the dictionaries and triggers for ACQ
        if (self._instr_ACQ):
            cur_acq = self._instr_ACQ
            retVal.append(cur_acq._get_current_config())
        #Get the dictionaries for generic HALs
        for cur_gen in self._list_GENs:
            retVal.append(cur_gen._get_current_config())
        
        #Save to file if necessary
        if (file_name != ''):
            with open(file_name, 'w') as outfile:
                json.dump(retVal, outfile, indent=4)
        return retVal

    def update_config(self, conf):
        #
        #Load the module parameters
        #
        trig_relations = []
        for cur_dict in conf:
            #Sort through each entry in the list of dictionaries and parse depending on their type (e.g. DDG, ACQ, AWG etc...)
            if cur_dict['type'] == 'DDG':
                #Find the corresponding DDG in the current list of registered DDG Modules and set its configuration parameters
                for cur_ddg in self._list_DDGs:
                    if cur_ddg.Name == cur_dict['instrument']:
                        cur_ddg._set_current_config(cur_dict)
                        break
                    #TODO: Consider adding input-trigger support for DDGs
            elif cur_dict['type'] == 'ACQ':
                cur_acq = self._instr_ACQ
                cur_acq._set_current_config(cur_dict)
                #After setting the parameters, write down the current device and its trigger relation (i.e. the source and ID)
                if 'TriggerSource' in cur_dict:
                    trig_relations.append( (cur_acq, cur_dict['TriggerSource']) )
            elif cur_dict['type'] == 'AWG':
                for cur_awg in self._list_AWGs:
                    if cur_awg.Name == cur_dict['Name']:
                        cur_awg._set_current_config(cur_dict)
                        for ind, cur_output_dict in enumerate(cur_dict['OutputChannels']):
                            if 'TriggerSource' in cur_output_dict:
                                trig_relations.append( (cur_awg.get_output_channel(ind), cur_output_dict['TriggerSource']) )
                        break
        #
        #Settle the triggers
        #
        possible_trig_sources = self._list_DDGs + self._list_AWGs
        for cur_trig_rel in trig_relations:
            cur_dest_obj = cur_trig_rel[0]
            cur_trig_dict = cur_trig_rel[1]
            cur_src_name = cur_trig_dict['TriggerHAL']
            cur_src = None
            #For the current trigger relation, find its source by using the HAL module name (i.e. H/W instrument name
            for cand_src in possible_trig_sources:
                if cand_src.Name == cur_src_name:
                    cur_src = cand_src
                    break
            assert cur_src != None, "Trigger source could not be found for instrument " + cur_dest_obj.name + " sourcing from an unknown module " + cur_src_name
            #Set the trigger source on the destination object (AWGs and ACQ modules have the set_trigger_source function implemented by default)
            cur_dest_obj.set_trigger_source(cur_src._get_trigger_output_by_id(cur_trig_dict['TriggerID'], cur_trig_dict['TriggerCH']))

    def init_instrument_relations(self):
        #Settle trigger relations in case they have changed in a previous configuration...
        for cur_trig_rel in self._cur_trig_rels:
            cur_trig_rel[0].set_trigger_source(cur_trig_rel[1])
            cur_trig_rel[0].InputTriggerEdge = cur_trig_rel[2]

    def prepare_instruments(self):
        #TODO: Write rest of this with error checking
        for cur_awg in self._list_AWGs:
            #TODO: Write concurrence/change checks to better optimise AwG...
            cur_awg.prepare_AWG_Waveforms()
        for cur_awg in self._list_AWGs:
            cur_awg.program_AWG_Waveforms()

    def get_data(self):
        #TODO: Pack the data appropriately if using multiple ACQ objects (coordinating their starts/finishes perhaps?)
        cur_acq = self._instr_ACQ
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

    @staticmethod
    def _add_rectangle(ax, xStart, xEnd, bar_width, yOff):
        '''
        Draws a rectangular patch for the timing diagram based on the delay and length values from a trigger object.

        Inputs:
            - ax     - Axis object to which the rectangle is to be drawn
            - xStart - Starting value on the x-axis
            - xEnd   - Ending value on the x-axis
            - bar_width - Vertical width of the rectangle to be drawn (should be less than 1 if multiple rows are to not intersect their rectangles)
            - yOff    - Current y-offset
        '''
        rect = patches.Rectangle( (xStart,yOff - 0.5*bar_width), xEnd-xStart, bar_width,
                                facecolor='white', edgecolor='black', hatch = '///')
        ax.add_patch(rect)

    @staticmethod
    def _add_rectangle_with_plot(ax, xStart, xEnd, bar_width, yOff, yVals):
        rect = patches.Rectangle( (xStart,yOff - 0.5*bar_width), xEnd-xStart, bar_width,
                                facecolor='white', edgecolor='black')
        ax.add_patch(rect)
        xOccupyFactor = 0.8
        yOccupyFactor = 0.8
        x0 = xStart + (1-xOccupyFactor)/2*(xEnd-xStart)
        x1 = xStart + (1+xOccupyFactor)/2*(xEnd-xStart)
        xVals = np.linspace(x0, x1, yVals.size)
        y0 = yOff-0.5*bar_width + (1-yOccupyFactor)/2*bar_width
        y1 = y0 + yOccupyFactor*bar_width
        yValsPlot = yVals * (y1-y0) + y0
        ax.plot(xVals, yValsPlot, 'k')

    @staticmethod
    def _plot_digital_pulse_sampled(ax, vals01, xStart, pts2xVals, bar_width, yOff):
        xVals = [xStart]
        yVals = [vals01[0]]
        last_val = vals01[0]
        for ind, cur_yval in enumerate(vals01):
            if cur_yval != last_val:
                xVals.append(pts2xVals * ind + xStart)
                xVals.append(pts2xVals * ind + xStart)
                yVals.append(last_val)
                yVals.append(cur_yval)
                last_val = cur_yval
        xVals.append(pts2xVals * ind + xStart)
        yVals.append(last_val)
        #Now scale the pulse appropriately...
        xVals = np.array(xVals)
        yVals = np.array(yVals)
        yVals = yVals*bar_width + yOff - bar_width*0.5
        ax.plot(xVals, yVals, 'k')

    @staticmethod
    def _plot_digital_pulse(ax, list_time_vals, xStart, scale_fac_x, bar_width, yOff):
        xVals = np.array( [xStart + x[0]*scale_fac_x for x in list_time_vals] )
        yVals = np.array( [x[1] for x in list_time_vals] )
        #
        xVals = np.repeat(xVals,2)[1:]
        yVals = np.ndarray.flatten(np.vstack([yVals,yVals]).T)[:-1]
        #Now scale the pulse appropriately...
        yVals = yVals*bar_width + yOff - bar_width*0.5
        ax.plot(xVals, yVals, 'k')

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

        bar_width = 0.6

        fig = plt.figure()
        ax = fig.add_axes((0.25, 0.125, 0.7, 0.78))
        num_channels = 0
        yticklabels = []

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
            elif cur_diag_info['Type'] == 'BlockShaded':
                if cur_diag_info['TriggerType'] == 'Gated':
                    if seg_times.size == 0:
                        continue
                    for cur_trig_seg in seg_times:
                        cur_trig_start = cur_trig_seg[0] * scale_fac
                        cur_len = (cur_trig_seg[1]-cur_trig_seg[0]) * scale_fac
                        self._add_rectangle(ax, cur_trig_start, cur_trig_start + cur_len, bar_width, num_channels)
                else:
                    for cur_trig_time in trig_times:
                        cur_trig_start = cur_trig_time * scale_fac
                        cur_len = cur_diag_info['Period'] * scale_fac
                        self._add_rectangle(ax, cur_trig_start, cur_trig_start + cur_len, bar_width, num_channels)
            elif cur_diag_info['Type'] == 'DigitalSampled':
                for cur_trig_time in trig_times:
                    cur_trig_start = cur_trig_time * scale_fac
                    mkrs, sample_rate = cur_diag_info['Data']
                    assert mkrs.size > 0, "Digital sampled pulse waveform is empty when plotting the timing diagram. Ensure _get_timing_diagram_info properly returns \'Type\' as \'None\' if inactive/empty..."
                    self._plot_digital_pulse_sampled(ax, mkrs, cur_trig_start, scale_fac/sample_rate, bar_width, num_channels)
            elif cur_diag_info['Type'] == 'DigitalEdges':
                for cur_trig_time in trig_times:
                    cur_trig_start = cur_trig_time * scale_fac
                    pts = cur_diag_info['Data']
                    assert len(pts) > 0 and pts[0][0] == 0.0, "Digital pulse waveform must be non-empty and start with t=0.0 when plotting the timing diagram."
                    self._plot_digital_pulse(ax, pts, cur_trig_start, scale_fac, bar_width, num_channels)
            elif cur_diag_info['Type'] == 'AnalogueSampled':
                for cur_trig_time in trig_times:
                    cur_trig_start = cur_trig_time * scale_fac
                    #Loop over all the waveform segments
                    cur_seg_x = cur_trig_start
                    for cur_wfm_dict in cur_diag_info['Data']:
                        cur_dur = cur_wfm_dict['Duration']*scale_fac
                        self._add_rectangle_with_plot(ax, cur_seg_x, cur_seg_x + cur_dur, bar_width, num_channels, cur_wfm_dict['yPoints'])
                        cur_seg_x += cur_dur
            else:
                assert False, "The \'Type\' key in the dictionary returned on calling the function _get_timing_diagram_info is invalid."
            num_channels += 1
            yticklabels.append(cur_obj.Name)

        ax.set_xlim((0, self._total_time*scale_fac))
        ax.set_ylim((-bar_width, num_channels + bar_width))
        
        fig.suptitle('timing configuration in ' + plt_units)
     
        ax.set_yticks(range(len(yticklabels)))
        ax.set_yticklabels(yticklabels, size=12)

        return fig
