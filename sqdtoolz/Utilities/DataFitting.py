import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize

class DFitPeakLorentzian:
    def __init__(self):
        pass

    def get_fitted_plot(self, data_x, data_y, xLabel="", dip = False, dontplot=False):
        def func(x, a, w, x0, c):
            return a * (0.5*w)**2/((x-x0)**2 + (0.5*w)**2) + c

        xMin = np.min(data_x)
        xMax = np.max(data_x)
        yMin = np.min(data_y)
        yMax = np.max(data_y)

        #Calculate initial guesses...
        c0 = 0.5 * ( np.mean(data_y[:int(data_y.size*0.1)]) + np.mean(data_y[-int(data_y.size*0.1):]) )
        w0 = 0.2 * (xMax - xMin)
        if dip:
            a0 = np.min(data_y) - c0
            x00 = data_x[np.argmin(data_y)]
        else:
            a0 = np.max(data_y) - c0
            x00 = data_x[np.argmax(data_y)]

        if dip:
            popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, w0, x00, c0],
                                             bounds=([1.2*a0, np.abs(data_x[1]-data_x[0]), xMin, -np.inf], [0, 0.9*(xMax - xMin), xMax, np.inf]))
        else:
            popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, w0, x00, c0],
                                             bounds=([0, np.abs(data_x[1]-data_x[0]), xMin, -np.inf], [1.2*a0, 0.9*(xMax - xMin), xMax, np.inf]))

        fig = None
        if not dontplot:
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

    def get_fitted_plot(self, data_x, data_y, xLabel="", yLabel="", fig=None, axs=None, dontplot=False):
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
                                            bounds=([0.1*a0, -5/(xMax-xMin), 0.5/(xMax-xMin),       -np.pi, yMin],
                                                    [1.2*a0,  5/(xMax-xMin), 0.5/np.abs(np.min(dx)), np.pi, yMax]))

        if dontplot:
            fig = None
        else:
            if fig == None:
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

class DFitExponential:
    def __init__(self):
        pass

    def get_fitted_plot(self, data_x, data_y, xLabel="", rise = False, fig=None, axs=None, dontplot=False):
        def func(x, a, c, tau):
            return a * np.exp(-x/tau) + c

        data_x = data_x - np.min(data_x)

        xMin = np.min(data_x)
        xMax = np.max(data_x)
        yMin = np.min(data_y)
        yMax = np.max(data_y)

        #Calculate initial guesses...
        if rise:
            hgt = yMax-yMin
            c0 = yMin + hgt
            a0 = -hgt
        else:
            a0 = yMax-yMin
            c0 = yMin
        tau0 = (xMax-xMin)*0.5

        if rise:
            popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, c0, tau0],
                                             bounds=([2.0*a0, yMin, 0.01*tau0], [0, yMax, tau0*10]))
        else:
            popt, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, c0, tau0],
                                             bounds=([0, yMin, 0.01*tau0], [2.0*a0, yMax, tau0*10]))

        if not dontplot:
            if fig == None:
                fig, axs = plt.subplots(1)
            axs.plot(data_x, data_y, 'kx')
            axs.plot(data_x, func(data_x, *popt), 'r-')
            axs.set_xlabel(xLabel)
            axs.set_ylabel('IQ Amplitude')
        else:
            fig = None

        datapkt = {
            'amplitude' : np.abs(popt[0]),
            'offset' : popt[1],
            'decay_time' : popt[2],
            'fig'   : fig
        }

        return datapkt   

class DFitMinMax2D:
    def __init__(self):
        pass

    def get_fitted_plot(self, data_x, data_y, data_z, isMin=True, xLabel="", yLabel=""):
        fig, axs = plt.subplots(1)
        axs.pcolor(data_x, data_y, data_z.T, shading='auto')
        
        if isMin:
            ext_inds = np.unravel_index(data_z.argmin(), data_z.shape)
        else:
            ext_inds = np.unravel_index(data_z.argmax(), data_z.shape)

        axs.plot(data_x[ext_inds[0]], data_y[ext_inds[1]], 'rx')
        axs.set_xlabel(xLabel)
        axs.set_ylabel(yLabel)

        ext_vals = ( data_x[ext_inds[0]], data_y[ext_inds[1]] )

        datapkt = {
            'extremum' : ext_vals,
            'fig' : fig
        }

        return datapkt
            
class DFitCircle3D:
    def __init__(self):
        pass

    @staticmethod
    def _minimize_perp_distance(x, y, z):
        #Function taken from: https://stackoverflow.com/questions/35118419/wrong-result-for-best-fit-plane-to-set-of-points-with-scipy-linalg-lstsq
        def cost_func(params, xyz):
            a, b, c, d = params
            x, y, z = xyz
            length_squared = a**2 + b**2 + c**2
            return ((a * x + b * y + c * z + d) ** 2 / length_squared).sum() 

        def unit_length(params):
            a, b, c, d = params
            return a**2 + b**2 + c**2 - 1

        #Constrain the vector perpendicular to the plane be of unit length
        cons = ({'type':'eq', 'fun': unit_length})
        sol = scipy.optimize.minimize(cost_func, [1,1,1,0], args=[x, y, z], constraints=cons)
        return np.array(sol.x)
    
    @staticmethod
    def _cart_to_polar(x,y,z):
        r = np.sqrt(x*x + y*y + z*z)
        phi = np.arctan2(y,x)
        theta = np.arccos(z/r)
        return phi, theta

    def get_rotation_axis(self, data_x, data_y, data_z, is_polar = False):
        '''
        Returns the rotation axis for a given circle of points.
        
        Inputs:
            - data_x, data_y, data_z - arrays of x, y and z coordinates of the circle of points.
            - is_polar - (Default False) If True, the returned value is the phi and theta coordinates rather than a normalised R3 vector.
        '''

        norm_vec = DFitCircle3D._minimize_perp_distance(data_x, data_y, data_z)[:3]
        centroid = np.array([np.mean(data_x), np.mean(data_y), np.mean(data_z)]).T

        candTangent = np.vstack([data_x[1:]-data_x[:-1], data_y[1:]-data_y[:-1], data_z[1:]-data_z[:-1]]).T
        candRadial = np.vstack([data_x[1:], data_y[1:], data_z[1:]]).T - centroid
        
        orientations = np.cross(candRadial, candTangent)
        orientation = np.dot(orientations, norm_vec)
        if np.mean(orientation) < 0:
            norm_vec = -norm_vec
        if is_polar:
            return DFitCircle3D._cart_to_polar(*norm_vec)
        else:
            return norm_vec

