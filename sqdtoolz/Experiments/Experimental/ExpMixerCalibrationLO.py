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
        
        #Min I, Max I, Min Q, Max Q
        cur_win = (self._range_DC_off_I[0], self._range_DC_off_I[1], self._range_DC_off_Q[0], self._range_DC_off_Q[1])

        data_list = []
        self.post_proc_list = []

        num_pts = 5

        for m in range(4):
            kwargs['data_file_index'] = m
            data_list += [ super()._run(file_path, [(self._var_DC_off_I, np.linspace(cur_win[0], cur_win[1], num_pts)),
                                            (self._var_DC_off_Q, np.linspace(cur_win[2], cur_win[3], num_pts))], **kwargs) ]
            
            dpkt = self._find_minimum(data_list[-1])
            self.post_proc_list += [dpkt]
            #Set the DC offsets to the minimum
            min_I, min_Q = dpkt['extremum']
            self._var_DC_off_I.Value, self._var_DC_off_Q.Value = min_I, min_Q
            #Setup new window for next iteration...
            new_win_size = ((cur_win[1]-cur_win[0])*2/num_pts, (cur_win[3]-cur_win[2])*2/num_pts)
            cur_win = [min_I-0.5*new_win_size[0], min_I+0.5*new_win_size[0], min_Q-0.5*new_win_size[1], min_Q+0.5*new_win_size[1]]
            #Trim window to minimum/maximum bounds...
            if cur_win[0] < self._range_DC_off_I[0]:
                cur_win[0] = self._range_DC_off_I[0]
            if cur_win[1] > self._range_DC_off_I[1]:
                cur_win[1] = self._range_DC_off_I[1]
            if cur_win[2] < self._range_DC_off_Q[0]:
                cur_win[2] = self._range_DC_off_Q[0]
            if cur_win[3] > self._range_DC_off_Q[1]:
                cur_win[3] = self._range_DC_off_Q[1]
        
        return None
        
    def _find_minimum(self, data):
        arr = data.get_numpy_array()
        data_amp = np.sqrt(arr[:,:,0]**2+arr[:,:,1]**2)

        dfit = DFitMinMax2D()
        dpkt = dfit.get_fitted_plot(data.param_vals[0], data.param_vals[1], data_amp, isMin=True, xLabel='DC Offset I', yLabel='DC Offset Q')
        
        return dpkt
                                        
    def _post_process(self, data):
        # arr = data.get_numpy_array()
        # data_amp = np.sqrt(arr[:,:,0]**2+arr[:,:,1]**2)

        # dfit = DFitMinMax2D()
        # dpkt = dfit.get_fitted_plot(data.param_vals[0], data.param_vals[1], data_amp, isMin=True, xLabel='DC Offset I', yLabel='DC Offset Q')
        
        # #Set the DC offsets to the minimum
        # self._var_DC_off_I.Value, self._var_DC_off_Q.Value = dpkt['extremum']

        # return dpkt['fig']
        pass
