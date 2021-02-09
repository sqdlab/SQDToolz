import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import json

class TimingConfiguration:
    def __init__(self, duration, list_DDGs, list_AWGs, instr_ACQ = None):
        self._list_DDGs = list_DDGs
        self._instr_ACQ = instr_ACQ
        self._list_AWGs = list_AWGs
        self._total_time = duration

    @property
    def RepetitionTime(self):
        return self._total_time
    @RepetitionTime.setter
    def RepetitionTime(self, len_seconds):
        self._total_time = len_seconds

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
    def _plot_digital_pulse(ax, vals01, xStart, pts2xVals, bar_width, yOff):
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

    def prepare_instruments(self):
        #TODO: Write rest of this with error checking
        for cur_awg in self._list_AWGs:
            #TODO: Write concurrence/change checks to better optimise AwG...
            cur_awg.program_AWG()

    def get_data(self):
        #TODO: Pack the data appropriately if using multiple ACQ objects (coordinating their starts/finishes perhaps?)
        cur_acq = self._instr_ACQ
        return cur_acq.get_data()

    @staticmethod
    def _get_trigger_edges(trig_object, init_trig_src_edge):
        #Collect the list/chain of trigger dependencies
        trig_list = [(trig_object, init_trig_src_edge)]
        cur_trig = trig_object._get_instr_trig_src()
        cur_src_edge = trig_object._get_instr_input_trig_edge()
        #By not inserting the first one, the times intrinsically start from t=0
        while(cur_trig != None):
            assert not cur_trig in trig_list, "There is a cyclic dependency on the trigger sources."
            trig_list += [(cur_trig, cur_src_edge)]
            cur_src_edge = cur_trig._get_instr_input_trig_edge()
            cur_trig = cur_trig._get_instr_trig_src()
            
        #Now spawn the tree of trigger times
        #TODO: Add error-checking to ensure the times do not overlap...
        all_times = np.array([])
        for cur_trig in trig_list[::-1]:    #Start from the top of the tree...
            cur_times = cur_trig[0].get_trigger_times(cur_trig[1])
            cur_times = np.array(cur_times)
            if (len(all_times) == 0):
                all_times = cur_times
            else:
                new_list = []
                for cur_time in all_times:
                    new_list += [cur_times + cur_time]  #Translate the current trigger edges by the previous trigger edges
                all_times = np.concatenate(new_list)
        return all_times

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
        #Plotting is done from the bottom to the top (i.e. increasing up the y-axis)
        #Plot the ACQ capture region
        cur_acq = self._instr_ACQ
        if (cur_acq):
            trig_times = self._get_trigger_edges(cur_acq.get_trigger_source(), cur_acq.InputTriggerEdge)
            for ind, cur_trig in enumerate(trig_times):
                cur_trig_start = cur_trig * scale_fac
                cur_len = cur_acq._get_acq_window_len(ind) * scale_fac
                self._add_rectangle(ax, cur_trig_start, cur_trig_start + cur_len, bar_width, num_channels)
            num_channels += 1
            yticklabels.append(cur_acq.name)
        #
        #Plot the AWG output pulses and markers (if any)
        #
        for cur_awg_wfm in self._list_AWGs[::-1]:
            #Assemble the marker channels (if any)
            wfm_plot_bars = cur_awg_wfm._get_waveform_plot_segments()
            for cur_ch_index, cur_output_channel in enumerate(cur_awg_wfm.get_output_channels()):
                for cur_mkr_channel in cur_output_channel.get_all_markers()[::-1]:
                    mkrs = cur_mkr_channel._assemble_marker_raw()
                    if mkrs.size > 0:
                        cur_trig_src = cur_output_channel.get_trigger_source() #TODO: There is code-duplication with below; optimise/pre-calculate...
                        if (cur_trig_src == None):
                            trig_times = [0]
                        else:
                            trig_times = self._get_trigger_edges(cur_trig_src, cur_output_channel.InputTriggerEdge)
                        for ind, cur_trig in enumerate(trig_times):
                            cur_trig_start = cur_trig * scale_fac
                            self._plot_digital_pulse(ax, mkrs, cur_trig_start, scale_fac/cur_awg_wfm._sample_rate, bar_width, num_channels)
                        num_channels += 1
                        cur_ch = cur_awg_wfm.get_output_channel(cur_ch_index)
                        yticklabels.append(cur_ch._instr_awg.name + ":" + cur_ch._channel_name + "[Mkr]")
            #Assemble the segments into its constituent channel(s) - e.g. IQ waveforms or other multichannel waveforms
            #may opt to combine or plot 2 separate channels...
            wfm_plot_bars = cur_awg_wfm._get_waveform_plot_segments()
            for cur_ch_index, cur_output_waveform in enumerate(wfm_plot_bars[::-1]):
                #Loop over all the trigger edges in the trigger source (each spawning its own waveform event)
                cur_trig_src = cur_awg_wfm.get_output_channel(cur_ch_index).get_trigger_source()
                if (cur_trig_src == None):
                    trig_times = [0]
                else:
                    trig_times = self._get_trigger_edges(cur_trig_src, cur_awg_wfm.get_output_channel(cur_ch_index).InputTriggerEdge)
                for ind, cur_trig in enumerate(trig_times):
                    cur_trig_start = cur_trig * scale_fac
                    #Loop over all the waveform segments
                    cur_seg_x = cur_trig_start
                    for cur_wfm_dict in cur_output_waveform[1]:
                        cur_dur = cur_wfm_dict['duration']*scale_fac
                        self._add_rectangle_with_plot(ax, cur_seg_x, cur_seg_x + cur_dur, bar_width, num_channels, cur_wfm_dict['yPoints'])
                        cur_seg_x += cur_dur
                num_channels += 1
                yticklabels.append(cur_output_waveform[0])
        #
        #Plot the DDG output pulses
        #
        for cur_ddg in self._list_DDGs:
            cur_channels = cur_ddg.get_all_outputs()
            for cur_ch in cur_channels[::-1]:
                cur_polarity = 2*cur_ch.TrigPolarity-1
                cur_verts = [(0.0, num_channels - cur_polarity*0.5*bar_width),
                             (cur_ch.TrigPulseDelay, num_channels - cur_polarity*0.5*bar_width),
                             (cur_ch.TrigPulseDelay, num_channels + cur_polarity*0.5*bar_width),
                             (cur_ch.TrigPulseDelay+cur_ch.TrigPulseLength, num_channels + cur_polarity*0.5*bar_width),
                             (cur_ch.TrigPulseDelay+cur_ch.TrigPulseLength, num_channels - cur_polarity*0.5*bar_width),
                             (self._total_time, num_channels - cur_polarity*0.5*bar_width)]
                ax.plot([x[0]*scale_fac for x in cur_verts], [x[1] for x in cur_verts], 'k')
                num_channels += 1
                yticklabels.append('{0}:{1}'.format(cur_ddg.Name, cur_ch.name))

        ax.set_xlim((0, self._total_time*scale_fac))
        ax.set_ylim((-bar_width, num_channels + bar_width))
        
        fig.suptitle('timing configuration in ' + plt_units)
     
        ax.set_yticks(range(len(yticklabels)))
        ax.set_yticklabels(yticklabels, size=12)

        return fig