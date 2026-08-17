from sqdtoolz.Utilities.FileIO import FileIOReader
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.GENmwSource import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*
from sqdtoolz.HAL.ZI.ZIQubit import ZIQubit
from sqdtoolz.HAL.ZI.ZIACQ import ZIACQ
from sqdtoolz.HAL.SOFTqpu import SOFTqpu
from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.HAL.ZI.ZIQuantumElement import ZIQuantumElement
from sqdtoolz.HAL.ZI.QuantumElements.TunableTransmonCouplerFixed import TunableTransmonCouplerFixed
from scipy.signal import savgol_filter
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from sqdtoolz.Experiments.Experimental.ZI import cryo_scope
from sqdtoolz.Utilities.Flattenator import Flattenator
import numpy as np
import warnings

class ExpZICryoscope:
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._name = name
        self._expt_config = expt_config
        self._hal_QPU = hal_QPU
        self._isY = 0
        self._qubit_ids = qubit_ids
        self.cur_coupler_obj = hal_QPU.get_coupler_obj_from_qubits(qubit_ids[0], qubit_ids[1], TunableTransmonCouplerFixed)
        self._kwargs = kwargs
        self.nyquist_oder = kwargs.pop('nyquist_order', 0)
        assert len(self._qubit_ids) >1 , "Also must define a second qubit as it will attempt to optimise a pulse specific to each coupler element"

        self._amplitudes = kwargs.pop('amplitudes', np.linspace(0.3, 0.3, 1))
        self._lengths = kwargs.pop('lengths', np.linspace(0.0, 300e-9, (1/2.0)*1e-9))
        self._transition = kwargs.pop('transition', 'ge')

        self._normalise_data = kwargs.pop('normalise_data', True)
        self.data = {}
        self.temp = 0

        self.f_max = kwargs.pop('f_max', None)
        if self.f_max is None and self._hal_QPU.get_qubit_obj(qubit_ids[0]).FluxConversionParams is not None:
            self.f_max = self._hal_QPU.get_qubit_obj(qubit_ids[0]).FluxConversionParams['f_max']
        self.Ec_over_h = kwargs.pop('Ec_over_h', None)
        assert self.Ec_over_h is not None, "Must provide Ec_over_h for the qubit to convert frequency shift to flux for pulse reconstruction."
        self.norm_window = kwargs.pop('norm_window', None)

        qubit = self._qubit_ids[0]

        lab.group_open(self._name)
        # x90 - measures <Y>
        exp_X = ExpZIqubit(f'cryoscope_{qubit}_X90', self._expt_config, cryo_scope, self._hal_QPU, self._qubit_ids, 
                         lengths=self._lengths, 
                         amplitudes=self._amplitudes,
                         y90=False,
                         **self._kwargs
                         )
        lab.run_single(exp_X, **kwargs)
        #
        dataX90 = exp_X.retrieve_last_dataset(qubit)
        if self._normalise_data:
            self.data['calibX'] = exp_X.retrieve_last_dataset(qubit+'_calib')

        # y90 - measures <X>
        exp_Y = ExpZIqubit(f'cryoscope_{qubit}_Y90', self._expt_config, cryo_scope, self._hal_QPU, self._qubit_ids, 
                        lengths=self._lengths, 
                        amplitudes=self._amplitudes,
                        y90=True,
                        **self._kwargs
                        )
        lab.run_single(exp_Y, **kwargs)
        #
        dataY90 = exp_Y.retrieve_last_dataset(qubit)
        if self._normalise_data:
            self.data['calibY'] = exp_Y.retrieve_last_dataset(qubit+'_calib')

        lab.group_close()

        self.data['Y'] = dataX90.get_numpy_array()
        self.data['X'] = dataY90.get_numpy_array()
        self.data['tau'] = dataX90.param_vals[1]
        self.data['amplitude'] = dataX90.param_vals[0]

    def post_process(self, filter_window_length=7, polyorder=2):
        assert isinstance(filter_window_length, int) and filter_window_length > 0, "filter_window_length must be a positive integer"
        assert isinstance(polyorder, int) and polyorder >= 0, "polyorder must be a non-negative integer"
        assert filter_window_length > polyorder, "filter_window_length must be greater than polyorder"

        num_amps = len(self.data['amplitude'])
        assert len(self.data['X']) == len(self.data['Y'])

        if self._normalise_data:
            dnormX = ExpZIqubit.normalise_qubit_data(self.data['calibX'], self._transition)
            dnormY = ExpZIqubit.normalise_qubit_data(self.data['calibY'], self._transition)
            self.data['Ynorm'] = [2*dnormY.normalise_data(self.data['Y'][i], ax=None)-1 for i in range(num_amps)]
            self.data['Xnorm'] = [2*dnormX.normalise_data(self.data['X'][i], ax=None)-1 for i in range(num_amps)]
            self.data['C'] = [np.asarray(x) + 1j * np.asarray(y) for x, y in zip(self.data['Xnorm'], self.data['Ynorm'])]

        tau = np.asarray(self.data['tau'], dtype=float)
        n = len(tau)
        dtau = tau[1] - tau[0] #dt

        # SG filter params
        wl = min(filter_window_length, n if n % 2 else n - 1)
        if wl % 2 == 0:
            wl -= 1
        wl = max(wl, polyorder + 1 + (polyorder + 1) % 2 + 1)
        assert wl < n, f"Not enough points ({n}) for Savitzky-Golay window {wl}; use more length points or a smaller window_length."

        # flux normalisation window
        if self.norm_window is None:
            self.norm_window = (int(0.8 * n), n)
        else:
            assert isinstance(self.norm_window, tuple) and len(self.norm_window) == 2, "norm_window must be a tuple of (start_index, end_index)"
            assert 0 <= self.norm_window[0] < self.norm_window[1] <= n, "norm_window indices must be within the range of tau data"

        freqs = np.fft.fftfreq(n, d=dtau)
        f0 = self.f_max + self.Ec_over_h

        # frequency demodulation and phase extraction
        f_demod_arr = np.zeros(num_amps)
        phase_arr = np.zeros((num_amps, n))
        delta_f_R_raw = np.zeros((num_amps, n))
        delta_f_R = np.zeros((num_amps, n))
        Phi_R = np.zeros((num_amps, n))
        s_arr = np.zeros((num_amps, n))
        norm_value_arr = np.zeros(num_amps)
        spec_arr = np.zeros((num_amps, n), dtype=complex)
        #
        for i in range(num_amps):
            C_i = np.asarray(self.data['C'][i])
            spec = np.fft.fft(C_i - np.mean(C_i)) # subtract DC offset
            f_demod = freqs[np.argmax(np.abs(spec))] # demodulation frequency for this amplitude

            residual = C_i * np.exp(-1j * 2 * np.pi * f_demod * tau) # demodulated signal
            phase_residual = np.unwrap(np.angle(residual))
            phase = phase_residual

            delta_f_raw = np.gradient(phase, dtau) / (2 * np.pi) + f_demod + 0.5*self.nyquist_oder*1/((tau[1] - tau[0])) # raw frequency shift from phase derivative

            # filter the phase derivative to reduce noise
            dphi_dtau = savgol_filter(phase, window_length=filter_window_length, polyorder=polyorder, deriv=1, delta=dtau, mode='nearest')
            delta_f = dphi_dtau / (2 * np.pi) + f_demod + 0.5*self.nyquist_oder*1/((tau[1] - tau[0]))

            arg = np.clip(1 - delta_f / f0, -1.0, 1.0)
            phi_r = np.arccos(arg ** 2) / np.pi

            # normalise flux from given window (defaults to last 20% of signal)
            norm_value = np.mean(phi_r[self.norm_window[0]:self.norm_window[1]])
            if not np.isfinite(norm_value) or abs(norm_value) < 1e-6:
                warnings.warn(f"amplitude[{i}]={self.data['amplitude'][i]:.3f}: normalisation ~0, likely f_demod aliasing (Nyquist wrapping) -- distrust this trace.")

            f_demod_arr[i] = f_demod
            phase_arr[i] = phase
            delta_f_R_raw[i] = delta_f_raw
            delta_f_R[i] = delta_f
            Phi_R[i] = phi_r
            s_arr[i] = phi_r / norm_value
            norm_value_arr[i] = norm_value
            spec_arr[i] = spec

        # store values
        self.data['f_demod'] = f_demod_arr
        self.data['phase'] = phase_arr
        self.data['delta_f_R_raw'] = delta_f_R_raw
        self.data['delta_f_R'] = delta_f_R
        self.data['Phi_R'] = Phi_R
        self.data['s'] = s_arr
        self.data['norm_value'] = norm_value_arr
        self.data['spec'] = spec_arr
        self.data['freqs'] = freqs

    def plot_calibrated_traces(self):
        if not self._normalise_data:
            return
        fig, (ax_x, ax_y, ax_phi) = plt.subplots(3, 1, figsize=(12, 6), sharex=True)
        fig.suptitle(f"{self._qubit_ids[0]}: Cryoscope")
        tau_ns = self.data['tau'] * 1e9
        for i, amp in enumerate(self.data['amplitude']):
            x_ampl = self.data['Xnorm'][i]
            y_ampl = self.data['Ynorm'][i]
            phi = np.arctan2(y_ampl, x_ampl)
            label = r"$\mathcal{A}=$" + f"{amp:.2f}"
            ax_x.plot(tau_ns, x_ampl, label=label)
            ax_y.plot(tau_ns, y_ampl, label=label)
            ax_phi.plot(tau_ns, phi, label=label)
        ax_x.set_ylabel(r'$\langle X \rangle$')
        ax_x.set_xlim([tau_ns.min(), tau_ns.max()])
        ax_x.legend(loc="lower left", fontsize=7, ncol=2)
        ax_y.set_ylabel(r'$\langle Y \rangle$')
        ax_phi.set_xlabel(r'$\tau$ (ns)')
        ax_phi.set_ylabel(r'$\phi$')
        fig.tight_layout()
        return fig

    def plot_fft_grid(self, max_amps=5, amp_indices=None, n_peaks=3):
        num_amps = len(self.data['amplitude'])
        if amp_indices is None:
            n_show = min(max_amps, num_amps)
            amp_indices = np.unique(np.linspace(0, num_amps - 1, n_show).astype(int))
        n_cols = len(amp_indices)

        freqs = self.data['freqs']
        order = np.argsort(freqs)
        freqs_sorted = freqs[order] / 1e6
        nyquist = freqs.max() / 1e6

        fig = plt.figure(figsize=(4 * n_cols, 4.5))
        gs = GridSpec(2, n_cols, figure=fig, height_ratios=[2, 1.3], hspace=0.45, wspace=0.35)

        for col, i in enumerate(amp_indices):
            amp = self.data['amplitude'][i]
            ax = fig.add_subplot(gs[0, col])
            mag = np.abs(self.data['spec'][i])[order]
            ax.plot(freqs_sorted, mag, color='C0')

            peak_idx = np.argsort(np.abs(self.data['spec'][i]))[::-1][:n_peaks]
            for rank, pk in enumerate(peak_idx):
                color = 'C1' if rank == 0 else '0.6'
                ax.axvline(freqs[pk] / 1e6, color=color, lw=1.2 if rank == 0 else 0.8,
                           ls='--', label='chosen f_demod' if rank == 0 else None)

            ax.axvspan(nyquist * 0.9, nyquist, color='r', alpha=0.08)
            ax.axvspan(-nyquist, -nyquist * 0.9, color='r', alpha=0.08)
            ax.set_title(r"$\mathcal{A}=$" + f"{amp:.2f}\n" + r"$f_\mathrm{demod}=$" + f"{self.data['f_demod'][i]/1e6:.1f} MHz")
            ax.set_xlabel("Frequency (MHz)")
            if col == 0:
                ax.set_ylabel("|FFT|")
                ax.legend(fontsize=7)

        ax_summary = fig.add_subplot(gs[1, :])
        ax_summary.plot(self.data['amplitude'], self.data['f_demod'] / 1e6, '-', color='0.6', zorder=1)
        ax_summary.scatter(self.data['amplitude'], self.data['f_demod'] / 1e6, color='0.6', s=15, zorder=2)
        ax_summary.scatter(self.data['amplitude'][amp_indices], self.data['f_demod'][amp_indices] / 1e6,
                            color='C1', s=40, zorder=3, label='shown above')
        ax_summary.axhline(nyquist, color='r', lw=0.8, ls=':')
        ax_summary.axhline(-nyquist, color='r', lw=0.8, ls=':')
        ax_summary.set_ylim([0, self.data['f_demod'].max() / 1e6 * 1.2])
        ax_summary.set_xlabel("Flux pulse amplitude")
        ax_summary.set_ylabel(r"$f_\mathrm{demod}$ (MHz)")
        fig.suptitle(f"{self._qubit_ids[0]}: FFT spectra used for demodulation (red = near/at Nyquist)", y=1.02)

        return fig

    def plot_amplitude_grid(self, max_amps=5, amp_indices=None):
        num_amps = len(self.data['amplitude'])
        if amp_indices is None:
            n_show = min(max_amps, num_amps)
            amp_indices = np.unique(np.linspace(0, num_amps - 1, n_show).astype(int))
        n_cols = len(amp_indices)

        tau_ns = self.data['tau'] * 1e9
        norm_lo, norm_hi = self.norm_window

        fig = plt.figure(figsize=(4 * n_cols, 9))
        gs = GridSpec(3, n_cols, figure=fig, hspace=0.35, wspace=0.35)

        for col, i in enumerate(amp_indices):
            amp = self.data['amplitude'][i]

            # frequency shift
            ax_det = fig.add_subplot(gs[0, col])
            ax_det.plot(tau_ns, self.data['delta_f_R_raw'][i] / 1e6, color='0.7', label='raw')
            ax_det.plot(tau_ns, self.data['delta_f_R'][i] / 1e6, color='C1', label='SG filtered')
            ax_det.set_title(r"$\mathcal{A}=$" + f"{amp:.2f}")
            if col == 0:
                ax_det.set_ylabel(r"$\Delta f_R$ (MHz)")
                ax_det.legend(fontsize=7)

            # flux relative
            ax_flux = fig.add_subplot(gs[1, col], sharex=ax_det)
            ax_flux.plot(tau_ns, self.data['Phi_R'][i], color='C0')
            ax_flux.axvspan(tau_ns[norm_lo], tau_ns[norm_hi - 1], color='0.85', label='normalisation window')
            ax_flux.axhline(self.data['norm_value'][i], color='k', lw=0.8, ls='--')
            if col == 0:
                ax_flux.set_ylabel(r"$\Phi_R / \Phi_0$")
                ax_flux.legend(fontsize=7)

            ax_s = fig.add_subplot(gs[2, col], sharex=ax_det)
            ax_s.plot(tau_ns, self.data['s'][i], color='C2')
            ax_s.axhline(1.0, color='k', lw=0.8, ls='--')
            ax_s.set_xlabel(r"$\tau$ (ns)")
            if col == 0:
                ax_s.set_ylabel("Normalized s(t)")

        fig.suptitle(f"{self._qubit_ids[0]}: Cryoscope reconstruction per amplitude")
        return fig

    def plot_summary(self):
        self.plot_calibrated_traces()
        self.plot_fft_grid()
        self.plot_amplitude_grid()

    def fit_step_response(self, amplitude_index=0, update_coupler=True):
        if len(self._amplitudes) > 1:
            normalised_step_response = self.data['s'][amplitude_index, :]
        else:
            normalised_step_response = self.data['s'][0,:]
        compensation_kernel = ExpZICryoscope.fit_step_response_from_s_data(normalised_step_response)

        if update_coupler:
            self.cur_coupler_obj.Pulse['precomp_kernel'] = compensation_kernel
            print(f"Updated lab.HAL({self.cur_coupler_obj}).Pulse['precomp_kernel'] with fitted step response.")

    @staticmethod
    def fit_step_response_from_s_data(normalised_step_response):
        raw_step_response = (normalised_step_response-1)*1+1 #Rescale it to see if it helps...
        pc = Flattenator()
        pc.fit_step_response(raw_step_response, num_poles=5, num_zeros=5, num_samples_missing=1, plot_response=True)
        return pc.get_compensation_kernel()*1.0
    

        
