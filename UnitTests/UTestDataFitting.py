from sqdtoolz.Utilities.DataFitting import*
import numpy as np

data_x = np.arange(0,10,0.05)
data_y = np.exp(-data_x/5)*np.cos(data_x*2*np.pi/2.2 + 2.54) + 0.5*np.random.rand(data_x.size)

dfit = DFitSinusoid()
dpkt = dfit.get_fitted_plot(data_x, data_y)
dpkt['fig'].show()
input('Press ENTER')

data_x = np.arange(100,300,1)
data_y = np.exp(-(data_x-220)**2/20**2) + 0.5*np.random.rand(data_x.size)
data_y2 = -np.exp(-(data_x-220)**2/20**2) + 0.5*np.random.rand(data_x.size)

dfit = DFitPeakLorentzian()
dpkt = dfit.get_fitted_plot(data_x, data_y, "test1")
dpkt['fig'].show()
input('Press ENTER')
dpkt = dfit.get_fitted_plot(data_x, data_y2, "test2", dip=True)
dpkt['fig'].show()
input('Press ENTER')
