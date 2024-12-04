from sqdtoolz.Experiment import Experiment
import numpy as np
import matplotlib.pyplot as plt

class ExpBodePlot(Experiment):
    def __init__(self, name, expt_config, VAR_freq, sweep_freq_vals, **kwargs):
        super().__init__(name, expt_config)

        self._VAR_freq = VAR_freq
        self._sweep_freq_vals = sweep_freq_vals
        self._dso_chans = kwargs.get('DSO_channel_names_src_out', ['CH1', 'CH2'])
        self._dont_plot = kwargs.get('dont_plot', False)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Do not provide sweeping variables in this experiment."
        sweep_vars = [(self._VAR_freq, self._sweep_freq_vals)]
        return super()._run(file_path, sweep_vars, **kwargs)

    def _init_aux_datafiles(self):
        self._init_data_file('BodePlot')

    def get_fft(self, data_x, data_y):
        sample_rate = 1/(data_x[1]-data_x[0])
        freqs = np.fft.fftfreq(data_y.size, 1.0/sample_rate)
        arr_fft = np.fft.fft(data_y)
        arr_fft[0] = 0  #Zero DC...
        return freqs, arr_fft

    def _mid_process(self):
        cur_swp_vals = self._retrieve_current_sweep_values()

        cur_freq = cur_swp_vals[self._VAR_freq.Name]
        osc_data = self._data['data']
        time_vals = self._data['parameter_values'][self._data['parameters'][0]]

        freq_vals, fft_vals = self.get_fft(time_vals, osc_data[self._dso_chans[0]])
        #Look for peak in between f/2 and 2f with f being the current excitation frequency
        fft_slice_inds = np.argmin(np.abs(freq_vals-cur_freq*0.5)), np.argmin(np.abs(freq_vals-cur_freq*2.0))
        fft_peak_freq_ind = fft_slice_inds[0] + np.argmax(np.abs(fft_vals[fft_slice_inds[0]:fft_slice_inds[1]]))
        #freq_vals[fft_peak_freq_ind]   #can inspect this in debugging...
        freq_vals, fft_valsOut = self.get_fft(time_vals, osc_data[self._dso_chans[1]])
        transferFunc = fft_valsOut[fft_peak_freq_ind] / fft_vals[fft_peak_freq_ind]

        data_dict = { 'Hreal' : np.real(transferFunc), 'Himag' : np.imag(transferFunc) }
        data_pkt = {
            'parameters' : [],
            'data' : data_dict
        }
        self._push_data_mid_iteration('BodePlot', self._VAR_freq.Name, data_pkt)

    def _post_process(self, data):
        if not self._dont_plot:
            leData = self.retrieve_last_aux_dataset('BodePlot')
            
            arr = leData.get_numpy_array()
            freq_sweeps = leData.param_vals[0]

            fig, axs = plt.subplots(nrows=2); axs[0].grid(); axs[1].grid()
            axs[0].set_ylabel('|H| (dB)'); axs[1].set_ylabel('arg(H) (°)'); axs[1].set_xlabel('Frequency')

            axs[0].loglog(freq_sweeps, arr[:,0]**2+arr[:,1]**2, 'r')
            angles = np.arctan2(arr[:,1], arr[:,0])
            axs[1].semilogx(freq_sweeps, np.unwrap(angles)/np.pi*180, 'b')

            fig.show()
            fig.savefig(self._file_path + 'BodePlot.png')
            leData.release()
            plt.close(fig)
