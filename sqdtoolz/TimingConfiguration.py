import matplotlib.patches as patches
import matplotlib.pyplot as plt

class TimingConfiguration:
    def __init__(self, duration, list_DDGs, instr_ACQ):
        self._list_DDGs = list_DDGs
        self._instr_ACQ = instr_ACQ
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
    def _reconcile_edge(trig_pulse_obj, input_trig_pol):
        '''
        Gives the starting point of the trigger (for generation or acquisition) given a trigger pulse and an input edge polarity.

        Inputs:
            - trig_pulse_obj - Trigger object holding the trigger pulse information
            -  input_trig_pol - Input trigger edge (0 or 1 for negative or positive edge/polarity)

        Returns the delay time in which the trigger activates.
        '''
        pulse_polarity = trig_pulse_obj.TrigPolarity
        if input_trig_pol == 0:
            if pulse_polarity == 0:
                return trig_pulse_obj.TrigPulseDelay
            else:
                return trig_pulse_obj.TrigPulseDelay + trig_pulse_obj.TrigPulseLength
        elif input_trig_pol == 1:
            if pulse_polarity == 0:
                return trig_pulse_obj.TrigPulseDelay + trig_pulse_obj.TrigPulseLength
            else:
                return trig_pulse_obj.TrigPulseDelay
        else:
            assert False, "Trigger input polarity must be 0 or 1 for negative or positive edge/polarity."


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
            cur_trig_start = self._reconcile_edge(cur_acq.get_trigger_source(), cur_acq.TriggerEdge) * scale_fac
            cur_len = cur_acq.NumSamples / cur_acq.SampleRate * scale_fac
            self._add_rectangle(ax, cur_trig_start, cur_trig_start + cur_len, bar_width, num_channels)
            num_channels += 1
            yticklabels.append(cur_acq.name)
        #Plot the DDG output pulses
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
                yticklabels.append('{0}:{1}'.format(cur_ddg.name, cur_ch.name))

        ax.set_xlim((0, self._total_time*scale_fac))
        ax.set_ylim((-bar_width, num_channels + bar_width))
        
        fig.suptitle('timing configuration in ' + plt_units)
     
        ax.set_yticks(range(len(yticklabels)))
        ax.set_yticklabels(yticklabels, size=12)

        return fig