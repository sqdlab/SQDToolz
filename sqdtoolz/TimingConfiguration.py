from matplotlib.patches import Rectangle, Path, PathPatch
import matplotlib.pyplot as plt

class TimingConfiguration:
    def __init__(self, duration, list_DDGs):
        self._list_DDGs = list_DDGs
        self._total_time = duration

    @property
    def RepetitionTime(self):
        return self._total_time
    @RepetitionTime.setter
    def RepetitionTime(self, len_seconds):
        self._total_time = len_seconds

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