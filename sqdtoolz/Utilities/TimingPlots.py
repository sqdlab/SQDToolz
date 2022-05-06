import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

class TimingPlot:
    def __init__(self):
        self.bar_width = 0.6

        self.fig = plt.figure()
        self.num_channels = -1
        self.yticklabels = []   #Holds the list of pairs containing: [string for label, maximum x-value]

        self._cur_pulses = []
        self._cur_rects = []
        self._cur_rectplots = []

        self.min_feature_size = 1e15

    class obj_rectangle:
        def __init__(self, x1, x2, y1, y2):
            self.x1 = x1
            self.x2 = x2
            self.y1 = y1
            self.y2 = y2
        
        def gen_rectangle(self, shade=True, colour='white'):
            x0 = (self.x1, self.y1)
            if shade:
                return patches.Rectangle( x0, self.x2-self.x1, self.y2-self.y1, facecolor=colour, edgecolor='black', hatch = '///')
            else:
                return patches.Rectangle( x0, self.x2-self.x1, self.y2-self.y1, facecolor=colour, edgecolor='black')

    def add_rectangle(self, xStart, xEnd):
        '''
        Draws a rectangular patch on the timing diagram.

        Inputs:
            - xStart - Starting value on the x-axis
            - xEnd   - Ending value on the x-axis
        '''
        yOff = self.num_channels
        rect = TimingPlot.obj_rectangle(xStart, xEnd, yOff - 0.5*self.bar_width, yOff + 0.5*self.bar_width)
        self._cur_rects += [rect]
        #Calculate smallest feature size...
        self.min_feature_size = min(self.min_feature_size, xEnd-xStart)
        self.yticklabels[-1][1] = max(xEnd, self.yticklabels[-1][1])

    def goto_new_row(self, new_ylabel):
        self.num_channels += 1
        self.yticklabels.append([new_ylabel,0])

    def add_rectangle_with_plot(self, xStart, xEnd, yVals):
        '''
        Draws a rectangular patch on the timing diagram with a plot embedded within it. Note that the plot is scaled to fit within the rectangle.

        Inputs:
            - xStart - Starting value on the x-axis
            - xEnd   - Ending value on the x-axis
            - yVals  - A list of y-values to use in generating the plot within the rectangle.
        '''
        yOff = self.num_channels
        rect = TimingPlot.obj_rectangle(xStart, xEnd, yOff - 0.5*self.bar_width, yOff + 0.5*self.bar_width)

        xOccupyFactor = 0.8
        yOccupyFactor = 0.8
        x0 = xStart + (1-xOccupyFactor)/2*(xEnd-xStart)
        x1 = xStart + (1+xOccupyFactor)/2*(xEnd-xStart)
        xVals = np.linspace(x0, x1, yVals.size)
        y0 = yOff-0.5*self.bar_width + (1-yOccupyFactor)/2*self.bar_width
        y1 = y0 + yOccupyFactor*self.bar_width
        yValsPlot = yVals * (y1-y0) + y0

        self._cur_rectplots += [(rect, (xVals, yValsPlot))]

        #Calculate smallest feature size...
        self.min_feature_size = min(self.min_feature_size, xEnd-xStart)
        self.yticklabels[-1][1] = max(xEnd, self.yticklabels[-1][1])

    def add_digital_pulse_sampled(self, vals01, xStart, pts2xVals):
        '''
        Draws a digital waveform (over a uniformly sampled set of points) on the timing diagram.

        Inputs:
            - vals01 - List of digital 0s and 1s
            - xStart - Starting value on the x-axis
            - pts2xVals - The sampling interval (i.e. reciprocal of sample rate) of each point in the digital waveform.
        '''
        vals01 = np.append(np.array(vals01), vals01[-1])

        yOff = self.num_channels
        xVals = [xStart]
        yVals = [vals01[0]]
        last_val = vals01[0]
        for ind, cur_yval in enumerate(vals01):
            if cur_yval != last_val:    #<--- Doing it this way to compress the waveform and only store points of signal-change...
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
        yVals = yVals*self.bar_width + yOff - self.bar_width*0.5
        self._cur_pulses += [(xVals, yVals)]    #ax.plot(xVals, yVals, 'k')
        #Calculate smallest feature size...
        feat_sizes = xVals[1:]-xVals[:-1]
        self.min_feature_size = min(self.min_feature_size, np.min(feat_sizes[feat_sizes>0]))
        #
        self.yticklabels[-1][1] = max(xVals[-1], self.yticklabels[-1][1])

    def add_digital_pulse(self, list_time_vals, xStart, scale_fac_x=1.0):
        '''
        Draws a digital waveform on the timing diagram. The waveform is given as a list of changes in the signal. For example,
        [[0,0], [10,1], [15,0]] implies that the signal is 0 from time 0 to 10, 1 from time 10 to 15 and then zero from 15
        onwards.

        Inputs:
            - list_time_vals - List of time and binary value pairs as outlined in the description above.
            - xStart - Starting value on the x-axis
            - scale_fac_x - (default: 1) The sampling interval (i.e. reciprocal of sample rate) of each point in the digital
                            waveform. This is used if list_time_vals is given as sample number in the first argument of the
                            pairs as opposed to the actual time.
        '''
        yOff = self.num_channels
        xVals = np.array( [xStart + x[0]*scale_fac_x for x in list_time_vals] )
        yVals = np.array( [x[1] for x in list_time_vals] )
        #
        xVals = np.repeat(xVals,2)[1:]
        yVals = np.ndarray.flatten(np.vstack([yVals,yVals]).T)[:-1]
        #Now scale the pulse appropriately...
        yVals = yVals*self.bar_width + yOff - self.bar_width*0.5
        self._cur_pulses += [(xVals, yVals)]    #ax.plot(xVals, yVals, 'k')
        #Calculate smallest feature size...
        feat_sizes = xVals[1:]-xVals[:-1]
        self.min_feature_size = min(self.min_feature_size, np.min(feat_sizes[feat_sizes>0]))
        #
        self.yticklabels[-1][1] = max(xVals[-1], self.yticklabels[-1][1])

    def _plot_stretched(self, total_time, x_units, title):
        ax = self.fig.subplots()
        ax.set_xlim((0, total_time))
        ax.set_ylim((-self.bar_width, self.num_channels + self.bar_width))
        
        self.fig.suptitle(title)
        ax.set_xlabel(f'time ({x_units})')
     
        ax.set_yticks(range(len(self.yticklabels)))
        ax.set_yticklabels([x[0] for x in self.yticklabels], size=12)

        #Rescale plot to better observe the smaller features...
        #
        min_pixels_per_feature = 3
        #
        size_ratio_x = self.min_feature_size / total_time
        #Get axis size (taken from: https://stackoverflow.com/questions/19306510/determine-matplotlib-axis-size-in-pixels)
        bbox = ax.get_window_extent().transformed(self.fig.dpi_scale_trans.inverted())
        width, height = bbox.width, bbox.height
        width *= self.fig.dpi
        height *= self.fig.dpi
        #
        if width*size_ratio_x < min_pixels_per_feature:
            old_size = self.fig.get_size_inches()
            size_fac =  min_pixels_per_feature / (width*size_ratio_x)
            new_size_x = old_size[0]-bbox.width + bbox.width*size_fac
            self.fig.set_size_inches(min(new_size_x, (8192) / self.fig.dpi), old_size[1]) #There's a limitation on MATPLOTLIB plots in which dimensions must be less than 2^16
            
            #Plot everything
            for cur_plot in self._cur_rects:
                ax.add_patch(cur_plot.gen_rectangle(True))
            for cur_plot in self._cur_pulses:
                ax.plot(cur_plot[0], cur_plot[1], 'k')
            for cur_plot in self._cur_rectplots:
                ax.add_patch(cur_plot[0].gen_rectangle(False))
                ax.plot(cur_plot[1][0], cur_plot[1][1], 'k')
            
            self.fig.tight_layout()

    def finalise_plot(self, total_time, x_units, title, max_segment_size_threshold = 100, tol=0.001):
        if len(self._cur_pulses) + len(self._cur_rects) + len(self._cur_rectplots) == 0:
            return plt.figure()

        #Gather the feature time-stamps (e.g. changes, beginnings/ends)
        x_vals = [x[0] for x in self._cur_pulses] + [np.array([x.x1, x.x2]) for x in self._cur_rects] + [np.array([x[0].x1, x[0].x2]) for x in self._cur_rectplots]
        x_vals = np.concatenate(x_vals)

        for cur_y_label in self.yticklabels:
            assert cur_y_label[1] <= total_time, f"Error in timing-diagram. The entity {cur_y_label[0]} has a time-point at {cur_y_label[1]} which exceeds the allocated total-time (designated repetition window size) of {total_time}."

        #np.unique does not work due to floating-point issues.
        a = x_vals
        i = np.argsort(a.flat)
        d = np.append(True, np.diff(a.flat[i]))
        x_vals = a.flat[i[d>tol]]

        #Find portions with long segments
        seg_lens_raw = x_vals[1:] - x_vals[:-1]
        seg_lens = seg_lens_raw / np.min(seg_lens_raw)

        if len(seg_lens) > 50 or np.max(seg_lens) < max_segment_size_threshold:
            #Default plotting - give up if there are a ton of segments or if there are not strange scaling on the plots...
            self._plot_stretched(total_time, x_units, title)
        else:
            #Fancy axis cutting!
            keep_size = 0.5 * np.min(seg_lens_raw)
            #Gather regions which need to be cut
            cut_inds = np.array(np.where(seg_lens >= max_segment_size_threshold))[0]

            xints = []
            divider_axes = []   #Just the boundary between two long segments that have each been cut!
            x_vals = np.append(x_vals, total_time)
            for c in range(len(cut_inds)+1):
                if c == 0:
                    ind_start = 0
                else:
                    ind_start = cut_inds[c-1]+1
                t_start = x_vals[ind_start]
                #
                if c == len(cut_inds):
                    ind_end = len(seg_lens)-1
                    t_end = total_time
                else:
                    ind_end = cut_inds[c]
                    t_end = x_vals[ind_end]
                #
                if ind_end - ind_start > 0:
                    mean_size = np.mean(seg_lens_raw[ind_start:ind_end])
                else:
                    mean_size = np.min(seg_lens_raw)
                    if c < len(cut_inds):
                        divider_axes += [c]
                #Adjust starting point to eat into the previous cut segment
                if ind_start > 0:
                    t_start -= min(mean_size*0.5, (x_vals[cut_inds[c-1]+1]-x_vals[cut_inds[c-1]])*0.5)
                #Adjust ending point to eat into the next cut segment
                if c < len(cut_inds):
                    t_end += min(mean_size*0.5, (x_vals[cut_inds[c]+1]-x_vals[cut_inds[c]])*0.5)
                #
                xints += [[t_start,t_end]]

            width_ratios = np.array([x[1]-x[0] for x in xints])
            width_ratios /= np.sum(width_ratios)
            width_ratios /= np.min(width_ratios)
            width_ratios = np.clip(width_ratios, 0, 2)
            axs = self.fig.subplots(1, cut_inds.size + 1, gridspec_kw={'width_ratios': width_ratios})
            self.fig.subplots_adjust(wspace=0.05)
            for m, ax in enumerate(axs):
                if m < len(axs)-1:
                    ax.spines['right'].set_visible(False)
                if m > 0:
                    ax.spines['left'].set_visible(False)
                    ax.set_yticks([])
                if m % 2 == 1:
                    ax.xaxis.tick_top()
                if m in divider_axes:
                    ax.set_xticks([ x_vals[cut_inds[m]] ])
                ax.set_xlim((xints[m][0], xints[m][1]))
                ax.ticklabel_format(useOffset=False)
                ax.set_ylim((-self.bar_width, self.num_channels + self.bar_width))  #Otherwise, one must use sharey=True on subplots
            axs[0].set_yticks(range(len(self.yticklabels)))
            axs[0].set_yticklabels([x[0] for x in self.yticklabels], size=12)
            self.fig.set_figwidth(15)

        
            #Plot digital pulses
            for cur_plot in self._cur_pulses:
                for ax in axs:
                    ax.plot(cur_plot[0], cur_plot[1], 'k')
            #Plot rectangles
            for cur_rect in self._cur_rects:
                for m, ax in enumerate(axs):
                    ax.add_patch(cur_rect.gen_rectangle(True))
            #Plot rectangles
            self._cur_rectplots.sort(key=lambda x: (x[0].y1, x[0].x1))    #Sort the rectangles in increasing y and then x to aid in colour coding...
            cols = ['lightyellow', 'powderblue', 'thistle']
            for p_ind, cur_plot in enumerate(self._cur_rectplots):
                cur_rect = cur_plot[0]
                for m, ax in enumerate(axs):
                    ax.add_patch(cur_rect.gen_rectangle(False, cols[p_ind % len(cols)]))
                    cur_x_vals = np.linspace(max(xints[m][0], cur_rect.x1), min(xints[m][1], cur_rect.x2), cur_plot[1][0].size)
                    ax.plot(cur_x_vals, cur_plot[1][1], 'k')

            
            #Plot the cut-slashes (inspired by: https://stackoverflow.com/questions/32185411/break-in-x-axis-of-matplotlib)
            d = 0.02 # how big to make the diagonal lines in axes coordinates
            ecc = 0
            for m, ax in enumerate(axs):
                temp_kwargs = dict(transform=ax.transAxes, color='k', clip_on=False)
                if m < len(axs)-1:
                    ax.plot((1-d*ecc,1+d*ecc), (-d,+d), **temp_kwargs)
                    ax.plot((1-d*ecc,1+d*ecc),(1-d,1+d), **temp_kwargs)
                if m > 0:
                    ax.plot((-d*ecc,+d*ecc), (1-d,1+d), **temp_kwargs)
                    ax.plot((-d*ecc,+d*ecc), (-d,+d), **temp_kwargs)

            self.fig.suptitle(title)
            self.fig.text(0.5, 0.0, f'time ({x_units})', verticalalignment='bottom') 

        return self.fig

