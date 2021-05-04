from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time

from sqdtoolz.Utilities.DataFitting import*

class ExpMixerCalibrationLO(Experiment):
    def __init__(self, name, expt_config, var_down_conv_freq, freqs_sidebands_LCR, var_DC_off_I, range_DC_off_I, var_DC_off_Q, range_DC_off_Q):
        super().__init__(name, expt_config)
        self._var_down_conv_freq = var_down_conv_freq
        self._freqs_sidebands_LCR = freqs_sidebands_LCR
        self._var_DC_off_I = var_DC_off_I
        self._range_DC_off_I = range_DC_off_I
        self._var_DC_off_Q = var_DC_off_Q
        self._range_DC_off_Q = range_DC_off_Q

    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot include sweeping variables in this experiment."
        self._expt_config.init_instruments()
        self._var_down_conv_freq.Value = self._freqs_sidebands_LCR[1]
        kwargs['skip_init_instruments'] = True
        return super()._run(file_path, [(self._var_DC_off_I, np.linspace(self._range_DC_off_I[0], self._range_DC_off_I[1], 10)),
                                        (self._var_DC_off_Q, np.linspace(self._range_DC_off_Q[0], self._range_DC_off_Q[1], 10))], **kwargs)
                                        
    def _post_process(self, data):
        arr = data.get_numpy_array()
        data_amp = np.sqrt(arr[:,:,0]**2+arr[:,:,1]**2)

        dfit = DFitMinMax2D()
        dpkt = dfit.get_fitted_plot(data.param_vals[0], data.param_vals[1], data_amp, isMin=True, xLabel='DC Offset I', yLabel='DC Offset Q')
        
        #Set the DC offsets to the minimum
        self._var_DC_off_I.Value, self._var_DC_off_Q.Value = dpkt['extremum']

        return dpkt['fig']
