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
        def func(x, a, gamma, f, phi, c):
            return a * np.exp(-x*gamma) * np.cos(2*np.pi*f*x + phi) + c

        xMin = np.min(data_x)
        xMax = np.max(data_x)
        yMin = np.min(data_y)
        yMax = np.max(data_y)
        dx = data_x[1:]-data_x[:-1]
        data_x -= xMin  #Shift the data so that it starts from x=0 for the decay...

        data_y_levelled = data_y - np.mean(data_y)
        freqs = np.linspace(0.5/(xMax-xMin), 0.125/np.abs(np.min(dx)), 50)  #Presuming at least 8 points for the sine wave
        data_y_fft = [np.sum(np.exp(-1j*2*np.pi*f*data_x[1:])*data_y_levelled[1:]*dx) for f in freqs]

        indFreq = np.argmax( np.abs(data_y_fft) )

        f0 = freqs[indFreq]
        phi0 = np.angle(data_y_fft[indFreq])
        a0 = np.max(data_y) - np.min(data_y)
        gamma0 = 0
        c0 = np.mean(data_y)
        delta0 = xMin

        #Calculate with decay
        popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, gamma0, f0, phi0, c0],
                                            bounds=([0.1*a0, -5*(xMax-xMin), 0.5/(xMax-xMin),       -np.pi, yMin],
                                                    [1.2*a0,  5*(xMax-xMin), 0.5/np.abs(np.min(dx)), np.pi, yMax]))

        fig, axs = plt.subplots(1)
        axs.plot(data_x, data_y, 'kx')
        axs.plot(data_x, func(data_x, *popt), 'r-')
        axs.set_xlabel(xLabel)
        axs.set_ylabel(yLabel)

        datapkt = {
            'amplitude' : popt[0],
            'decay_rate': popt[1],
            'frequency' : popt[2],
            'phase'     : popt[3],
            'offset'    : popt[4],
            'fig'   : fig
        }

        return datapkt
            
