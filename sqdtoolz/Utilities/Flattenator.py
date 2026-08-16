import numpy as np
import scipy.signal
import scipy.optimize
import scipy.linalg
import matplotlib.pyplot as plt

class Flattenator:
    def __init__(self):
        self._zeros = []
        self._poles = []
        self._gainK = []
        self._cur_fit = None

    @staticmethod
    def _pack_poles_zeroes_gain(x, num_poles, num_zeros):
        cur_ind = 0
        poles, zeros = [], []
        #Poles
        for m in range(num_poles // 2):
            r, theta = x[cur_ind:cur_ind+2]; cur_ind += 2
            p = r * np.exp(1j * theta)
            poles += [p, p.conjugate()]
        if num_poles % 2:
            poles.append(x[cur_ind]); cur_ind += 1
        #Zeroes
        for m in range(num_zeros // 2):
            r, theta = x[cur_ind:cur_ind+2]; cur_ind += 2
            z = r * np.exp(1j * theta)
            zeros += [z, z.conjugate()]
        if num_zeros % 2:
            zeros.append(x[cur_ind]); cur_ind += 1
        #
        return np.asarray(zeros), np.asarray(poles), x[cur_ind]

    def fit_step_response(self, step_resp:np.ndarray, num_poles, num_zeros=None, num_samples_missing=0, plot_response=False):
        """
        Give the raw data for the step-response and perform model-determination assuming a causal BIBO-stable system.

        Inputs:
            step_resp - Step response as a real-valued array
            num_poles - Number of poles to trial inside the unit-circle. Note that all complex poles will be conjugate pairs and one pole is real-valued if num_poles is odd.
            num_zeros - Number of zeros to trial inside the unit-circle. Note that all complex zeros will be conjugate pairs and one pole is real-valued if num_zeros is odd.
            num_samples_missing - If the step response is given later with a few samples dropped, the optimiser accounts for this and only looks after num_samples_missing points
            plot_response - Plot the model fitting if True.            
        """
        N = step_resp.shape[0] + num_samples_missing
        num_zeros = num_poles - 1 if num_zeros is None else num_zeros
        assert num_zeros <= num_poles, "A causal BIBO stable system cannot have zeroes exceeding the number of poles (within the unit-circle)."

        #Initial guess (canonical form being H(z)=K.A(z)/B(z) with A and B being polynomials with real coefficients...)
        x0 = []
        #Poles
        for m in range(num_poles // 2):    #Conjugate poles
            x0 += [0.9, 0.2]
        if num_poles % 2:  #Real Pole if odd order
            x0 += [0.8]
        #Zeroes
        for m in range(num_zeros // 2):    #Conjugate poles
            x0 += [0.8, 0.5]
        if num_zeros % 2:  #Real Pole if odd order
            x0 += [0.0]
        #Gain
        x0 += [step_resp[-1]]   #Take the steady-state value as the estimated gain

        #Bounds: poles must be strictly within unit circle while zeroes can live anywhere.
        lbs, hbs = [], []
        #Poles
        for m in range(num_poles // 2):
            lbs += [1e-6, 1e-6]
            hbs += [0.999999, np.pi - 1e-6]
        if num_poles % 2:
            lbs += [-0.999999]
            hbs += [0.999999]
        #Zeroes
        for m in range(num_zeros // 2):
            lbs += [0.0, -np.pi]
            hbs += [np.inf, np.pi]
        if num_zeros % 2:
            lbs += [-np.inf]
            hbs += [np.inf]
        #Gain
        lbs += [-np.inf]
        hbs += [np.inf]

        def step_resp_sim_zpk(x):
            z, p, k = Flattenator._pack_poles_zeroes_gain(x, num_poles, num_zeros)
            b, a = scipy.signal.zpk2tf(z, p, k)         #An awesome function that returns the polynomial coefficients given poles/zeroes!
            _, yhat = scipy.signal.dstep((b, a, 1.0), n=N)   #Another awesome function that yields the step-response given a polynomial zpk-model
            return np.squeeze(yhat).real

        result = scipy.optimize.least_squares(lambda x: step_resp_sim_zpk(x)[num_samples_missing:] - step_resp, x0, bounds=(lbs, hbs))

        leZeroes, lePoles, leGain = Flattenator._pack_poles_zeroes_gain(result.x, num_poles, num_zeros)
        b, a = scipy.signal.zpk2tf(leZeroes, lePoles, leGain)

        self._zeros = leZeroes
        self._poles = lePoles
        self._gainK = leGain
        self._cur_fit = step_resp_sim_zpk(result.x)
        self._raw_data = step_resp*1.0
        self._num_samples_missing = num_samples_missing
        self._impulse_resp = np.concatenate([[self._cur_fit[0]], np.diff(self._cur_fit)])

        #Calculate compensating convolution kernel by using LSQ on impulse response - i.e.
        #   y[n] = H[n]*g[n] = delta[n]
        #Thus, on finding g[n] (by associativity of convolution):
        #   y[n] = H[n]*(g[n]*x[n]) = (H[n]*g[n])*x[n] = delta[n]*x[n] = x[n]
        #
        targ_step_amplitude = 1.00
        y_targ = np.array([targ_step_amplitude]+[0.0]*(self._raw_data.shape[0]-1))
        #This method is more robust as it works for responses over/under the size of the impulse response...
        matH = np.array([np.concatenate([[0]*x, self._impulse_resp, [0]*(max(0,y_targ.size-x-self._impulse_resp.size))])[:y_targ.size] for x in range(y_targ.size)]).T
        #
        U, s, Vh = np.linalg.svd(matH, full_matrices=False)
        tol = max(matH.shape) * np.spacing(np.max(s))
        s_inv = np.array([1 / val if val > tol else 0 for val in s])
        X = (Vh.T * s_inv) @ (U.T @ y_targ)
        self._comp_kernel = X

        if plot_response:
            self.plot_response()

    def plot_response(self):
        assert not (self._cur_fit is None), "Must run fit_step_response first."

        t_samples = np.arange(self._num_samples_missing + self._raw_data.shape[0])

        fig = plt.figure(figsize=(10, 7))
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1, 1], hspace=0.3, wspace=0.3)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])
        ax2.set_box_aspect(1)

        ax1.plot(t_samples[self._num_samples_missing:], self._raw_data, label="Measured")
        ax1.plot(t_samples, self._cur_fit, "--", label="Model")
        ax1.set_xlabel("Sample")
        ax1.set_ylabel("Step response")
        ax1.grid(True)
        ax1.legend()

        for cur_zero in self._zeros:
            ax2.plot([np.real(cur_zero)], [np.imag(cur_zero)], 'bo')
        for cur_pole in self._poles:
            ax2.plot([np.real(cur_pole)], [np.imag(cur_pole)], 'rx')
        theta = np.linspace(0, 2 * np.pi, 100)
        x = np.cos(theta)
        y = np.sin(theta)
        ax2.plot(x,y, 'k', linestyle='dashed')
        ax2.set_aspect("equal")
        ax2.grid(); ax2.axhline(0, color='black') and ax2.axvline(0, color='black')

        ax3.plot(self._comp_kernel)
        ax3.set_xlabel('Sample')
        ax3.set_ylabel('Compensating Kernel')
        ax3.grid()

        N = self._raw_data.shape[0]
        ax4.plot(self._raw_data, label="Measured")
        ax4.plot(np.convolve(self._comp_kernel, [1.0]*N, mode='full')[:N], label="Comp. Pulse")
        ax4.set_xlabel('Sample')
        ax4.set_ylabel('Step response')
        ax4.legend(); ax4.grid()
    
    def get_compensation_kernel(self):
        assert not (self._cur_fit is None), "Must run fit_step_response first."
        return self._comp_kernel
