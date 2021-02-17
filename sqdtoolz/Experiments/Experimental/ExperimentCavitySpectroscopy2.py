from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time

class ExperimentCavitySpectroscopy2(Experiment):
    def __init__(self, name, expt_config, param_source_frequency):
        super().__init__(name, expt_config)
        self._param_source_frequency = param_source_frequency
        self._freq_vals = []

    def set_freq_vals(self, freq_array):
        self._freq_vals = freq_array[:]

    def _run(self, sweep_vars=[]):
        self._expt_config.init_instrument_relations()

        self._expt_config.update_waveforms([WFS_Gaussian("blank", None, 25e-9, 0.0), WFS_Gaussian("blank2", None, 50e-9, 0.0)], 100, 1, readout_segments=["blank"])

        data_final = super()._run([(self._param_source_frequency, self._freq_vals)])

        return data_final
    
    def save_data(self, save_dir, data_final_array, **kwargs):
        final_str = f"Timestamp: {time.asctime()} \n"
        col_num = 1
        final_str += "Column " + str(col_num) + ":\n"
        final_str += "\tname: " + "Frequency" + "\n"
        final_str += "\ttype: coordinate\n"
        col_num += 1
        final_str += "Column " + str(col_num) + ":\n"
        final_str += "\tname: real(Response)\n"
        final_str += "\ttype: value"
        col_num += 1
        final_str += "Column " + str(col_num) + ":\n"
        final_str += "\tname: imag(Response)\n"
        final_str += "\ttype: value"

        #Save data
        np.savetxt(save_dir + 'data.dat', data_final_array, delimiter='\t', header=final_str, fmt='%.15f')

    def _post_process(self, data):
        #Run some fits
        leFitFreq = 420e6
        #Set some parameters
        self._param_source_frequency.set_raw(leFitFreq)
