from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.Utilities.Optimisers import OptimiseParaboloid
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Utilities.FileIO import*
class ExpMixerCalibrationLO(Experiment):
    def __init__(self, name, expt_config, var_down_conv_freq, freqs_sidebands_LCR, var_DC_off_I, range_DC_off_I, var_DC_off_Q, range_DC_off_Q, optimise=False, **kwargs):
        super().__init__(name, expt_config)
        self._var_down_conv_freq = var_down_conv_freq
        self._freqs_sidebands_LCR = freqs_sidebands_LCR
        self._var_DC_off_I = var_DC_off_I
        self._range_DC_off_I = (min(range_DC_off_I), max(range_DC_off_I))
        self._var_DC_off_Q = var_DC_off_Q
        self._range_DC_off_Q = (min(range_DC_off_Q), max(range_DC_off_Q))
        self._ch_id = kwargs.get('acq_ch', 'CH1')
        self._iters = kwargs.get('iterations', 1)

        self._optimise = optimise
        self._sample_points = kwargs.get('sample_points', 3)
        self._win_shrink_factor = kwargs.get('win_shrink_factor', 0.33)


    def _cost_func(self, x, y):
        self._var_DC_off_I.Value = x
        self._var_DC_off_Q.Value = y
        self._expt_config.prepare_instruments()
        smpl_data = self._expt_config.get_data()

        i_val, q_val = smpl_data['data'][self._ch_id + '_I'], smpl_data['data'][self._ch_id + '_Q']

        ampl = np.sqrt(i_val**2 + q_val**2)
        return ampl

    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot include sweeping variables in this experiment."
        self._expt_config.init_instruments()
        self._var_down_conv_freq.Value = self._freqs_sidebands_LCR[1]
        kwargs['skip_init_instruments'] = True
        
        if self._optimise:
            self._file_path = file_path

            opt = OptimiseParaboloid(self._cost_func)
            min_coord, self.fig = opt.find_minimum( self._range_DC_off_I, self._range_DC_off_Q, 'I-Channel', 'Q-Channel', num_iters=self._iters, num_win_sample_pts=self._sample_points, step_shrink_factor=self._win_shrink_factor )

            print(f'Minimum Coordinate: I={min_coord[0]}, Q={min_coord[1]}, Ampl={min_coord[2]}')
            
            self._var_DC_off_I.Value, self._var_DC_off_Q.Value = min_coord[0], min_coord[1]
            #
            data_opt = np.array(opt.opt_data)
            final_data = {
                'data' : {
                    'CH_I' : data_opt[:,0],
                    'CH_Q' : data_opt[:,1],
                    'CH_ampl' : data_opt[:,2]
                },
                'parameters' : ['step']
            }
            data_file = FileIOWriter(file_path + 'data.h5')
            data_file.push_datapkt(final_data, [])
            data_file.close()
            return FileIOReader(file_path + 'data.h5')
        else:
            #Min I, Max I, Min Q, Max Q
            cur_win = (self._range_DC_off_I[0], self._range_DC_off_I[1], self._range_DC_off_Q[0], self._range_DC_off_Q[1])

            data_list = []
            self.post_proc_list = []

            num_pts = 5

            for m in range(self._iters):
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
        if self._optimise:
            # data_opt = data.get_numpy_array()
            # #
            # fig, ax = plt.subplots(1)
            # ax.scatter(data_opt[:,0], data_opt[:,1], c=data_opt[:,2])
            # ax.set_xlabel('I (V)'); ax.set_ylabel('Q (V)')
            # ax.grid(b=True, which='minor'); ax.grid(b=True, which='major', color='k')
            # #
            self.fig.show()
            self.fig.savefig(self._file_path + 'fitted_plot.png')
