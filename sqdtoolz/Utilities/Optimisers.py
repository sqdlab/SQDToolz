import matplotlib.patches as patches
import numpy as np
import matplotlib.pyplot as plt

class OptimiseParaboloid:
    def __init__(self, fXY):
        self._fXY = fXY
    
    def _sample_coord(self, x, y):
        z_val = self._fXY(x,y)
        self.rec_pts += [[x,y,z_val]]
        return z_val

    def find_minimum(self, x_bounds, y_bounds, fig=None, ax=None, **kwargs):
        self.rec_pts = []

        num_sample_points = kwargs.get('num_win_sample_pts', 3)
        step_bound_fraction = kwargs.get('step_shrink_factor', 0.33)
        dont_plot = kwargs.get('dont_plot', False)

        cur_x_bounds = x_bounds
        cur_y_bounds = y_bounds
        is_x = True
        frac_move = 1-step_bound_fraction
        bnd_history = []
        for m in range(10):
            cur_xMid = 0.5*(cur_x_bounds[0] + cur_x_bounds[1])
            cur_yMid = 0.5*(cur_y_bounds[0] + cur_y_bounds[1])
            if is_x:
                cur_x = np.linspace(*cur_x_bounds, num_sample_points)
                cur_z = [self._sample_coord(cur_x[m], cur_yMid)  for m in range(num_sample_points)]
                pFit = np.polyfit(cur_x, np.array(cur_z), 2)
                xMin = -pFit[1]*0.5/pFit[0]
                # print(xMin)
                cur_x_bounds = (cur_x_bounds[0]*(1-frac_move) + xMin*frac_move, cur_x_bounds[1]*(1-frac_move) + xMin*frac_move)
            else:
                cur_y = np.linspace(*cur_y_bounds, num_sample_points)
                cur_z = [self._sample_coord(cur_xMid, cur_y[m])  for m in range(num_sample_points)]
                pFit = np.polyfit(cur_y, np.array(cur_z), 2)
                yMin = -pFit[1]*0.5/pFit[0]
                # print(yMin)
                cur_y_bounds = (cur_y_bounds[0]*(1-frac_move) + yMin*frac_move, cur_y_bounds[1]*(1-frac_move) + yMin*frac_move)
            is_x = not is_x
            bnd_history += [(cur_x_bounds, cur_y_bounds)]
            # print(bnd_history[-1])

        arr_pts = np.array(self.rec_pts)

        if not dont_plot:
            if fig == None:
                fig, ax = plt.subplots(1)
            ax.scatter(arr_pts[:,0], arr_pts[:,1], c=arr_pts[:,2])
            for cur_bnd in bnd_history:
                rect = patches.Rectangle((cur_bnd[0][0], cur_bnd[1][0]), cur_bnd[0][1] - cur_bnd[0][0], cur_bnd[1][1] - cur_bnd[1][0], linewidth=1, edgecolor='r', facecolor='none')
                ax.add_patch(rect)

        return arr_pts[np.argmin(arr_pts[:,2]),:], fig   #Basically: (x, y, minimum z), fig

