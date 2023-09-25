from sqdtoolz.Utilities.DataFitting import*
import numpy as np


data_x = np.arange(0,10,0.05)
data_y = 1.2*(1-np.exp(-data_x/5.7)) + 0.5*np.random.rand(data_x.size)

dfit = DFitExponential()
dpkt = dfit.get_fitted_plot(data_x, data_y, rise=True)
dpkt['fig'].show()
input('Press ENTER')

data_x = np.arange(0,10,0.05)
data_y = np.exp(-data_x/5.7) + 0.5*np.random.rand(data_x.size)

dfit = DFitExponential()
dpkt = dfit.get_fitted_plot(data_x, data_y)
dpkt['fig'].show()
input('Press ENTER')


data_x = np.arange(0,10,0.05)
data_y = np.arange(0,10,0.05)
xx, yy = np.meshgrid(data_x, data_y)
data_z = np.sin(xx) + np.sin(yy) + 0.25*(yy-2)**2

dfit = DFitMinMax2D()
dpkt = dfit.get_fitted_plot(data_x, data_y, data_z.T, True, "x-vals", "y-vals")
dpkt['fig'].show()
input('Press ENTER')


data_x = np.arange(0,10,0.05)
data_y = np.exp(-data_x/5)*np.cos(data_x*2*np.pi/2.2 + 2.54) + 0.5*np.random.rand(data_x.size)

dfit = DFitSinusoid()
dpkt = dfit.get_fitted_plot(data_x, data_y)
dpkt['fig'].show()
input('Press ENTER')

data_x = np.linspace(0.0,0.5,50)
data_y = np.array([0.23851978, 0.26857639, 0.23126279, 0.27585205, 0.26447248,
    0.27526831, 0.17744127, 0.22679398, 0.21559565, 0.24723698,
    0.35787993, 0.31643191, 0.31584339, 0.22591795, 0.22043368,
    0.18779161, 0.1751315 , 0.11268123, 0.1717033 , 0.22510175,
    0.21942741, 0.28069079, 0.3084679 , 0.30082049, 0.236087  ,
    0.29243284, 0.16359482, 0.21956686, 0.10740641, 0.08908458,
    0.13835961, 0.20114916, 0.23415966, 0.36481327, 0.3908816 ,
    0.29160973, 0.31766139, 0.23254812, 0.16462614, 0.16513641,
    0.0647385 , 0.13140232, 0.06296652, 0.11841913, 0.19849058,
    0.18849815, 0.30028236, 0.34362802, 0.31551777, 0.32641923])

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


data_x = np.arange(-10,10,0.1)
data_y = 5 * (0.75*0.5*2+data_x - 1)**2/((data_x - 1)**2 + (0.5*2)**2) + 3 + 0.5*np.random.rand(data_x.size)
data_y2 = 5 * (0.1*0.5*2+data_x - 1)**2/((data_x - 1)**2 + (0.5*2)**2) + 3 + 0.5*np.random.rand(data_x.size)
data_y3 = 5 * (-0.5*0.5*2+data_x - 1)**2/((data_x - 1)**2 + (0.5*2)**2) + 3 + 0.5*np.random.rand(data_x.size)

dfit = DFitFanoResonance()
dpkt = dfit.get_fitted_plot(data_x, data_y, "test1")
dpkt['fig'].show()
input('Press ENTER')
dpkt = dfit.get_fitted_plot(data_x, data_y2, "test2")
dpkt['fig'].show()
input('Press ENTER')
dpkt = dfit.get_fitted_plot(data_x, data_y3, "test2")
dpkt['fig'].show()
input('Press ENTER')