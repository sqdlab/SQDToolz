import numpy as np
from sqdtoolz.Experiments.Experimental.ExpZIChevrons2QFixedCoupler import ExpZIChevrons2QFixedCoupler
from sqdtoolz.HAL.ZI.QuantumElements.TunableTransmonCouplerFixed import TunableTransmonCouplerFixed
from sqdtoolz.Utilities.DataFitting import DFitPeakLorentzian, DFitSinusoid
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import matplotlib.pyplot as plt
import matplotlib.gridspec
from pathlib import Path
import scipy.interpolate

class ExpZIFixedCouplerTuneup:
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, fit_qubit, **kwargs):
        self._name = name
        self._expt_config = expt_config
        self._qpu = hal_QPU
        self._qubit_ids = qubit_ids
        self._qubit_fit = fit_qubit
        self._state_fit = kwargs.get('fit_state', 'E')
        self._extremum_type = kwargs.get('pop_fit_extremum', 'max')
        assert self._extremum_type in ['min', 'max'], "The pop_fit_extremum (to fit in the final time-trace) must be 'min' or 'max'."

        self._individual_plots = kwargs.pop('individual_plots', False)
        self._update_live = kwargs.pop('update_params_live', True)
        self._enable_ZI_log_messages = kwargs.pop('enable_ZI_log_messages', False)

        cur_coupler = hal_QPU.get_coupler_obj_from_qubits(qubit_ids[0],qubit_ids[1], TunableTransmonCouplerFixed)

        if 'flux_amp_range' in kwargs:
            self._flux_amp_range = kwargs.pop('flux_amp_range')
            assert not 'flux_amp_span' in kwargs, "Do not supply 'flux_amp_span' if supplying 'flux_amp_range'"
            assert not 'flux_amp_points' in kwargs, "Do not supply 'flux_amp_points' if supplying 'flux_amp_range'"
        else:
            amp_span = kwargs.pop('flux_amp_span', 0.05)
            amp_points = kwargs.pop('flux_amp_points', 11)
            self._flux_amp_range = cur_coupler.Amplitude + np.linspace(-amp_span/2, amp_span/2, amp_points)
        if 'wait_times' in kwargs:
            self._wait_times = kwargs.pop('wait_times')
            assert not 'wait_time_max' in kwargs, "Do not supply 'wait_time_max' if supplying 'wait_times'"
            assert not 'wait_time_points' in kwargs, "Do not supply 'wait_time_points' if supplying 'wait_times'"
        else:
            max_wait_time = kwargs.pop('wait_time_max', 250e-9)
            max_wait_points = kwargs.pop('wait_time_points', 30)
            self._wait_times = np.linspace(1e-9,max_wait_time, max_wait_points)

    def run(self, lab):
        fig = plt.figure(figsize=(12, 7.5))
        # Outer grid: 2 columns
        outer = fig.add_gridspec(1, 2, wspace=0.15)
        # Left column: top:bottom = 1:3
        left = outer[0].subgridspec(2, 1, height_ratios=[1, 3], hspace=0.12)
        # Right column: top:bottom = 1:1
        right = outer[1].subgridspec(2, 1, height_ratios=[1, 1], hspace=0.12)
        ax00 = fig.add_subplot(left[0])
        ax10 = fig.add_subplot(left[1])
        ax01 = fig.add_subplot(right[0])
        ax11 = fig.add_subplot(right[1])

        lab.group_open(self._name)
        #
        #CHEVRON SWEEP
        #
        exp = ExpZIChevrons2QFixedCoupler(f'flux_pulse_{self._qubit_ids[0]}_{self._qubit_ids[1]}', self._expt_config, self._qpu, self._qubit_ids,
                                          amplitudes=self._flux_amp_range, wait_times=self._wait_times,
                                          single_shot=True, dont_show_plot=not self._individual_plots)
        lab.run_single(exp)
        #
        #
        fitted_data = np.load(exp._file_path + f'fitted_data.npy', allow_pickle=True).item()
        qubit_ind = fitted_data['qubits'].index(self._qubit_fit)
        state_ind = ['g','e','f'].index(self._state_fit.lower())
        leCounts = fitted_data['pop_qubit_amps_times'][qubit_ind,state_ind]
        #
        dFit = DFitPeakLorentzian()
        data_x, data_y = fitted_data['flux_amps'], np.var(leCounts,axis=1)
        dPkt = dFit.get_fitted_plot(data_x, data_y, dontplot=True)
        #
        ax00.plot(data_x, data_y, 'kx')
        data_x_fine = np.linspace(np.min(data_x), np.max(data_x), 51)
        ax00.plot(data_x_fine, dFit.get_plot_data_from_dpkt(data_x_fine, dPkt), 'r-')
        ax00.set_ylabel('VAR')
        #
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(fitted_data['wait_times'])
        ax10.pcolor(fitted_data['flux_amps'], fitted_data['wait_times']/norm_fac, leCounts.T, cmap='inferno')
        ax10.set_xlabel('Flux Amplitudes (0-1)')
        ax10.set_ylabel(f'Wait Times ({norm_prefix}s)')
        opt_amp = float(dPkt['centre'])
        ax10.vlines([opt_amp], np.min(fitted_data['wait_times'])/norm_fac, np.max(fitted_data['wait_times'])/norm_fac, color='white', linestyle='dashed')
        #
        exp.cur_coupler_obj.Amplitude = opt_amp
        ##############################
        #
        #TIME SWEEP
        #
        exp2 = ExpZIChevrons2QFixedCoupler(f'flux_pulse_{self._qubit_ids[0]}_{self._qubit_ids[1]}_single', lab.CONFIG('ZI'), lab.HAL('QPU'), ["Q1", "Q2"],
                                           amplitudes=np.array([exp.cur_coupler_obj.Amplitude]), wait_times=self._wait_times,
                                           single_shot=True, dont_show_plot=not self._individual_plots)
        lab.run_single(exp2)
        #
        fitted_data2 = np.load(exp2._file_path + f'fitted_data.npy', allow_pickle=True).item()
        leCounts = fitted_data2['pop_qubit_amps_times'][qubit_ind,state_ind][0] #Slice out the single amplitude...
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(fitted_data['wait_times'])
        #
        for m in range(3):
            ax01.plot(fitted_data2['wait_times']/norm_fac, fitted_data2['pop_qubit_amps_times'][qubit_ind,m][0])
        ax01.set_ylabel('Population')
        ax01.legend(['G','E','F'],ncol=3, loc="upper right")
        #
        data_x , data_y = fitted_data2['wait_times']/norm_fac, leCounts
        ax11.plot(data_x , data_y, 'kx')
        # dFit = DFitSinusoid()
        # dPkt = dFit.get_fitted_plot(data_x*1e9,data_y, dontplot=True)
        # ax11.plot(data_x_fine, dFit.get_plot_data_from_dpkt(data_x_fine*1e9, dPkt))
        #Run a spline fit
        leSpline = scipy.interpolate.CubicSpline(data_x , data_y)
        data_x_fine = np.linspace(np.min(data_x), np.max(data_x), data_x.size*3)
        ax11.plot(data_x_fine, leSpline(data_x_fine))
        #Use the spline fit to find the extremum
        cs_der = leSpline.derivative()
        cs_der2 = leSpline.derivative(2)
        roots = cs_der.roots()
        peaks_x = []
        for r in roots:
            if data_x_fine[0] <= r <= data_x_fine[-1]:
                if cs_der2(r) < 0 and self._extremum_type=='max':
                    peaks_x.append(r)
                elif cs_der2(r) > 0 and self._extremum_type=='min':
                    peaks_x.append(r)
        #Approximate the period as there can be multiple initial maxima due to distortions etc...
        approx_period = np.median(np.diff(peaks_x))
        extremum_ind = np.argmin(np.abs(peaks_x-approx_period))
        ax11.plot([peaks_x[extremum_ind]] , [leSpline(peaks_x[extremum_ind])], 'ro')
        ax11.legend([['G','E','F'][state_ind], 'Spline'],ncol=3, loc="upper right")
        #
        ax01.set_xlim([data_x_fine[0], data_x_fine[-1]])
        ax11.set_xlim([data_x_fine[0], data_x_fine[-1]])
        ax11.set_xlabel(f'Wait Time ({norm_prefix}s)')
        ax11.set_ylabel('Population')
        ax01.grid(); ax11.grid()
        #
        exp.cur_coupler_obj.Length = float(peaks_x[extremum_ind])*norm_fac
        ##############################
        lab.group_close()
        #
        ax00.set_title(f'Fitting Flux Amplitude: {opt_amp:.4g}', fontweight='bold')
        ax01.set_title(f"Fitting Wait Time: {float(peaks_x[extremum_ind]):.4g}{norm_prefix}s", fontweight='bold')
        fig.savefig(str(Path(exp._file_path).parent) + '/Overview.png')
        fig.show()
