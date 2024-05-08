from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.WaveformSegments import*
import time
from sqdtoolz.Utilities.Optimisers import OptimiseParaboloid
from sqdtoolz.Utilities.DataFitting import*
import scipy.optimize
from sqdtoolz.Utilities.FileIO import*

class ExpMixerCalibrationSB(Experiment):
    def __init__(self, name, expt_config, var_down_conv_freq, freq_SB_minimise, var_amp, range_amps, var_phs, range_phs, optimise=False, **kwargs):
        super().__init__(name, expt_config)
        self._var_down_conv_freq = var_down_conv_freq
        self._freq_SB_minimise = freq_SB_minimise
        self._var_amp = var_amp
        self._range_amps = (min(range_amps), max(range_amps))
        self._var_phs = var_phs
        self._range_phs = (min(range_phs), max(range_phs))
        self._iters = kwargs.get('iterations', 1)

        self._edge_map_points = kwargs.get('num_map_edge_points', 5)
        self._optimise = optimise
        self._sample_points = kwargs.get('sample_points', 3)
        self._win_shrink_factor = kwargs.get('win_shrink_factor', 0.33)

        self._opt_val = (1,0)

    def _cost_func(self, x, y):
        self._var_amp.Value = x
        self._var_phs.Value = y
        self._expt_config.prepare_instruments()
        smpl_data = self._expt_config.get_data()['data']

        ch_names = sorted([x for x in smpl_data['data']])
        assert len(ch_names) == 2, "The acquisition and processing should only return two channels in the output for I and Q respectively."
        i_val, q_val = smpl_data['data'][ch_names[0]], smpl_data['data'][ch_names[1]]

        ampl = np.sqrt(i_val**2 + q_val**2)
        if isinstance(ampl, np.ndarray):
            ampl = ampl[0]
        return ampl

    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot include sweeping variables in this experiment."
        self._expt_config.init_instruments()
        self._var_down_conv_freq.Value = self._freq_SB_minimise
        kwargs['skip_init_instruments'] = True

        if self._optimise:
            self._file_path = file_path
            
            opt = OptimiseParaboloid(self._cost_func)
            min_coord, self.fig = opt.find_minimum( self._range_amps, self._range_phs, 'Amplitude Factor', 'Phase Offset', num_iters=self._iters, num_win_sample_pts=self._sample_points, step_shrink_factor=self._win_shrink_factor )

            print(f'Minimum Coordinate: Amp={min_coord[0]}, Phs={min_coord[1]}, Value={min_coord[2]}')
            
            self._var_amp.Value, self._var_phs.Value = min_coord[0], min_coord[1]
            self._opt_val = min_coord[0], min_coord[1]
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
            return super()._run(file_path, [(self._var_amp, np.linspace(self._range_amps[0], self._range_amps[1], self._edge_map_points)),
                                            (self._var_phs, np.linspace(self._range_phs[0], self._range_phs[1], self._edge_map_points))], **kwargs)

    def _post_process(self, data):
        if self._optimise:
            # data_opt = data.get_numpy_array()
            # #
            # fig, ax = plt.subplots(1)
            # ax.scatter(data_opt[:,0], data_opt[:,1], c=data_opt[:,2])
            # ax.set_xlabel('Amplitude-Factor Q/I'); ax.set_ylabel('Phase-Difference')
            # ax.grid(b=True, which='minor'); ax.grid(b=True, which='major', color='k')
            # #
            self.fig.show()
            self.fig.savefig(self._file_path + 'fitted_plot.png')
        else:
            arr = data.get_numpy_array()
            data_amp = np.sqrt(arr[:,:,0]**2+arr[:,:,1]**2)

            dfit = DFitMinMax2D()
            dpkt = dfit.get_fitted_plot(data.param_vals[0], data.param_vals[1], data_amp, isMin=True, xLabel='Amplitude-Factor Q/I', yLabel='Phase-Difference')
            
            #Set the DC offsets to the minimum
            self._var_amp.Value, self._var_phs.Value = dpkt['extremum']

            return dpkt['fig']

    def commit_to_SPEC(self, SPEC_obj):
        SPEC_obj['AmpFac'].Value, SPEC_obj['PhsOff'].Value = self._opt_val
