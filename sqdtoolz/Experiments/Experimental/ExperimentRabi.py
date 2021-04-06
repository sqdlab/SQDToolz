from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time

from sqdtoolz.Utilities.FileIO import*

class ExperimentRabi(Experiment):
    def __init__(self, name, expt_config, wfm_mod_control, sample_times, param_rabi_frequency):
        super().__init__(name, expt_config)
        self._wfm_mod_control = wfm_mod_control
        self._sample_times = sample_times
        self._param_rabi_frequency = param_rabi_frequency

    def _run(self, file_path, sweep_vars=[]):
        self._expt_config.init_instrument_relations()

        #Doing it the segmented style...
        wfm_segments = []
        read_segments = []
        for ind, cur_time in enumerate(self._sample_times):
            wfm_segments += [
                WFS_Gaussian(f"init{ind}", self._wfm_mod_control, 75e-9, 1.0),
                WFS_Constant(f"pulse{ind}", self._wfm_mod_control, cur_time, 0.5),
                WFS_Constant(f"pad{ind}", None, 45e-9, 0.5),
                WFS_Constant(f"read{ind}", None, 150e-9, 0.0)
            ]
            read_segments += [f"read{ind}"]

        self._expt_config.update_waveforms(wfm_segments, 50, len(read_segments), readout_segments=read_segments)
        self._expt_config.prepare_instruments()

        data_file = FileIOWriter(file_path + 'data.h5')
        
        data = self._expt_config.get_data()
        data_file.push_datapkt(data, sweep_vars)

        data_file.close()

        return FileIOReader(file_path + 'data.h5')

    def _post_process(self, data):
        #Run some fits
        leFitFreq = 5e6
        #Set some parameters
        self._param_rabi_frequency.set_raw(leFitFreq)
