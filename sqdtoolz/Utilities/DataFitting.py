import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize

class DFitPeakLorentzian:
    def __init__(self):
        pass

    def get_fitted_plot(self, data_x, data_y, xLabel="", dip = False):
        def func(x, a, w, x0, c):
            return a * (0.5*w)**2/((x-x0)**2 + (0.5*w)**2) + c

        xMin = np.min(data_x)
        xMax = np.max(data_x)
        yMin = np.min(data_y)
        yMax = np.max(data_y)

        #Calculate initial guesses...
        c0 = 0.5 * ( np.mean(data_y[:int(data_y.size*0.1)]) + np.mean(data_y[-int(data_y.size*0.1):]) )
        w0 = 0.2 * (xMax - xMin)
        x00 = np.mean(data_x)
        if dip:
            a0 = np.min(data_y) - c0
        else:
            a0 = np.max(data_y) - c0

        if dip:
            popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, w0, x00, c0],
                                             bounds=([1.2*a0, np.abs(data_x[1]-data_x[0]), xMin, -np.inf], [0, 0.9*(xMax - xMin), xMax, np.inf]))
        else:
            popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, w0, x00, c0],
                                             bounds=([0, np.abs(data_x[1]-data_x[0]), xMin, -np.inf], [1.2*a0, 0.9*(xMax - xMin), xMax, np.inf]))

        fig, axs = plt.subplots(1)
        axs.plot(data_x, data_y, 'kx')
        axs.plot(data_x, func(data_x, *popt), 'r-')
        axs.set_xlabel(xLabel)
        axs.set_ylabel('IQ Amplitude')

        datapkt = {
            'amplitude' : popt[0],
            'width' : popt[1],
            'centre' : popt[2],
            'offset' : popt[3],
            'fig'   : fig
        }

        return datapkt
            

class DFitSinusoid:
    def __init__(self):
        pass

    def get_fitted_plot(self, data_x, data_y, xLabel="", yLabel=""):
        def func(x, a, tau, f, phi, c):
            return a * np.exp(-x/tau) * np.cos(2*np.pi*f*x + phi) + c

        xMin = np.min(data_x)
        xMax = np.max(data_x)
        yMin = np.min(data_y)
        yMax = np.max(data_y)

        #Calculate initial guesses...
        # c0 = 0.5 * ( np.mean(data_y[:int(data_y.size*0.1)]) + np.mean(data_y[-int(data_y.size*0.1):]) )
        # w0 = 0.2 * (xMax - xMin)
        # x00 = np.mean(data_x)
        # if dip:
        #     a0 = np.min(data_y) - c0
        # else:
        #     a0 = np.max(data_y) - c0

        a0 = np.max(data_y) - np.min(data_y)
        tau0 = 1
        f0 = 1
        phi0 = 0
        c0 = np.mean(data_y)

        popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, tau0, f0, phi0, c0])
                                            #bounds=([1.2*a0, np.abs(data_x[1]-data_x[0]), xMin, -np.inf], [0, 0.9*(xMax - xMin), xMax, np.inf]))

        fig, axs = plt.subplots(1)
        axs.plot(data_x, data_y, 'kx')
        axs.plot(data_x, func(data_x, *popt), 'r-')
        axs.set_xlabel(xLabel)
        axs.set_ylabel(yLabel)

        datapkt = {
            'amplitude' : popt[0],
            'decay_time': popt[1],
            'frequency' : popt[2],
            'phase'     : popt[3],
            'offset'    : popt[4],
            'fig'   : fig
        }

        return datapkt
            
