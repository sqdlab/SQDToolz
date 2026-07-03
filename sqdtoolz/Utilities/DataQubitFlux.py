import numpy as np
from sqdtoolz.Utilities.FileIO import FileIODirectory
from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

class DataTransmonFlux:
    """
    Fit flux sweeps of transmon qubit spectroscopy.
    """
    def __init__(self, qubit_id, qubit_ampl, fluxDC, frequencies):
        self._qubit_id = qubit_id
        self._qubit_amp = np.array(qubit_ampl)
        self._fluxDC = np.array(fluxDC)
        self._frequencies = np.array(frequencies)
        self._qubit_amp_fit = None
    
    @classmethod
    def calibrateQubitFluxFromFile(cls, file_path, flux_param_index=0, freq_param_index=1, iq_indices=[0,1], background_subtraction=True, qubit_id=None):
        cur_data = FileIODirectory(file_path)
        #
        assert (flux_param_index != freq_param_index) and flux_param_index < len(cur_data.param_names) and freq_param_index < len(cur_data.param_names), \
            f"Provide correct parameter indices for frequency and flux (param: {cur_data.param_names})"
        if qubit_id:
            assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        else:
            qubit_id = Path(file_path).stem
        #
        arr = cur_data.get_numpy_array()
        ampl = np.sqrt(arr[:,:,0]**2 + arr[:,:,1]**2)
        if background_subtraction:
            ampl_corrected = (ampl.T - np.nanmean(ampl, axis=1)).T
        else:
            ampl_corrected = ampl
        return cls(qubit_id, ampl_corrected, cur_data.param_vals[flux_param_index], cur_data.param_vals[freq_param_index])


    def fit_qubit_frequency(self, p0=None, prominence_frac=0.9, fixed_period=None, fit_flux_range=None):
        """
        Fits qubit frequency vs flux using the standard transmon flux dependence:
            f(flux) = f_max * sqrt(|cos(pi * (flux - flux0) / period)|) + offset

        Tune prominence_frac to adjust peak detection (lower prominence -> higher sensitivity)

        fit_flux_range: optional (min, max) tuple to restrict which flux values are
        used in the fit (peak extraction still happens over the full dataset; only
        the fit itself is restricted).
        """
        def extract_peak_freq(freq_vals, row):
            prominence_thresh = prominence_frac * (np.nanmax(row) - np.nanmin(row))
            peak_idx, props = find_peaks(row, prominence=prominence_thresh)
            if len(peak_idx) == 0:
                return np.nan
            idx = peak_idx[np.argmax(props['prominences'])]
            return freq_vals[idx]

        peak_freqs_all = np.array([
            extract_peak_freq(self._frequencies, row) for row in self._qubit_amp
        ])
        valid = ~np.isnan(peak_freqs_all)

        # Restrict to fit_flux_range if provided
        if fit_flux_range is not None:
            in_range = (self._fluxDC >= fit_flux_range[0]) & (self._fluxDC <= fit_flux_range[1])
            valid = valid & in_range

        flux_valid = self._fluxDC[valid]
        peak_freqs_valid = peak_freqs_all[valid]
        assert len(peak_freqs_valid) > 0, "No rows had a peak satisfying find_peaks within fit_flux_range; try lowering prominence_frac or widening fit_flux_range."

        def transmon_flux_model(x, f_max, flux0, period, offset):
            return f_max * np.sqrt(np.abs(np.cos(np.pi * (x - flux0) / period))) + offset

        if fixed_period is not None:
            def transmon_flux_model_fixed_period(x, f_max, flux0, offset):
                return transmon_flux_model(x, f_max, flux0, fixed_period, offset)
            if p0 is None:
                f_max_guess = 4e9
                offset_guess = 0
                flux0_guess = 0
                p0 = [f_max_guess, flux0_guess, offset_guess]
            else:
                assert len(p0) == 3, "p0 must be [f_max, flux0, offset] when fixed_period is provided."
            popt_fit, pcov = curve_fit(
                transmon_flux_model_fixed_period, flux_valid, peak_freqs_valid, p0=p0, maxfev=20000
            )
            f_max, flux0, offset = popt_fit
            popt = np.array([f_max, flux0, fixed_period, offset])
        else:
            if p0 is None:
                f_max_guess = 4e9
                offset_guess = 0
                flux0_guess = 0
                period_guess = 3
                p0 = [f_max_guess, flux0_guess, period_guess, offset_guess]
            else:
                assert len(p0) == 4, "p0 must be [f_max, flux0, period, offset] when no fixed_period is provided."
            popt, pcov = curve_fit(
                transmon_flux_model, flux_valid, peak_freqs_valid, p0=p0, maxfev=20000
            )
        self._qubit_amp_fit = {
            'peak_freqs': peak_freqs_all,
            'peak_freqs_valid': peak_freqs_valid,
            'flux_valid': flux_valid,
            'valid_mask': valid,
            'popt': popt,
            'pcov': pcov,
            'f_max': popt[0],
            'flux0': popt[1],
            'period': popt[2],
            'offset': popt[3],
            'fit_func': transmon_flux_model,
        }
        return self._qubit_amp_fit


    def plot_qubit_flux_sweep(self, save=False, plot_fit=True, extrap_range=None):
        show_extrap = plot_fit and self._qubit_amp_fit
        if show_extrap:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5), gridspec_kw={'width_ratios': [2, 1]})
        else:
            fig, ax1 = plt.subplots(1, 1, figsize=(14, 5))
        fig.suptitle(f"{self._qubit_id} flux analysis", fontsize=16)
        ax1.pcolor(self._frequencies, self._fluxDC, self._qubit_amp)
        ax1.set_ylabel('Flux (V)')
        ax1.set_xlabel('Frequency (Hz)')
        if show_extrap:
            ax1.set_title('Measured range')
        if plot_fit:
            if self._qubit_amp_fit:
                valid_mask = self._qubit_amp_fit['valid_mask']
                peak_freqs = self._qubit_amp_fit['peak_freqs']

                fit_func = self._qubit_amp_fit['fit_func']
                popt = self._qubit_amp_fit['popt']
                flux_smooth = np.linspace(np.min(self._fluxDC), np.max(self._fluxDC), 500)
                freq_smooth = fit_func(flux_smooth, *popt)
                ax1.plot(freq_smooth, flux_smooth, 'w-', linewidth=1, label='Fit')
                ax1.plot(peak_freqs[valid_mask], self._fluxDC[valid_mask], 'wx', markersize=2, label='Detected peak')

                ax1.legend(loc='lower right', fontsize=8)
            else:
                print("Do fit_qubit_frequency() before plotting the fit.")
        if show_extrap:
            fit_func = self._qubit_amp_fit['fit_func']
            popt = self._qubit_amp_fit['popt']
            f_max = self._qubit_amp_fit['f_max']
            flux0 = self._qubit_amp_fit['flux0']
            period = self._qubit_amp_fit['period']
            offset = self._qubit_amp_fit['offset']

            if extrap_range == None:
                extrap_range=(-0.75*period, 0.75*period)

            flux_extrap = np.linspace(extrap_range[0], extrap_range[1], 1000)
            freq_extrap = fit_func(flux_extrap, *popt)

            peak_freq_val = f_max + offset
            if extrap_range[0] <= flux0 <= extrap_range[1]:
                ax2.plot(peak_freq_val, flux0, 'ko', markersize=3, label='Sweet spot (fit)')

            info_text = (
                f"$f_{{max}}$ = {peak_freq_val*1e-9:.4f} GHz\n"
                f"Period = {period:.4f} V\n"
                f"Sweet spot = {flux0:.4f} V"
            )
            ax2.text(
                0.03, 0.03, info_text, transform=ax2.transAxes,
                fontsize=9, verticalalignment='bottom',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
            )
            ax2.plot(freq_extrap, flux_extrap, 'r-', linewidth=1, label='Fit (extrapolated)')
            ax2.plot(peak_freqs[valid_mask], self._fluxDC[valid_mask], 'x', markersize=1, label='Measured peaks')
            ax2.axhspan(np.min(self._fluxDC), np.max(self._fluxDC), color='grey', alpha=0.15, label='Measured range')
            ax2.set_ylabel('Flux (V)')
            ax2.set_xlabel('Frequency (Hz)')
            ax2.set_title(f'Extrapolated fit ({extrap_range[0]:.3f}V to {extrap_range[1]:.3f}V)')
            ax2.legend(loc='lower right', fontsize=8)
        fig.tight_layout()
        if save and show_extrap:
            fig.savefig(parent + '/QubitFluxSpecFit.png')
        elif save:
            fig.savefig(parent + '/QubitFluxSpecFull.png')

    def plot_qubit_flux_sweep_with_linescans(self, save=False):
        n = len(self._fluxDC)
        chunk = n / 3
        flux_indices = [int(chunk * i + chunk / 2) for i in range(3)]
        if self._fluxDC[0] < self._fluxDC[-1]:
            flux_indices = flux_indices[::-1]            
        #
        fig = plt.figure(figsize=(14, 5))
        gs = GridSpec(3, 2, width_ratios=[2, 1], figure=fig)
        fig.suptitle(f"{self._qubit_id} qubit spectroscopy", fontsize=16)
        ax_main = fig.add_subplot(gs[:, 0])
        ax_main.pcolor(self._frequencies, self._fluxDC, self._qubit_amp)
        ax_main.set_title(f"Flux sweep")
        ax_main.set_ylabel('Flux (V)')
        ax_main.set_xlabel('Frequency (Hz)')
        #
        axes_right = [fig.add_subplot(gs[i, 1]) for i in range(3)]
        axes_right[0].set_title('Linescans')
        for ax, idx in zip(axes_right, flux_indices):
            flux_val = self._fluxDC[idx]
            ax.plot(self._frequencies, self._qubit_amp[idx, :], linewidth=1.0, label = f"Flux = {flux_val:.4g} V")
            ax.legend(loc='lower right')
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel('Amplitude')
            ax.xaxis.grid(True, color='black', alpha=0.3, linewidth=0.8)
            ax_main.axhline(flux_val, color='white', linestyle='--', linewidth=1, alpha=0.7)
        for ax in axes_right[:-1]:
            plt.setp(ax.get_xticklabels(), visible=False)
            ax.set_xlabel('')
        fig.tight_layout()
        #
        if save:
            fig.savefig(parent + '/QubitFluxSpecLinescans.png')


    def get_frequency_from_fluxDC(self, fluxDC):
        assert self._qubit_amp_fit is not None, "Run fit_qubit_frequency() first."
        fit_func = self._qubit_amp_fit['fit_func']
        popt = self._qubit_amp_fit['popt']
        return fit_func(np.asarray(fluxDC), *popt)

    def get_frequency_from_fluxAmplitude(self, flux_amplitude, fluxDC=0):
        """
        Returns the fitted qubit frequency when a flux pulse of amplitude `flux_amplitude`
        is applied on top of a DC bias point `fluxDC` (i.e. total flux = fluxDC_bias + flux_amplitude).
        """
        assert self._qubit_amp_fit is not None, "Run fit_qubit_frequency() first."
        fit_func = self._qubit_amp_fit['fit_func']
        popt = self._qubit_amp_fit['popt']
        total_flux = np.asarray(fluxDC) + np.asarray(flux_amplitude)
        return fit_func(total_flux, *popt)

    def get_fluxDC_from_target_frequency(self, target_freq, near_flux=None, prefer_negative_flux=True):
        """
        Returns fluxDC value for a target frequency.
        """
        assert self._qubit_amp_fit is not None, "Run fit_qubit_frequency() first."
        f_max = self._qubit_amp_fit['f_max']
        flux0 = self._qubit_amp_fit['flux0']
        period = self._qubit_amp_fit['period']
        offset = self._qubit_amp_fit['offset']
        if near_flux is None:
            near_flux = flux0

        # Solve f_max*sqrt(|cos(pi*(x-flux0)/period)|) + offset = target_freq
        # => cos(pi*(x-flux0)/period) = +/- ((target_freq - offset)/f_max)^2
        ratio = (target_freq - offset) / f_max
        if ratio < 0 or ratio > 1:
            print(f"{self._qubit_id} can not reach {target_freq*1e-9:.4f} GHz by flux tuning.")
            return np.nan 
        cos_val_mag = ratio**2
        #
        candidates = []
        for sign in [1, -1]:
            cos_val = sign * cos_val_mag
            cos_val = np.clip(cos_val, -1, 1)
            base_angle = np.arccos(cos_val)
            for n in range(-2, 3):
                for angle in [base_angle, -base_angle]:
                    theta = angle + 2 * np.pi * n
                    x = flux0 + theta * period / np.pi
                    candidates.append(x)
        candidates = np.array(candidates)
        if prefer_negative_flux:
            negative_candidates = candidates[candidates < 0]
            if len(negative_candidates) > 0:
                best_idx = np.argmin(np.abs(negative_candidates - near_flux))
                return negative_candidates[best_idx]
            else:
                print(f"{self._qubit_id}: no negative flux solution found for {target_freq*1e-9:.4f} GHz; returning closest overall.")
        best_idx = np.argmin(np.abs(candidates - near_flux))
        return candidates[best_idx]