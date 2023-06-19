import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize

class DFitPeakLorentzian:
    def __init__(self):
        pass

    def get_fitted_plot(self, data_x, data_y, xLabel="", yLabel="IQ Amplitude", dip = False, axs=None, dontplot=False):
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
            if axs == None:
                fig, axs = plt.subplots(1)
            axs.plot(data_x, data_y, 'kx')
            axs.plot(data_x, func(data_x, *popt), 'r-')
            axs.set_xlabel(xLabel)
            axs.set_ylabel(yLabel)

        datapkt = {
            'amplitude' : popt[0],
            'width' : popt[1],
            'centre' : popt[2],
            'offset' : popt[3],
            'fig'   : fig
        }

        return datapkt

    def get_plot_data_from_dpkt(self, data_x, dpkt):
        def func(x, a, w, x0, c):
            return a * (0.5*w)**2/((x-x0)**2 + (0.5*w)**2) + c
        return func(data_x, dpkt['amplitude'], dpkt['width'], dpkt['centre'], dpkt['offset'])


class DFitFanoResonance:
    def __init__(self):
        #It fits a dip according to the equation given in: https://en.wikipedia.org/wiki/Fano_resonance
        pass

    def get_fitted_plot(self, data_x, data_y, xLabel="", yLabel="IQ Amplitude", axs=None, dontplot=False):
        def func(x, a, b, w, x0, c):
            return a * (b*0.5*w+x-x0)**2/((x-x0)**2 + (0.5*w)**2) + c

        xMin = np.min(data_x)
        xMax = np.max(data_x)

        dpkt = DFitPeakLorentzian().get_fitted_plot(data_x,data_y,dip=True,dontplot=True)

        #Calculate initial guesses by fitting a normal Lorentzian...
        c0 = dpkt['offset'] #0.5 * ( np.mean(data_y[:int(data_y.size*0.1)]) + np.mean(data_y[-int(data_y.size*0.1):]) )
        w0 = dpkt['width'] #0.2 * (xMax - xMin)
        a0 = dpkt['amplitude'] #np.min(data_y) - c0
        x00 = dpkt['centre'] #data_x[np.argmin(data_y)]

        r2 = 0
        b0_tries = [-1,-0.1,0,0.1,1]
        for b0 in b0_tries:
            poptNew, pcov = scipy.optimize.curve_fit(func, data_x, data_y, [a0, b0, w0, x00, c0], #method='dogbox',
                                                bounds=([1.5*a0, -np.inf, 0, xMin, -np.inf], [0, np.inf, 0.95*(xMax - xMin), xMax, np.inf]))
            residuals = data_y- func(data_x, *poptNew)
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((data_y-np.mean(data_y))**2)
            r2_new = 1 - (ss_res / ss_tot)
            if r2_new > r2:
                popt = poptNew
                r2 = r2_new
        
        #Calculate maxima and minima...
        w = popt[2]
        b = popt[1]
        x0 = popt[3]
        x1 = 0.5*(2*x0-b*w)
        x2 = (w+2*b*x0)/(2*b)
        if func(x1, popt[0], b, w, x0, popt[4]) > func(x2, popt[0], b, w, x0, popt[4]):
            xMinimum = x2
            xMaximum = x1
            yMinimum = func(x2, popt[0], b, w, x0, popt[4])
            yMaximum = func(x1, popt[0], b, w, x0, popt[4])
        else:
            xMinimum = x1
            xMaximum = x2
            yMinimum = func(x1, popt[0], b, w, x0, popt[4])
            yMaximum = func(x2, popt[0], b, w, x0, popt[4])

        fig = None
        if not dontplot:
            if axs == None:
                fig, axs = plt.subplots(1)
            axs.plot(data_x, data_y, 'kx')
            axs.plot(data_x, func(data_x, *popt), 'r-')
            axs.set_xlabel(xLabel)
            axs.set_ylabel(yLabel)

        datapkt = {
            'amplitude' : popt[0],
            'FanoFac':popt[1],
            'width' : popt[2],
            'centre' : popt[3],
            'offset' : popt[4],
            'xMinimum': xMinimum,
            'xMaximum': xMaximum,
            'yMinimum': yMinimum,
            'yMaximum': yMaximum,
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

    def get_fitted_plot(self, data_x, data_y, xLabel="", yLabel="IQ Amplitude", rise = False, fig=None, axs=None, dontplot=False):
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
            axs.set_ylabel(yLabel)
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
        # norm_vec = centroid*1.0

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

class DFitNotchResonance:
    def __init__(self):
        #It fits a dip according to the equation given in: https://en.wikipedia.org/wiki/Fano_resonance
        pass

    def get_fitted_plot(self, freq_vals, i_vals, q_vals, **kwargs):
        dont_plot_estimates = kwargs.get('dont_plot_estimates', False)
        prop_detrend_start = kwargs.get('prop_detrend_start', 0.05)
        prop_detrend_end = kwargs.get('prop_detrend_end', 0.05)

        #Setup the axes...
        if dont_plot_estimates:
            fig = plt.figure(); fig.set_figwidth(20)#; fig.set_figheight(7)
            #
            axFitAmp = plt.subplot(1, 3, 1)
            axFitPhs = plt.subplot(1, 3, 2)
            axFitIQ  = plt.subplot(1, 3, 3)
            #
            axFitAmp.grid(); axFitPhs.grid(); axFitIQ.grid()
        else:
            fig = plt.figure(); fig.set_figwidth(20)#; fig.set_figheight(7)
            #
            axWidth = plt.subplot(2, 4, 1); axWidth.set_title('Estimate Peak Width')
            axPhaseDetrend = plt.subplot(2, 4, 2)
            axPhaseSlopeEst = plt.subplot(2, 4, 3)
            axPhaseSlope = plt.subplot(2, 4, 4)
            #
            axFitAmp = plt.subplot(2, 3, 4)
            axFitPhs = plt.subplot(2, 3, 5)
            axFitIQ  = plt.subplot(2, 3, 6)
            #
            axWidth.grid(); axPhaseDetrend.grid(); axPhaseSlopeEst.grid(); axPhaseSlope.grid(); axFitAmp.grid(); axFitPhs.grid(); axFitIQ.grid()

        #Width estimation
        data_x, data_y = freq_vals, np.abs(i_vals + 1j*q_vals)
        if dont_plot_estimates:
            dpkt = DFitFanoResonance().get_fitted_plot(data_x, data_y**2, xLabel='Frequency (Hz)', yLabel='|IQ|^2', dontplot=True)
        else:
            dpkt = DFitFanoResonance().get_fitted_plot(data_x, data_y**2, xLabel='Frequency (Hz)', yLabel='|IQ|^2', axs=axWidth)
        #
        f0 = dpkt['xMinimum']
        Ql0 = f0/dpkt['width']
        a0 = np.sqrt(dpkt['offset'])

        #Phase detrending estimation
        phase_vals = np.unwrap(np.angle(i_vals + 1j*q_vals))
        #Take the average of the lines fitted to the the starting and ending sections...
        cut_ind = int(freq_vals.size*prop_detrend_start)
        coefs1 = np.polyfit(freq_vals[0:cut_ind], phase_vals[0:cut_ind], 1)
        cut_ind = int(freq_vals.size-freq_vals.size*prop_detrend_end)
        coefs2 = np.polyfit(freq_vals[cut_ind:], phase_vals[cut_ind:], 1)
        coefs = 0.5*(coefs1+coefs2)
        #Plot the line...
        poly1d_fn = np.poly1d(coefs)
        if not dont_plot_estimates:
            axPhaseDetrend.plot(freq_vals, phase_vals)
            poly1d_fn0 = np.poly1d(coefs1)
            axPhaseDetrend.plot(freq_vals, poly1d_fn0(freq_vals), 'k', alpha=0.5)
            poly1d_fn0 = np.poly1d(coefs2)
            axPhaseDetrend.plot(freq_vals, poly1d_fn0(freq_vals), 'k', alpha=0.5)
            axPhaseDetrend.plot(freq_vals, poly1d_fn(freq_vals), 'r')
            axPhaseDetrend.set_xlabel('Frequency (Hz)')
            axPhaseDetrend.set_ylabel('Phase (rad)')
            axPhaseDetrend.set_title('Estimate Phase Trend')
        #
        tau0 = coefs[0] / (2*np.pi)
        alpha0 = coefs[1]

        #Phase slope estimation
        detrended_phase = phase_vals - poly1d_fn(freq_vals)
        def smooth(y, box_pts):
            box = np.ones(box_pts)/box_pts
            y_smooth = np.convolve(y, box, mode='same')
            return y_smooth
        phase_derivs = np.diff(smooth(detrended_phase,5)) / np.diff(freq_vals)
        dfit = DFitPeakLorentzian()
        if dont_plot_estimates:
            dpkt = dfit.get_fitted_plot(freq_vals[:-1], phase_derivs, xLabel='Frequency (Hz)', yLabel='Phase Slope (rad/Hz)', dip=False, dontplot=True)
        else:
            dpkt = dfit.get_fitted_plot(freq_vals[:-1], phase_derivs, xLabel='Frequency (Hz)', yLabel='Phase Slope (rad/Hz)', dip=False, axs=axPhaseSlopeEst)
        ps = dpkt['amplitude']
        #Plot the Detrended+Slope Estimate...
        if not dont_plot_estimates:
            axPhaseSlopeEst.set_title('Estimate Phase Slope')
            axPhaseSlope.plot(freq_vals, phase_vals - poly1d_fn(freq_vals), alpha=0.5)
            tempYlims = axPhaseSlope.get_ylim()
            axPhaseSlope.plot(freq_vals, ps*(freq_vals-f0))
            axPhaseSlope.set_ylim(tempYlims)
            axPhaseSlope.set_xlabel('Frequency (Hz)')
            axPhaseSlope.set_ylabel('Detrended Phase (rad)')
            axPhaseSlope.set_title('Detrended Phase Slope')
        #
        Qc0 = Ql0*(f0*ps+2*Ql0)/(f0*ps)

        #Estimate phi
        # f0_ind = np.argmin(np.abs(freq_vals - f0))
        # tan_arg_res = q_vals[f0_ind] / i_vals[f0_ind]
        # #
        # func_phi = lambda phi: (tan_arg_res-2*np.pi*f0*tau0-alpha0) * (Qc0-Ql0*np.cos(phi)) + Ql0*np.sin(phi)
        # phi0 = scipy.optimize.fsolve(func_phi, 0)[0]
        phi0 = 0.0

        #Perform actual fitting...
        def func(f, params):
            a, tau, alpha, Ql, Qc, phi, f0 = params
            a = np.abs(a)
            Ql = np.abs(Ql)
            Qc = np.abs(Qc)
            return a*np.exp(1j*(2*np.pi*f*tau+alpha))*( 1-Ql/Qc*np.exp(1j*phi)/(1+2j*Ql*(f/f0-1)) )
        def cost_func(params, iq_vals):
            a, tau, alpha, Ql, Qc, phi, f0 = params
            iq_valsC = iq_vals[0] + 1j*iq_vals[1]
            func_vals = func(freq_vals, params)
            # return ( (np.abs(iq_valsC)-np.abs(func_vals))**2/np.abs(iq_valsC)**2 ).sum() + ( (np.angle(iq_valsC)-np.angle(func_vals))**2/np.angle(iq_valsC)**2 ).sum() + 1000*np.heaviside(Ql-Qc,1)
            # return (np.abs(iq_valsC - func_vals) * np.exp(-(freq_vals-f0)**2/(f0/Ql0)**2)).sum() + 1000*np.heaviside(Ql-Qc,1)
            return (np.abs(iq_valsC - func_vals)).sum() + 1000*np.heaviside(Ql-Qc,1)
        #
        def get_min_max(val1, val2):
            return min(val1,val2), max(val1,val2)
        #Run it once to refine the estimate for tau0 and alpha0, then run it with the same i.c.s to refine the estimate...
        for m in range(2):
            if m == 1:
                tau0, alpha0 = sol.x[1], sol.x[2]
            init_conds = [a0, tau0, alpha0, Ql0, Qc0, phi0, f0]
            sol = scipy.optimize.minimize(cost_func, init_conds, args=[i_vals, q_vals], method='Nelder-Mead',
                                            bounds = [
                                                get_min_max(a0*0.5,a0*2.0),
                                                get_min_max(tau0*0.25,tau0*4.0),
                                                get_min_max(alpha0*0.1,alpha0*10.0),
                                                get_min_max(Ql0*0.2,Ql0*5.0),
                                                get_min_max(Qc0*0.2,Qc0*5.0),
                                                get_min_max(-np.pi,np.pi),
                                                get_min_max((freq_vals[0]+f0)/2,(freq_vals[-1]+f0)/2)
                                            ])

        #Plot final fits...
        axFitAmp.plot(freq_vals,np.abs(i_vals + 1j*q_vals), alpha=0.5)
        axFitAmp.plot(freq_vals,np.abs(func(freq_vals, init_conds)))
        axFitAmp.plot(freq_vals,np.abs(func(freq_vals, sol.x)))
        axFitAmp.set_title('Fitted Amplitude'); axFitAmp.set_xlabel('Frequency (Hz)'); axFitAmp.set_ylabel('Amplitude')
        #
        axFitPhs.plot(freq_vals,phase_vals, alpha=0.5)
        axFitPhs.plot(freq_vals,np.unwrap(np.angle(func(freq_vals, init_conds))))
        axFitPhs.plot(freq_vals,np.unwrap(np.angle(func(freq_vals, sol.x))))
        axFitPhs.set_title('Fitted Phase'); axFitPhs.set_xlabel('Frequency (Hz)'); axFitPhs.set_ylabel('Phase (rad)')
        #
        axFitIQ.plot(i_vals,q_vals, alpha=0.5)
        axFitIQ.plot(np.real(func(freq_vals, init_conds)), np.imag(func(freq_vals, init_conds)))
        axFitIQ.plot(np.real(func(freq_vals, sol.x)), np.imag(func(freq_vals, sol.x)))
        axFitIQ.set_title('Fitted IQ'); axFitIQ.set_xlabel('I-Channel'); axFitIQ.set_ylabel('Q-Channel')

        if not dont_plot_estimates:
            fig.subplots_adjust(left=None, bottom=-1.1, right=None, top=None, wspace=None, hspace=None)

        # print(init_conds)
        # print(sol.x)
        return {
            'fres' : sol.x[6],
            'Qi' : sol.x[4]*sol.x[3]/(sol.x[4]-sol.x[3]),
            '|Qc|' : sol.x[4],
            'Ql' : sol.x[3],
            'arg(Qc)' : sol.x[5],
            'tau': sol.x[1],
            'alpha': sol.x[2],
            'ampl' : sol.x[0]
        }

class DFitReflectanceResonance:
    def __init__(self):
        #It fits a dip according to the equation given in P. Pakkiam's thesis.
        #https://unsworks.unsw.edu.au/entities/publication/6d9ea387-bc52-49d2-b5c2-6979779f4d30 (check Appendix D)
        pass

    def get_fitted_plot(self, freq_vals, i_vals, q_vals, **kwargs):
        dont_plot = kwargs.get('dont_plot', False)
        dont_plot_estimates = kwargs.get('dont_plot_estimates', False)
        prop_detrend_start = kwargs.get('prop_detrend_start', 0.05)
        prop_detrend_end = kwargs.get('prop_detrend_end', 0.05)
        phase_slope_smooth_num = kwargs.get('phase_slope_smooth_num', 25)
        assert phase_slope_smooth_num % 2 == 1, "Make sure \'phase_slope_smooth_num\' is an odd number."
        
        # iq_vals = i_vals + 1j*q_vals
        # iq_vals = iq_vals * np.exp(-1j*np.angle(iq_vals[0]))
        # i_vals, q_vals = np.real(iq_vals), np.imag(iq_vals)

        def get_min_max(val1, val2):
            return min(val1,val2), max(val1,val2)
        
        if not dont_plot:
            if dont_plot_estimates:
                fig, axs = plt.subplots(ncols=3); fig.set_figwidth(20)
                axAmp, axPhs, axIQ = axs
                axAmp.grid(); axPhs.grid(); axIQ.grid()
            else:
                fig = plt.figure(); fig.set_figwidth(15); fig.set_figheight(12)

                gs = fig.add_gridspec(2,6)
                axPhsDetrend = fig.add_subplot(gs[0, 0:2])
                axPhs = fig.add_subplot(gs[0, 2:4])
                axPhaseSlope = fig.add_subplot(gs[0, 4:6])
                axAmp = fig.add_subplot(gs[1, 0:3])
                axIQ = fig.add_subplot(gs[1, 3:6])
                gs.update(left=0.0,right=1.0,top=1.0,bottom=0.0,wspace=0.3,hspace=0.09)

                axAmp.grid(); axPhs.grid(); axPhsDetrend.grid(); axPhaseSlope.grid(); axIQ.grid()

        #Phase detrending estimation
        phase_vals = np.unwrap(np.angle(i_vals + 1j*q_vals))
        #Take the average of the lines fitted to the the starting and ending sections...
        cut_ind = int(freq_vals.size*prop_detrend_start)
        coefs1 = np.polyfit(freq_vals[0:cut_ind], phase_vals[0:cut_ind], 1)
        cut_ind2 = int(freq_vals.size-freq_vals.size*prop_detrend_end)
        coefs2 = np.polyfit(freq_vals[cut_ind2:], phase_vals[cut_ind2:], 1)
        coefs = 0.5*(coefs1+coefs2)
        # coefs[1] = coefs1[1]
        #Plot the line...
        poly1d_fn = np.poly1d(coefs)
        if not dont_plot and not dont_plot_estimates:
            axPhsDetrend.plot(freq_vals, phase_vals, 'k', alpha=0.5)
            poly1d_fn0 = np.poly1d(coefs1)
            axPhsDetrend.plot(freq_vals, poly1d_fn0(freq_vals), 'r', alpha=0.5)
            poly1d_fn0 = np.poly1d(coefs2)
            axPhsDetrend.plot(freq_vals, poly1d_fn0(freq_vals), 'r', alpha=0.5)
            axPhsDetrend.plot(freq_vals, poly1d_fn(freq_vals), 'r')
            axPhsDetrend.set_xlabel('Frequency (Hz)')
            axPhsDetrend.set_ylabel('Phase (rad)')
            axPhsDetrend.set_title('Estimate Phase Trend')
            axPhsDetrend.axvspan(freq_vals[0], freq_vals[cut_ind-1], alpha=0.2)
            axPhsDetrend.axvspan(freq_vals[cut_ind2-1], freq_vals[-1], alpha=0.2)

        #Phase slope estimation
        detrended_phase = phase_vals - poly1d_fn(freq_vals)
        def smooth(y, box_pts):
            box = np.ones(box_pts)/box_pts
            y_smooth = np.convolve(y, box, mode='valid')
            return y_smooth
        phase_slope_freqs = freq_vals[int((phase_slope_smooth_num-1)/2):int(freq_vals.size-(phase_slope_smooth_num+1)/2+1)]
        phase_derivs = np.diff(smooth(detrended_phase,phase_slope_smooth_num)) / np.diff(phase_slope_freqs)
        dfit = DFitPeakLorentzian()
        leDip = np.abs(np.min(phase_derivs)) > np.abs(np.max(phase_derivs))
        if dont_plot or dont_plot_estimates:
            dpkt = dfit.get_fitted_plot(phase_slope_freqs[:-1], phase_derivs, xLabel='Frequency (Hz)', yLabel='Phase Slope (rad/Hz)', dip=leDip, dontplot=True)
        else:
            dpkt = dfit.get_fitted_plot(phase_slope_freqs[:-1], phase_derivs, xLabel='Frequency (Hz)', yLabel='Phase Slope (rad/Hz)', dip=leDip, axs=axPhaseSlope)
        ps = dpkt['amplitude']
        f0 = dpkt['centre']
        #Plot the Detrended+Slope Estimate...
        if not dont_plot:
            axPhs.plot(freq_vals, phase_vals - poly1d_fn(freq_vals), 'k', alpha=0.5)
            if not dont_plot_estimates:
                tempYlims = axPhs.get_ylim()
                axPhs.plot(freq_vals, ps*(freq_vals-f0), 'r', alpha=0.5)
                axPhs.set_ylim(tempYlims)
                axPhs.set_xlabel('Frequency (Hz)')
                axPhs.set_ylabel('Detrended Phase (rad)')
                axPhs.set_title('Estimate Phase Slope')
                axPhaseSlope.set_title(f'Detrended Phase Slope (smoothed {phase_slope_smooth_num})')

        #Min-Max Amplitude Estimation
        data_x, data_y = freq_vals, np.abs(i_vals + 1j*q_vals)
        dpkt = DFitPeakLorentzian().get_fitted_plot(data_x, data_y, xLabel='Frequency (Hz)', yLabel='|IQ|', dip=True, dontplot=True)
        #
        Vmin, Vmax = get_min_max(dpkt['amplitude']+dpkt['offset'], dpkt['offset'])
        if not dont_plot:
            axAmp.plot(data_x, data_y, 'k', alpha=0.5)
            if not dont_plot_estimates:
                y_data = DFitPeakLorentzian().get_plot_data_from_dpkt(data_x, dpkt)
                axAmp.plot(data_x, y_data, 'r', alpha=0.5)

        #Calculate initial estimates - check Table D.1
        w0 = f0*2*np.pi
        k = Vmax
        h = 1/k*(Vmax - Vmin)
        p = ps/(np.pi*2)
        Qint = (h-1)*w0/(h*(h-2))*np.abs(p)
        if p > 0:
            Qext = -(h-1)*w0/h**2*p
        else:
            Qext = (h-1)*w0/(h-2)**2*p
        p0 = coefs[0]/(np.pi*2)
        phi0 = coefs[1]
        l = coefs[0]*3e8/(4*np.pi)

        #Perform actual fitting...
        def func(f, params):
            k, Qint, Qext, f0, l, phi = params
            return -k * (1-Qext/Qint*(1+1j*Qint*(f/f0-f0/f))) / (1+Qext/Qint*(1+1j*Qint*(f/f0-f0/f))) * np.exp(2j*2*np.pi*f*l/3e8) * np.exp(1j*phi)
        def cost_func(params, iq_vals):
            iq_valsC = iq_vals[0] + 1j*iq_vals[1]
            func_vals = func(freq_vals, params)
            k, Qint, Qext, f0, l, phi = params
            return (np.abs(iq_valsC - func_vals)*np.exp((freq_vals-f0)**2/(freq_vals[-1]-freq_vals[0])**2)).sum()
            # return (np.abs(iq_valsC - func_vals)).sum()
        #
        #Run it once to refine the estimate for tau0 and alpha0, then run it with the same i.c.s to refine the estimate...
        init_conds = [k, Qint, Qext, f0, l, phi0]
        sol = scipy.optimize.minimize(cost_func, init_conds, args=[i_vals, q_vals], method='Nelder-Mead',
                                        bounds = [
                                            get_min_max(k*0.5,k*1.5),
                                            get_min_max(Qint*0.5,Qint*2.0),
                                            get_min_max(Qext*0.5,Qext*2.0),
                                            ((np.min(freq_vals)+f0)*0.5, (np.max(freq_vals)+f0)*0.5),
                                            get_min_max(l*0.5,l*1.5),
                                            get_min_max(phi0*0.75,phi0*1.25)
                                        ])

        if not dont_plot:
            axAmp.plot(freq_vals,np.abs(func(freq_vals, init_conds)))
            axAmp.plot(freq_vals,np.abs(func(freq_vals, sol.x)))
            axAmp.legend(['Data', 'Helper', 'Guess', 'Fitted'])
            axAmp.set_xlabel('Frequency (Hz)')
            axAmp.set_ylabel('Amplitude')

            axPhs.plot(freq_vals,np.angle(func(freq_vals, init_conds[:4]+[0,0])))
            axPhs.plot(freq_vals,np.angle(func(freq_vals, sol.x[:4].tolist()+[0,0])))

            axIQ.plot(i_vals, q_vals, 'k', alpha=0.5)
            axIQ.plot(np.real(func(freq_vals, init_conds)), np.imag(func(freq_vals, init_conds)))
            axIQ.plot(np.real(func(freq_vals, sol.x)), np.imag(func(freq_vals, sol.x)))
            axIQ.legend(['Data', 'Guess', 'Fitted'])
            axIQ.set_xlabel('I-Channel')
            axIQ.set_ylabel('Q-Channel')

        return {
            'fres' : sol.x[3],
            'Qint' : sol.x[1],
            'Qext' : sol.x[2],
            'Qeff' : sol.x[1]*sol.x[2]/(sol.x[1]+sol.x[2]),
            'Length': sol.x[4],
            'Amplitude': sol.x[0],
            'Phase' : sol.x[5]
        }
