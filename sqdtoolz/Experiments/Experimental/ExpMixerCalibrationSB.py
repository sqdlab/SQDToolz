from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time

from sqdtoolz.Utilities.DataFitting import*

class ExpMixerCalibrationSB(Experiment):
    def __init__(self, name, expt_config, var_down_conv_freq, freq_SB_minimise, var_amp, range_amps, var_phs, range_phs):
        super().__init__(name, expt_config)
        self._var_down_conv_freq = var_down_conv_freq
        self._freq_SB_minimise = freq_SB_minimise
        self._var_amp = var_amp
        self._range_amps = range_amps
        self._var_phs = var_phs
        self._range_phs = range_phs

    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot include sweeping variables in this experiment."
        self._expt_config.init_instruments()
        self._var_down_conv_freq.Value = self._freq_SB_minimise
        kwargs['skip_init_instruments'] = True
        return super()._run(file_path, [(self._var_amp, np.linspace(self._range_amps[0], self._range_amps[1], 10)),
                                        (self._var_phs, np.linspace(self._range_phs[0], self._range_phs[1], 10))], **kwargs)
                                        
    def _post_process(self, data):
        arr = data.get_numpy_array()
        data_amp = np.sqrt(arr[:,:,0]**2+arr[:,:,1]**2)

        dfit = DFitMinMax2D()
        dpkt = dfit.get_fitted_plot(data.param_vals[0], data.param_vals[1], data_amp, isMin=True, xLabel='Amplitude-Factor Q/I', yLabel='Phase-Difference')
        
        #Set the DC offsets to the minimum
        self._var_amp.Value, self._var_phs.Value = dpkt['extremum']

        return dpkt['fig']
