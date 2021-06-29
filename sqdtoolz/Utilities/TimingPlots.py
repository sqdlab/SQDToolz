import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

class TimingPlot:
    def __init__(self):
        self.bar_width = 0.6

        self.fig = plt.figure()
        self.ax = self.fig.subplots()
        self.num_channels = -1
        self.yticklabels = []

        self.min_feature_size = 1e15

    def add_rectangle(self, xStart, xEnd):
        '''
        Draws a rectangular patch for the timing diagram based on the delay and length values from a trigger object.

        Inputs:
            - xStart - Starting value on the x-axis
            - xEnd   - Ending value on the x-axis
        '''
        yOff = self.num_channels
        rect = patches.Rectangle( (xStart,yOff - 0.5*self.bar_width), xEnd-xStart, self.bar_width,
                                facecolor='white', edgecolor='black', hatch = '///')
        self.ax.add_patch(rect)
        #Calculate smallest feature size...
        self.min_feature_size = min(self.min_feature_size, xEnd-xStart)

    def goto_new_row(self, new_ylabel):
        self.num_channels += 1
        self.yticklabels.append(new_ylabel)

    def add_rectangle_with_plot(self, xStart, xEnd, yVals):
        yOff = self.num_channels
        rect = patches.Rectangle( (xStart,yOff - 0.5*self.bar_width), xEnd-xStart, self.bar_width,
                                facecolor='white', edgecolor='black')
        self.ax.add_patch(rect)
        xOccupyFactor = 0.8
        yOccupyFactor = 0.8
        x0 = xStart + (1-xOccupyFactor)/2*(xEnd-xStart)
        x1 = xStart + (1+xOccupyFactor)/2*(xEnd-xStart)
        xVals = np.linspace(x0, x1, yVals.size)
        y0 = yOff-0.5*self.bar_width + (1-yOccupyFactor)/2*self.bar_width
        y1 = y0 + yOccupyFactor*self.bar_width
        yValsPlot = yVals * (y1-y0) + y0
        self.ax.plot(xVals, yValsPlot, 'k')
        #Calculate smallest feature size...
        self.min_feature_size = min(self.min_feature_size, xEnd-xStart)

    def add_digital_pulse_sampled(self, vals01, xStart, pts2xVals):
        yOff = self.num_channels
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
        yVals = yVals*self.bar_width + yOff - self.bar_width*0.5
        self.ax.plot(xVals, yVals, 'k')
        #Calculate smallest feature size...
        feat_sizes = xVals[1:]-xVals[:-1]
        self.min_feature_size = min(self.min_feature_size, np.min(feat_sizes[feat_sizes>0]))

    def add_digital_pulse(self, list_time_vals, xStart, scale_fac_x):
        yOff = self.num_channels
        xVals = np.array( [xStart + x[0]*scale_fac_x for x in list_time_vals] )
        yVals = np.array( [x[1] for x in list_time_vals] )
        #
        xVals = np.repeat(xVals,2)[1:]
        yVals = np.ndarray.flatten(np.vstack([yVals,yVals]).T)[:-1]
        #Now scale the pulse appropriately...
        yVals = yVals*self.bar_width + yOff - self.bar_width*0.5
        self.ax.plot(xVals, yVals, 'k')
        #Calculate smallest feature size...
        feat_sizes = xVals[1:]-xVals[:-1]
        self.min_feature_size = min(self.min_feature_size, np.min(feat_sizes[feat_sizes>0]))

    def finalise_plot(self, total_time, x_units, title):
        self.ax.set_xlim((0, total_time))
        self.ax.set_ylim((-self.bar_width, self.num_channels + self.bar_width))
        
        self.fig.suptitle(title)
        self.ax.set_xlabel(f'time ({x_units})')
     
        self.ax.set_yticks(range(len(self.yticklabels)))
        self.ax.set_yticklabels(self.yticklabels, size=12)

        #Rescale plot to better observe the smaller features...
        #
        min_pixels_per_feature = 3
        #
        size_ratio_x = self.min_feature_size / total_time
        #Get axis size (taken from: https://stackoverflow.com/questions/19306510/determine-matplotlib-axis-size-in-pixels)
        bbox = self.ax.get_window_extent().transformed(self.fig.dpi_scale_trans.inverted())
        width, height = bbox.width, bbox.height
        width *= self.fig.dpi
        height *= self.fig.dpi
        #
        if width*size_ratio_x < min_pixels_per_feature:
            old_size = self.fig.get_size_inches()
            size_fac =  min_pixels_per_feature / (width*size_ratio_x)
            new_size_x = old_size[0]-bbox.width + bbox.width*size_fac
            self.fig.set_size_inches(min(new_size_x, (8192) / self.fig.dpi), old_size[1]) #There's a limitation on MATPLOTLIB plots in which dimensions must be less than 2^16
            self.fig.tight_layout()

        return self.fig

# tp = TimingPlot()
# tp.goto_new_row('test1')
# tp.add_digital_pulse_sampled(np.array([0,0,1,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0]), 1e-9, 1e-9)
# tp.add_digital_pulse([(0.0, 0), (5e-9, 1), (10e-9, 0)], 20e-9, 1)
# tp.finalise_plot(1e-6, 'ns', 'test').show()
# input('Press ENTER')

