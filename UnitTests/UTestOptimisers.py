from sqdtoolz.Utilities.Optimisers import OptimiseParaboloid
import numpy as np
import matplotlib.pyplot as plt

X = np.arange(-1,1,0.001)                 
Y = np.arange(-1,1,0.001)
xx, yy = np.meshgrid(X, Y)

z_vals = 10*(2*(xx-0.25)**2+(yy-0.123)**2) + 0.01*np.random.rand(*xx.shape)
# plt.pcolor(X,Y, z_vals, shading='nearest')

def sample_coord(x, y):
    return z_vals[np.argmin(np.abs(y-Y)), np.argmin(np.abs(x-X))]

opt = OptimiseParaboloid(sample_coord)
min_coord, fig = opt.find_minimum( (-0.9,0.9), (-0.85,0.9) )

print(min_coord)
fig.show()
input('Done')