# tp = TimingPlot()
# tp.goto_new_row('test1')
# tp.add_digital_pulse_sampled(np.array([0,0,1,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0]), 1e-9, 1e-9)
# tp.add_digital_pulse([(0.0, 0), (5e-9, 1), (10e-9, 0)], 20e-9, 1)
# tp.goto_new_row('test2')
# tp.add_rectangle(10e-9, 4900e-9)
# tp.goto_new_row('test3')
# tp.add_rectangle_with_plot(2000e-9, 10e-6, np.sin(np.linspace(0,10,100))*0.5+0.5)
# tp.finalise_plot(10e-6, 'ns', 'test', tol=1e-9).show()

# tp = TimingPlot()
# tp.goto_new_row('test1')
# tp.add_digital_pulse_sampled(np.array([0,0,1,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0]), 1e-9, 1e-9)
# tp.add_digital_pulse([(0.0, 0), (5e-9, 1), (10e-9, 0)], 20e-9, 1)
# tp.goto_new_row('test2')
# tp.add_rectangle(46e-6, 50e-6)
# tp.goto_new_row('test3')
# tp.add_rectangle_with_plot(0, 4e-6, 0*np.sin(np.linspace(0,10,100))*0.5+0.5)
# tp.add_rectangle_with_plot(4e-6, 45e-6, 0*np.sin(np.linspace(0,10,100))*0.5+0.5)
# tp.goto_new_row('test4')
# tp.add_rectangle_with_plot(45e-6, 45e-6+20e-9, np.sin(np.linspace(0,10,100))*0.5+0.5)
# tp.add_rectangle_with_plot(45e-6+20e-9, 50e-6, 0*np.sin(np.linspace(0,10,100))*0.5+0.5)
# tp.finalise_plot(50e-6, 's', 'test', tol=1e-9).show()
# input('Press ENTER')

