from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import iq_blobs
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np

class ExpZITWPATuneup(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, hal_twpa, qubit_ids, **kwargs):
        self._qubit_ids = qubit_ids
        self._hal_twpa = hal_twpa
        self._iq_blob_data = {}
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        self._plot_all_qubits = kwargs.pop('plot_all_qubits', False)
        self._update_qubit = kwargs.pop('update_qubit_params', True)
        self._optimum_twpa_point = {'Frequency': self._hal_twpa.Frequency, 'Power':self._hal_twpa.Power}

        if 'twpa_freq_range' in kwargs:
            self._twpa_freq_range = kwargs.pop('twpa_freq_range')
        else:
            self._twpa_freq_range =self._hal_twpa.Frequency
    
        if 'twpa_power_range' in kwargs:
            self._twpa_power_range = kwargs.pop('twpa_power_range')
        else:
            self._twpa_power_range = self._hal_twpa.Power

        super().__init__(name, expt_config, iq_blobs, hal_QPU, qubit_ids, states="ge", **kwargs)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Supply the twpa power/frequency when defining the Experiment object."
        var_power = VariablePropertyTransient('pump_power', self._hal_twpa,'Power')
        var_freq = VariablePropertyTransient('pump_frequency', self._hal_twpa,'Frequency')
        super()._run(file_path, sweep_vars=[(var_freq, self._twpa_freq_range), (var_power, self._twpa_power_range)], **kwargs)

    def _post_process(self, data):
        n_qubits = len(self._qubit_ids)
        for qubit in self._qubit_ids:     
            leData = self.retrieve_last_dataset(qubit + r'_calib')
            arr = leData.get_numpy_array()
            sweep_vals = leData.param_vals
            g_real = arr[..., 0]
            g_imag = arr[..., 1]
            e_real = arr[..., 2]
            e_imag = arr[..., 3]

            mean_g_real = np.mean(g_real, axis=-1)
            mean_g_imag = np.mean(g_imag, axis=-1)
            mean_e_real = np.mean(e_real, axis=-1)
            mean_e_imag = np.mean(e_imag, axis=-1)

            delta_real = mean_e_real - mean_g_real
            delta_imag = mean_e_imag - mean_g_imag
            
            d = np.sqrt(delta_real**2 + delta_imag**2)

            var_g = np.var(g_real, axis=-1) + np.var(g_imag, axis=-1)
            var_e = np.var(e_real, axis=-1) + np.var(e_imag, axis=-1)
            
            sigma = (np.sqrt(var_g) + np.sqrt(var_e)) / 2.0
            
            voltage_snr = d / (2.0 * sigma)
            power_snr = voltage_snr**2
            
            power_snr = np.where(power_snr <= 0, 1e-10, power_snr)
            snr_db = 10.0 * np.log10(power_snr)
            self._iq_blob_data[qubit] = snr_db

        snr_db_total = np.sum([self._iq_blob_data[qubit] for qubit in self._qubit_ids], axis = 0)
        opt_indicies = np.where(snr_db_total == snr_db_total.max())
        freqs, powers, _ = sweep_vals
        if not self._dont_show_plot:
            #TODO: add plots for each qubit
            if len(freqs)>1 and len(powers)>1: #2D sweep
                fig = plt.figure(layout="constrained"); fig.set_figwidth(12); fig.set_figheight(12)
                fig.suptitle(f"Tuneup {self._qubit_id}", fontsize=16, fontweight='bold')
                self._optimum_twpa_point['Frequency'] = freqs[opt_indicies[0]]
                self._optimum_twpa_point['Power'] = powers[opt_indicies[1]]
                XX, YY = np.meshgrid(freqs,powers)
                ZZ = snr_db_total.T
                fig, ax = plt.subplots()
                cmap = ax.pcolormesh(XX,YY,ZZ)
                ax.plot(freqs[opt_indicies[0]], powers[opt_indicies[1]], 'o', color = 'red', label = f'$f_p=${freqs[opt_indicies[0]]/1e9} GHz, $P=${powers[opt_indicies[1]]} dB')
                cbar = fig.colorbar(cmap)
                ax.legend(loc=0)
                plt.show()
                
                if self._plot_all_qubits:#Plot of all qubits individually
                    n = len(self._qubit_ids)
                    cols = int(np.ceil(np.sqrt(n)))
                    rows = int(np.ceil(n / cols))
                    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3))
                    if n == 1:
                        axes_flat = [axes]
                    else:
                        axes_flat = axes.flatten()

                    for i,qubit in enumerate(self._qubit_ids):
                        ZZ = (self._iq_blob_data[qubit]).T
                        if i < n:
                            cmap = axes_flat[i].pcolormesh(XX,YY,ZZ)
                            axes_flat[i].plot(freqs[opt_indicies[0]], powers[opt_indicies[1]], 'o', color = 'red', 
                                    label = f'$f_p=${freqs[opt_indicies[0]]/1e9} GHz, $P=${powers[opt_indicies[1]]} dB'
                                )
                            cbar = fig.colorbar(cmap)
                            axes_flat[i].legend(loc=0)
                            axes_flat[i].set_title(f'{qubit}')
                        else:
                            axes_flat[i].axis('off')
                    plt.tight_layout()
                    plt.show()

            else: #1D sweep TWPA parameter, repititions
                fig, ax = plt.subplots()
                sweep_param = max(freqs, powers, key=len)
                sweep_param_idx,  sweep_param_vals = max(enumerate([freqs, powers]), key=lambda x: len(x[1]))
                if sweep_param_idx == 0:
                    ax.plot(freqs, snr_db_total[:, 0], label='mean SNR')
                    for qubit in self._qubit_ids:
                        snr = self._iq_blob_data[qubit]
                        ax.plot(freqs, snr[0,:], label=f'{qubit}')
                    ax.vline(freqs[opt_indicies[0]], color = 'black', label = f'$f_p=${freqs[opt_indicies[0]]/1e9} GHz, $P=${powers[opt_indicies[1]]} dB')
                else:
                    ax.plot(powers, snr_db_total[0, :], label='mean SNR')
                    for qubit in self._qubit_ids:
                        snr = self._iq_blob_data[qubit]
                        ax.plot(powers, snr[0,:], label=f'{qubit}')
                    ax.vline(powers[opt_indicies[1]], color = 'black', label = f'$f_p=${freqs[opt_indicies[0]]/1e9} GHz, $P=${powers[opt_indicies[1]]} dB')

        if self._update_qubit:
            self._hal_twpa.Frequency = self._optimum_twpa_point['Frequency'][0] 
            self._hal_twpa.Power = self._optimum_twpa_point['Power'][0]

        