from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time

class ExperimentRabi(Experiment):
    def __init__(self, name, expt_config, wfm_mod_control, sample_times, param_rabi_frequency):
        super().__init__(name, expt_config)
        self._wfm_mod_control = wfm_mod_control
        self._sample_times = sample_times
        self._param_rabi_frequency = param_rabi_frequency

    def _run(self, sweep_vars=[]):
        self._expt_config.init_instrument_relations()

        #Doing it the segmented style...
        wfm_segments = []
        read_segments = []
        for ind, cur_time in enumerate(self._sample_times):
            wfm_segments += [
                WFS_Gaussian(f"init{ind}", self._wfm_mod_control, 75e-9, 1.0),
                WFS_Constant(f"pad1{ind}", None, 45e-9, 0.5),
                WFS_Constant(f"hold{ind}", None, cur_time, 0.5),
                WFS_Gaussian(f"pulse{ind}", self._wfm_mod_control, 75e-9, 1.0),
                WFS_Constant(f"pad2{ind}", None, 45e-9, 0.5),
                WFS_Constant(f"read{ind}", None, 150e-9, 0.0)
            ]
            read_segments += [f"read{ind}"]

        self._expt_config.update_waveforms(wfm_segments, 50, len(read_segments), readout_segments=read_segments)

        self._expt_config.prepare_instruments()
        data = self._expt_config.get_data()
        #TODO: Add in a preprocessor - e.g. max/min or average etc...
        data = [np.mean(x) for x in data]

        data_final = np.array(data)
        data_final = np.c_[self._sample_times, data_final]
        return data_final
    
    def save_data(self, save_dir, data_final_array):
        final_str = f"Timestamp: {time.asctime()} \n"
        col_num = 1
        final_str += "Column " + str(col_num) + ":\n"
        final_str += "\tname: " + "Times" + "\n"
        final_str += "\ttype: coordinate\n"
        col_num += 1
        final_str += "Column " + str(col_num) + ":\n"
        final_str += "\tname: Probabilities\n"
        final_str += "\ttype: value"
        col_num += 1

        #Save data
        np.savetxt(save_dir + 'data.dat', data_final_array, delimiter='\t', header=final_str, fmt='%.15f')

    def _post_process(self, data):
        #Run some fits
        leFitFreq = 5e6
        #Set some parameters
        self._param_rabi_frequency.set_raw(leFitFreq)
