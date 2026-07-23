from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
import matplotlib as mpl
from sqdtoolz.Experiments.Experimental.ZI import calibrate_tunable_transmon_fixed_coupler_osc
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import numpy as np
from sqdtoolz.Utilities.DataFitting import DFitPeakLorentzian
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.ZI.QuantumElements.TunableTransmonCouplerFixed import TunableTransmonCouplerFixed
from sqdtoolz.Utilities.DataQubitFlux import DataTransmonFlux
from matplotlib.ticker import MaxNLocator

class ExpZIChevrons2QFixedCoupler(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        self._fit_freq = None
        assert 'amplitudes' in kwargs, "Must supply the array of flux amplitudes to sweep on the coupler."
        self._amplitudes = kwargs.pop('amplitudes')
        self._plot_with_frequency = kwargs.pop('plot_with_frequency', True)
        
        self.cur_coupler_obj = hal_QPU.get_coupler_obj_from_qubits(qubit_ids[0],qubit_ids[1], TunableTransmonCouplerFixed)
        self.tuned_qubit = hal_QPU.get_qubit_obj(self.cur_coupler_obj.get_involved_qubits()[0])

        #Add additional qubits that may be involved with this coupler (e.g. auxiliary lines/qubits) if it hasn't been supplied...
        leQubitLines = self.cur_coupler_obj.get_involved_qubits()
        for cur_qubit in leQubitLines:
            if not cur_qubit in qubit_ids:
                print(f"WARNING: Adding Qubit {cur_qubit} to measurement/tracking list as it's involved in this two-qubit coupler '{self.cur_coupler_obj.Name}'.")
                qubit_ids.append(cur_qubit)

        self._temp_var_ampl = VariablePropertyTransient('flux_amplitude', self.cur_coupler_obj, 'Amplitude')
        self._single_shot = kwargs.pop('single_shot', False)

        super().__init__(name, expt_config, calibrate_tunable_transmon_fixed_coupler_osc, hal_QPU, qubit_ids, **kwargs)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        if self._single_shot:
            kwargs['override_ACQ_params'] = {'AveragingOrder': "SingleShot", 'AcquisitionMode': "DISCRIMINATION"}
        else:
            kwargs['override_ACQ_params'] = {'AveragingOrder': "DEFAULT", 'AcquisitionMode': "DEFAULT"}
        assert len(sweep_vars) == 0, "Cannot sweep other variables here as it'll hurt the post-processing. Perhaps use grouped sweeps?"
        return super()._run(file_path, sweep_vars + [(self._temp_var_ampl, self._amplitudes)], **kwargs)

    def _post_process(self, data):
        if self._single_shot:
            cmap = 'inferno'
            fig, axs = plt.subplots(ncols=3, nrows=len(self._qubit_ids)); fig.set_figwidth(10); fig.set_figheight(3*len(self._qubit_ids))
            axs[0,0].set_title('G'); axs[0,1].set_title('E'); axs[0,2].set_title('F')
            if self.cur_coupler_obj.signals['flux']:
                fig.suptitle(f"Chevrons: {self.cur_coupler_obj.Name} ({self.cur_coupler_obj.signals['flux']})", y=1.05)
            else:
                fig.suptitle(f"Chevrons: {self.cur_coupler_obj.Name}",y=1.05)

            final_pops = []
            for m,cur_data in enumerate(self._qubit_ids):
                leData = self.retrieve_last_aux_dataset(cur_data)
                arr = leData.get_numpy_array()
                wait_times = leData.param_vals[2]
                norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(wait_times)

                count0 = np.sum(arr[...,0]==0,axis=1) / arr.shape[1]
                count1 = np.sum(arr[...,0]==1,axis=1) / arr.shape[1]
                count2 = np.sum(arr[...,0]==2,axis=1) / arr.shape[1]

                flux_amps = leData.param_vals[0]
                if self.tuned_qubit.FluxConversionParams is not None and self._plot_with_frequency:
                    x_vals = DataTransmonFlux.convert_flux_amplitude_to_frequency_zi(self.tuned_qubit, flux_amplitude=flux_amps, fluxDC=self.tuned_qubit.FluxDC)
                    norm_fac_f, norm_prefix_f = Miscellaneous.get_metric_multiplier(x_vals)
                    x_vals /= norm_fac_f
                    amp_order = np.argsort(flux_amps)
                    amp_sorted, freq_for_amp_sorted = flux_amps[amp_order], x_vals[amp_order]
                    def amp_to_freq(amp, _a=amp_sorted, _f=freq_for_amp_sorted):
                        return np.interp(amp, _a, _f)
                    freq_order = np.argsort(x_vals)
                    freq_sorted, amp_for_freq_sorted = x_vals[freq_order], flux_amps[freq_order]
                    def freq_to_amp(freq, _f=freq_sorted, _a=amp_for_freq_sorted):
                        return np.interp(freq, _f, _a)
                    #
                    locator = MaxNLocator(nbins=6)
                    freq_ticks = locator.tick_values(freq_sorted.min(), freq_sorted.max())
                    freq_ticks = freq_ticks[(freq_ticks >= freq_sorted.min()) & (freq_ticks <= freq_sorted.max())]
                    for i in [0,1,2]:
                        secax = axs[m, i].secondary_xaxis('top', functions=(amp_to_freq, freq_to_amp))
                        secax.set_xticks(freq_ticks)
                        if m == 0:
                            secax.set_xlabel(f'Frequency ({norm_prefix_f}Hz)', labelpad=4)
                        else:
                            secax.set_xticklabels([])
                            secax.tick_params(top=False, labeltop=False)
                # fig,axs = plt.subplots(ncols=3); fig.set_figwidth(15); axs[0].set_title('G'); axs[1].set_title('E'); axs[2].set_title('F')
                axs[m,0].pcolor(flux_amps, wait_times/norm_fac, count0.T, vmin=0, vmax=1, cmap=cmap)
                axs[m,1].pcolor(flux_amps, wait_times/norm_fac, count1.T, vmin=0, vmax=1, cmap=cmap)
                axs[m,2].pcolor(flux_amps, wait_times/norm_fac, count2.T, vmin=0, vmax=1, cmap=cmap)
                axs[m,0].set_ylabel(f'Wait Times ({norm_prefix}s)')
                axs[m,1].set_yticklabels([]); axs[m,2].set_yticklabels([])
                if m < len(self._qubit_ids)-1:
                    axs[m,0].set_xticklabels([]); axs[m,1].set_xticklabels([]); axs[m,2].set_xticklabels([])
                else:
                    axs[m,0].set_xlabel('Flux Amplitude (0-1)'); axs[m,1].set_xlabel('Flux Amplitude (0-1)'); axs[m,2].set_xlabel('Flux Amplitude (0-1)')
                axs[m,2].text(x=1.05, y=0.5, s=cur_data, rotation=0, ha='left', va='center', transform=axs[m,2].transAxes)
                final_pops.append([count0, count1, count2])
            final_pops = np.array(final_pops)
            fig.subplots_adjust(wspace=0.05,hspace=0.05)
            #
            norm = mpl.colors.Normalize(vmin=0, vmax=1)
            sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
            sm.set_array([])
            cbar = fig.colorbar(sm,ax=axs,orientation="horizontal",location="bottom",pad=0.1,fraction=0.04,)
            cbar.set_label("Population Probability")

            np.save(self._file_path + f'fitted_data.npy', {'qubits':self._qubit_ids, 'wait_times':wait_times, 'flux_amps':leData.param_vals[0], 'pop_qubit_amps_times':final_pops})
        else:
            fig, axs = plt.subplots(nrows=len(self._qubit_ids))
            if self.cur_coupler_obj.signals['flux']:
                fig.suptitle(f"Chevrons: {self.cur_coupler_obj.Name} ({self.cur_coupler_obj.signals['flux']})", y=0.98)
            else:
                fig.suptitle(f"Chevrons: {self.cur_coupler_obj.Name}", y=0.98)

            for m, cur_qubit in enumerate(self._qubit_ids):
                leData = self.retrieve_last_dataset(cur_qubit)
                wait_times = leData.param_vals[1]
                norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(wait_times)
                arr = leData.get_numpy_array()
                #
                flux_amps = leData.param_vals[0]
                axs[m].pcolor(flux_amps, wait_times/norm_fac, np.sqrt(arr[:,:,0]**2+arr[:,:,1]**2).T, vmin=0)
                axs[m].set_ylabel(f'Wait Time ({norm_prefix}s)')
                axs[m].text(x=1.03, y=0.5, s=cur_qubit, rotation=0, ha='left', va='center', transform=axs[m].transAxes)
                #
                if self.tuned_qubit.FluxConversionParams is not None and self._plot_with_frequency:
                    x_vals = DataTransmonFlux.convert_flux_amplitude_to_frequency_zi(self.tuned_qubit, flux_amplitude=flux_amps, fluxDC=self.tuned_qubit.FluxDC)
                    amp_order = np.argsort(flux_amps)
                    amp_sorted, freq_for_amp_sorted = flux_amps[amp_order], x_vals[amp_order]
                    def amp_to_freq(amp, _a=amp_sorted, _f=freq_for_amp_sorted):
                        return np.interp(amp, _a, _f)
                    freq_order = np.argsort(x_vals)
                    freq_sorted, amp_for_freq_sorted = x_vals[freq_order], flux_amps[freq_order]
                    def freq_to_amp(freq, _f=freq_sorted, _a=amp_for_freq_sorted):
                        return np.interp(freq, _f, _a)
                    secax = axs[m].secondary_xaxis('top', functions=(amp_to_freq, freq_to_amp))
                    #
                    locator = MaxNLocator(nbins=8)
                    freq_ticks = locator.tick_values(freq_sorted.min(), freq_sorted.max())
                    freq_ticks = freq_ticks[(freq_ticks >= freq_sorted.min()) & (freq_ticks <= freq_sorted.max())]
                    secax.set_xticks(freq_ticks)

                    if m == 0:
                        secax.set_xlabel('Frequency', labelpad=8)
                    else:
                        secax.set_xticklabels([])
                        # secax.tick_params(top=False, labeltop=False)
                if m < len(self._qubit_ids)-1:
                    axs[m].set_xticklabels([])
                    # axs[m].tick_params(axis='x', which='both', bottom=False)
            axs[m].set_xlabel('Flux Pulse Amplitude (0-1)')

            fig.subplots_adjust(hspace=0.1, top=0.8)

        fig.savefig(self._file_path + f'fitted_plot.png')
        if not self._dont_show_plot:
            fig.show()
        else:
            plt.close(fig)
