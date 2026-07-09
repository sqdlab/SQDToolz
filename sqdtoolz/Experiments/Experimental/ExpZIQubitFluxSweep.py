from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ExpZIRes import ExpZIRes
from laboneq_applications.experiments import resonator_spectroscopy, qubit_spectroscopy
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sqdtoolz.Utilities.FileIO import FileIODirectory
from pathlib import Path
import sqdtoolz as stz

class ExpZIQubitFluxSweep:
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, qubit_frequencies, res_frequencies, flux_range, flux_var, **kwargs):
        # Allow a single qubit_id (str) or a list for multiple qubits.
        if isinstance(qubit_ids, str):
            qubit_ids = [qubit_ids]
            qubit_frequencies = [qubit_frequencies]
            res_frequencies = [res_frequencies]

        assert isinstance(qubit_ids, list) and all(isinstance(q, str) for q in qubit_ids), \
            "Supply qubit_ids as a single string (one qubit) or a list of strings (multiple qubits)."
        assert len(qubit_frequencies) == len(qubit_ids), \
            "Supply qubit_frequencies as a list of frequency arrays matching the length of qubit_ids."
        assert len(res_frequencies) == len(qubit_ids), \
            "Supply res_frequencies as a list of frequency arrays matching the length of qubit_ids."

        self._qubit_ids = qubit_ids
        self._name = name
        self._expt_config = expt_config
        self._flux_var = flux_var
        assert self._flux_var._prop == 'FluxDC', "Supply a 'Flux_DC' variable as flux_var, i.e. stz.VariableProperty(f'fluxLineQ0', lab, lab.HAL('Q0'), 'FluxDC')."
        flux_qubit = self._flux_var._get_current_config()['ResList'][0][0]
        assert flux_qubit in self._qubit_ids, \
            f"Supply a 'Flux_DC' variable corresponding to one of the qubits being measured. Currently you supplied a flux variable for {flux_qubit}, which is not in {self._qubit_ids}."
        self._flux_range = flux_range
        self._res_freq_range = res_frequencies
        self._qubit_freq_range = qubit_frequencies

        self._update_qubit = kwargs.pop('update_qubit_params', True)
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)

        self._is_trough = kwargs.pop('is_trough', True)
        self._fit_type = kwargs.pop('res_fit_type', 'Full')
        assert self._fit_type in ["Default", "Fano", "Full"], "Choose res_fit_type as either 'Default', 'Fano' or 'Full'."
        self._dont_plot = kwargs.pop('dont_plot', False)
        self._xUnits = kwargs.pop('plot_x_units', 'Hz')

        self._hal_QPU = hal_QPU

        self._enable_ZI_log_messages = kwargs.pop('enable_ZI_log_messages', False)
        self._print_file_path = kwargs.pop('print_file_path', False)

        self._averages = kwargs.pop('measurement_averages', None)
        if self._averages is not None:
            if isinstance(self._averages, (int, float)):
                self._averages = [self._averages] * len(self._qubit_ids)

            assert len(self._averages) == len(self._qubit_ids), \
                "Supply measurement_averages as a single value or a list matching the length of qubit_ids."

        self._acq_hal_name = kwargs.pop('acquisition_hal', 'ZIacq')

    def run(self, lab):
        original_freqs = {qid: self._hal_QPU.get_qubit_obj(qid).ReadoutFrequency for qid in self._qubit_ids}

        last_expR = {}
        last_expQ = {}
        readout_freqs_at_flux = {qid: [] for qid in self._qubit_ids}

        lab.group_open(self._name)
        if not self._flux_range is None:
            for j, flux in enumerate(self._flux_var.array(self._flux_range)):
                print(f'({j+1}/{len(self._flux_range)}) Setting "{self._flux_var.Name}": {flux:.3f} V.')
                for i, (qid, res_freqs, qubit_freqs) in enumerate(zip(self._qubit_ids, self._res_freq_range, self._qubit_freq_range)):
                    if self._averages is not None:
                        lab.HAL(self._acq_hal_name).NumRepetitions = self._averages[i]
                        stz.ExperimentConfiguration(self._expt_config._name, lab, 0, [], self._acq_hal_name) # update averages
                    expR = ExpZIRes(f'res_spec_{qid}', self._expt_config, self._hal_QPU, qid, frequencies=res_freqs, dont_plot=self._dont_plot, is_trough=self._is_trough, fit_type=self._fit_type, update=True)
                    lab.run_single(expR, disable_ZI_logging=not self._enable_ZI_log_messages)
                    last_expR[qid] = expR
                    readout_freqs_at_flux[qid].append(lab.HAL(qid).ReadoutFrequency)
                    #
                    expQ = ExpZIqubit(f'qubit_spec_{qid}', self._expt_config, qubit_spectroscopy, self._hal_QPU, [qid], frequencies=[qubit_freqs], ZI_plot=not self._dont_plot, update=self._update_qubit)
                    lab.run_single(expQ, disable_ZI_logging=not self._enable_ZI_log_messages)
                    last_expQ[qid] = expQ
        lab.group_close()

        if not self._update_qubit:
            for qid in self._qubit_ids:
                self._hal_QPU.get_qubit_obj(qid).ReadoutFrequency = original_freqs[qid]

        qubit_data = {}
        for qid in self._qubit_ids:
            expQ = last_expQ[qid]
            expR = last_expR[qid]

            dataQ = FileIODirectory(expQ._file_path + f'{qid}.h5')
            dataR = FileIODirectory(expR._file_path + f'{qid}.h5')

            arrQ = dataQ.get_numpy_array()
            freq_valsQ = dataQ.param_vals[1]
            amplQ = np.sqrt(arrQ[:,:,0]**2 + arrQ[:,:,1]**2)
            row_means = np.nanmean(amplQ, axis=1)
            amplQ_corrected = (amplQ.T - row_means).T

            arrR = dataR.get_numpy_array()
            freq_valsR = dataR.param_vals[1]
            amplR = np.sqrt(arrR[:,:,0]**2 + arrR[:,:,1]**2)
            row_means = np.nanmean(amplR, axis=1)
            amplR_corrected = (amplR.T - row_means).T

            qubit_data[qid] = {
                'freq_valsQ': freq_valsQ,
                'amplQ_corrected': amplQ_corrected,
                'freq_valsR': freq_valsR,
                'amplR_corrected': amplR_corrected,
                'readout_freqs': readout_freqs_at_flux[qid],
                'parent': str(Path(expQ._file_path).parent),
            }

            self._plot_overview(qid, qubit_data[qid])
            self._plot_qubit_flux_spec(qid, qubit_data[qid])

        if len(self._qubit_ids) > 1:
            self._plot_multi_qubit_comparison(qubit_data)

        if self._print_file_path:
            print(r"File: '{}'".format(qubit_data[self._qubit_ids[0]]['parent']))

    def _get_linescan_indices(self):
        n = len(self._flux_range)
        chunk = n / 3
        flux_indices = [int(chunk * i + chunk / 2) for i in range(3)]
        if self._flux_range[0] < self._flux_range[-1]:
            flux_indices = flux_indices[::-1]
        return flux_indices

    def _plot_overview(self, qid, data):
        fig, axes = plt.subplots(ncols=2, sharey=True, figsize=(14,5))
        fig.suptitle(f"{qid} flux sweep", fontsize=16)
        axes[0].pcolor(data['freq_valsQ'], self._flux_range, data['amplQ_corrected'])
        axes[0].set_title(f'Qubit spectroscopy ({self._hal_QPU.get_qubit_obj(qid).DrivePower} dBm drive)')
        axes[0].set_ylabel('Flux (V)')
        axes[1].pcolor(data['freq_valsR'], self._flux_range, data['amplR_corrected'])
        axes[1].set_title(f'Resonator spectroscopy ($f_r={self._hal_QPU.get_qubit_obj(qid).ReadoutFrequency*1e-9:.4f}$ GHz)')
        #
        if self._plot_fitted_res_freqs:
            axes[1].plot(data['readout_freqs'], self._flux_range, 'wo', markersize=2, alpha=0.7, label="Fitted frequencies")
        axes[1].legend()
        #
        for ax in axes:
            ax.set_xlabel('Frequency (Hz)')
            ax.yaxis.grid(True, color='white', alpha=0.3, linewidth=0.8)
        fig.tight_layout()
        fig.savefig(data['parent'] + f'/Overview_{qid}.png')
        if self._dont_show_plot:
            plt.close(fig)

    def _plot_qubit_flux_spec(self, qid, data):
        fig = plt.figure(figsize=(14, 5))
        gs = GridSpec(3, 2, width_ratios=[2, 1], figure=fig)
        fig.suptitle(f"{qid} qubit spectroscopy ({self._hal_QPU.get_qubit_obj(qid).DrivePower} dBm drive)", fontsize=16)
        ax_main = fig.add_subplot(gs[:, 0])
        ax_main.pcolor(data['freq_valsQ'], self._flux_range, data['amplQ_corrected'])
        ax_main.set_title(f"Flux sweep")
        ax_main.set_ylabel('Flux (V)')
        ax_main.set_xlabel('Frequency (Hz)')
        #
        flux_indices = self._get_linescan_indices()
        axes_right = [fig.add_subplot(gs[i, 1]) for i in range(3)]
        axes_right[0].set_title('Linescans')
        for ax, idx in zip(axes_right, flux_indices):
            flux_val = self._flux_range[idx]
            ax.plot(data['freq_valsQ'], data['amplQ_corrected'][idx, :], linewidth=1.0, label=f"Flux = {flux_val:.4g} V")
            ax.legend(loc='lower right')
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel('Amplitude')
            ax.xaxis.grid(True, color='black', alpha=0.3, linewidth=0.8)
            ax_main.axhline(flux_val, color='white', linestyle='--', linewidth=1, alpha=0.7)
        for ax in axes_right[:-1]:
            plt.setp(ax.get_xticklabels(), visible=False)
            ax.set_xlabel('')
        fig.tight_layout()
        fig.savefig(data['parent'] + f'/QubitFluxSpec_{qid}.png')
        if self._dont_show_plot:
            plt.close(fig)

    def _plot_multi_qubit_comparison(self, qubit_data):
        n_qubits = len(self._qubit_ids)
        fig, axes = plt.subplots(ncols=n_qubits, sharey=True, figsize=(7 * n_qubits, 5))
        fig.suptitle("Qubit spectroscopy comparison", fontsize=16)
        if n_qubits == 1:
            axes = [axes]
        for ax, qid in zip(axes, self._qubit_ids):
            data = qubit_data[qid]
            ax.pcolor(data['freq_valsQ'], self._flux_range, data['amplQ_corrected'])
            ax.set_title(f"{qid} ({self._hal_QPU.get_qubit_obj(qid).DrivePower} dBm drive)")
            ax.set_xlabel('Frequency (Hz)')
            ax.yaxis.grid(True, color='white', alpha=0.3, linewidth=0.8)
            ax.xaxis.grid(True, color='white', alpha=0.3, linewidth=0.8)
        axes[0].set_ylabel('Flux (V)')
        fig.tight_layout()
        parent = qubit_data[self._qubit_ids[0]]['parent']
        fig.savefig(parent + '/QubitSpecComparison.png')
        if self._dont_show_plot:
            plt.close(fig)