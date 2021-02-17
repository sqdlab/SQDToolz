from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time

class ExperimentCavitySpectroscopy(Experiment):
    def __init__(self, name, expt_config, param_source_frequency, awg_readout_mkr):
        super().__init__(name, expt_config)
        self._param_source_frequency = param_source_frequency
        self._awg_readout_mkr = awg_readout_mkr
        self._freq_vals = []

    def set_freq_vals(self, freq_array):
        self._freq_vals = freq_array[:]

    def _run(self, sweep_vars=[]):
        self._expt_config.init_instrument_relations()

        self._awg_readout_mkr.add_waveform_segment(WFS_Gaussian("blank", None, 75e-9, 0.0))
        self._awg_readout_mkr.get_output_channel().marker(0).set_markers_to_trigger()
        self._awg_readout_mkr.get_output_channel().marker(0).TrigPulseDelay = 0e-9
        self._awg_readout_mkr.get_output_channel().marker(0).TrigPulseLength = 30e-9

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
