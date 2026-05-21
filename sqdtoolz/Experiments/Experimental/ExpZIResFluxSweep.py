from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from laboneq_applications.experiments import resonator_spectroscopy
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
import scipy.interpolate
import scipy.optimize
from sqdtoolz.Utilities.DataFitting import DFitPeakLorentzian

class ExpZIResFluxSweep(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_id, frequencies, flux_range, **kwargs):
        assert isinstance(qubit_id, str), "Supply qubit_id as the solitary string ID here (i.e. not a list)."
        self._qubit_id = qubit_id

        self._update_qubit = kwargs.pop('update_qubit_params', True)

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)

        self._is_trough = kwargs.pop('is_trough', True)
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')
        self._flux_range = flux_range
        self._frequencies = frequencies
        self._hal_QPU = hal_QPU

        self._opt_flux_val = None

        kwargs['frequencies'] = frequencies
        super().__init__(name, expt_config, resonator_spectroscopy, hal_QPU, [qubit_id], **kwargs)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Supply the frequency/flux when defining the Experiment object."

        var_flux = VariablePropertyTransient('Flux', self._hal_QPU.get_qubit_obj(self._qubit_id),'FluxDC')
        super()._run(file_path, sweep_vars=[(var_flux, self._flux_range)], **kwargs)

    def _post_process(self, data):
        leData = self.retrieve_last_dataset(self._qubit_id)
        flux_vals,freq_vals = leData.param_vals
        arr = leData.get_numpy_array()

        ampl = np.sqrt(arr[:,:,0]**2 + arr[:,:,1]**2)

        is_trough = self._is_trough

        dfit = DFitPeakLorentzian()
        res_freqs = []
        for cur_slice in ampl:
            dpkt = dfit.get_fitted_plot(freq_vals, cur_slice, dip=is_trough, dontplot=True)
            res_freqs.append(dpkt['centre'])
        res_freqs = np.array(res_freqs)

        norm_fac = 10**np.round(np.log10(res_freqs).mean())
        if flux_vals[1]-flux_vals[0] < 0:
            spl = scipy.interpolate.UnivariateSpline(flux_vals[::-1], res_freqs[::-1]/norm_fac)
        else:
            spl = scipy.interpolate.UnivariateSpline(flux_vals, res_freqs/norm_fac)
        spl.set_smoothing_factor(0.5)
        soln = scipy.optimize.minimize_scalar(lambda x:-spl(x), bounds=(np.min(flux_vals), np.max(flux_vals)))

        opt_flux = soln.x
        sweet_freq = spl(opt_flux)*norm_fac

        fitted_data = {
            'raw_fit_freqs': res_freqs,
            'smoothed_fit_freqs': spl(flux_vals)*norm_fac,
            'sweet_freq_flux': np.array([sweet_freq, opt_flux])
        }
        np.save(self._file_path + 'fitted_data.npy', fitted_data)

        if not self._dont_plot:
            fig, ax = plt.subplots(1); fig.set_figwidth(15)
            ExpZIResFluxSweep.plot_fitted_results(ax, self._qubit_id, freq_vals, flux_vals, ampl, fitted_data)
            if not self._dont_show_plot:
                fig.show()
            else:
                plt.close(fig)
            fig.savefig(self._file_path + 'fitted_plot.png')

        self._opt_flux_val = opt_flux
    
    @staticmethod
    def plot_fitted_results(ax, qubit_id, freq_vals, flux_vals, ampl, fitted_data):
        ax.pcolor(freq_vals, flux_vals, ampl)
        ax.plot(fitted_data['smoothed_fit_freqs'], flux_vals, 'w-')
        ax.plot(fitted_data['raw_fit_freqs'], flux_vals, 'wo')
        ax.plot([fitted_data['sweet_freq_flux'][0]], [fitted_data['sweet_freq_flux'][1]], 'ro')
        ax.set_title(f"{qubit_id} sweet spot: f={fitted_data['sweet_freq_flux'][0]*1e-9:.4f} GHz, FluxDC={fitted_data['sweet_freq_flux'][1]:.4f} V")
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Flux (V)')

    def update_qubit(self):
        assert self._opt_flux_val != None, "Must run an experiment before updating qubit parameters."
        self._hal_QPU.get_qubit_obj(self._qubit_id).FluxDC = self._opt_flux_val
        # TODO: update flux range to minimum
        self._opt_flux_val = None
