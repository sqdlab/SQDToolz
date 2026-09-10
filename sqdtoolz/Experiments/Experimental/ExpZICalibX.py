from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from sqdtoolz.Experiments.Experimental.ZI import single_qubit_gates_sweep
import numpy as np
import scipy.optimize


class ExpZICalibX(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, calib_denominator=1, **kwargs):
        self._qubit_datasets = qubit_ids
        self._hal_QPU = hal_QPU

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. The updates shall be done by calling update_qubit after running the experiment."
        kwargs['update'] = False
        self._fit_vals = []
        self._fit_data = []
        self._failed_qubits = []
        self._cur_angle = 0.0
        self._prev_angle = 0.0
        self._only_every_n = kwargs.pop('only_every_n', 1)
        assert calib_denominator in [1, 2], "Either supply 'calib_denominator' with 1 or 2 for X or X/2 gate calibration"
        self._calib_denominator = calib_denominator
        self._num_gates = kwargs.pop('num_gates', 20)

        self._expected_corr_sign = kwargs.pop('expected_corr_sign', None)
        assert self._expected_corr_sign in (None, 1, -1, 1.0, -1.0), "expected_corr_sign must be None, 1 or -1"

        if calib_denominator == 2:
            gate_label = 'X/2'
        else:
            gate_label = 'X'

        kwargs['gate_lists'] = [[[gate_label] * n for _ in range(len(qubit_ids))] for n in range(1, self._num_gates + 1) if n % self._only_every_n == 0]

        self._n_vals = np.array([n for n in range(1, self._num_gates + 1) if n % self._only_every_n == 0])
        assert len(self._n_vals) >= 4, (
            f"only_every_n={self._only_every_n} with num_gates={self._num_gates} leaves only "
            f"{len(self._n_vals)} gate-count point(s) -- need at least 4 for a reliable fit. "
            "Reduce only_every_n or increase num_gates."
        )
        super().__init__(name, expt_config, single_qubit_gates_sweep, hal_QPU, qubit_ids, **kwargs)

    def _model_func(self, n_vals, corr_pct, decay_per_100):
        if self._calib_denominator == 2:
            return np.sin((n_vals - 1) * (1 + corr_pct / 100) * np.pi / 2) \
                   * np.exp(-(n_vals - 1) / (decay_per_100 * 100)) / 2 + 0.5
        else:
            return np.cos((n_vals - 1) * (1 + corr_pct / 100) * np.pi) \
                   * np.exp(-(n_vals - 1) / (decay_per_100 * 100)) / 2 + 0.5

    def _fit_single_qubit(self, qubit_dataset):
        leData = self.retrieve_last_dataset(qubit_dataset)
        arr = leData.get_numpy_array()
        assert self._normalise_data, "No point analysing this without normalised data..."

        # Get calibration data
        calib_file = qubit_dataset + '_calib'
        leDataCalib = self.retrieve_last_dataset(calib_file)
        dnorm = ExpZIqubit.normalise_qubit_data(leDataCalib, self._transition)
        pop_probs = dnorm.normalise_data(arr)

        n_vals = self._n_vals

        # bounds
        if self._expected_corr_sign == 1 or self._expected_corr_sign == 1.0:
            corr_bounds = (0.0, 10.0)
        elif self._expected_corr_sign == -1 or self._expected_corr_sign == -1.0:
            corr_bounds = (-10.0, 0.0)
        else:
            corr_bounds = (-10.0, 10.0)
        decay_bounds = (0.1, 50.0)

        # initial guess
        corr_grid = np.linspace(*corr_bounds, 801)
        decay_grid = np.geomspace(*decay_bounds, 25)
        best_cost, best_guess = np.inf, (0.0, 1.0)
        for decay in decay_grid:
            residuals = pop_probs[None, :] - self._model_func(n_vals[None, :], corr_grid[:, None], decay)
            costs = np.sum(residuals ** 2, axis=1)
            i = np.argmin(costs)
            if costs[i] < best_cost:
                best_cost, best_guess = costs[i], (corr_grid[i], decay)

        try:
            popt, pcov = scipy.optimize.curve_fit(
                self._model_func, n_vals, pop_probs, p0=best_guess,
                bounds=([corr_bounds[0], decay_bounds[0]], [corr_bounds[1], decay_bounds[1]]),
                method='trf', maxfev=20000,
            )
            perr = np.sqrt(np.diag(pcov)) if np.all(np.isfinite(pcov)) else (np.nan, np.nan)
        except RuntimeError as e:
            raise RuntimeError(f"curve_fit failed to converge from grid guess {best_guess}: {e}")

        fit_data = {'Gate': 'X/2' if self._calib_denominator == 2 else 'X'}
        fit_data['Corr_Fac_Pct'] = popt[0]
        fit_data['Corr_Fac_Pct_err'] = perr[0]
        fit_data['Gate_Decay_per_100'] = popt[1]
        fit_data['Gate_Decay_per_100_err'] = perr[1]

        # --- Goodness-of-fit / sanity checks --------------------------------
        fitted = self._model_func(n_vals, *popt)
        ss_res = np.sum((pop_probs - fitted) ** 2)
        ss_tot = np.sum((pop_probs - np.mean(pop_probs)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        fit_data['r_squared'] = r_squared

        pinned = (np.isclose(popt[0], corr_bounds, atol=0.05).any()
                  or np.isclose(popt[1], decay_bounds, atol=0.05).any())
        if pinned:
            print(f"Fit for '{qubit_dataset}' has a parameter at its bound (corr={popt[0]:.3f}%, decay={popt[1]:.3f}/100) -- do not trust this calibration without inspecting the plot.")
        if not np.isnan(r_squared) and r_squared < 0.8:
            print(f"Poor fit quality for '{qubit_dataset}' (R^2={r_squared:.3f}). Inspect fitted_plot_{qubit_dataset}.png before trusting this correction factor.")

        if (1 + popt[0] / 100) < 1:
            fit_data['Gate_Corr_Fac'] = float(1 / (1 + popt[0] / 100))
        else:
            fit_data['Gate_Corr_Fac'] = 2 - float(1 / (1 + popt[0] / 100))

        fig, ax = plt.subplots(1)
        ax.plot(n_vals, pop_probs, 'o-')
        ax.plot(n_vals, fitted, 'ro')
        ax.set_xlabel('Number of Gates (n)')
        ax.set_ylabel(r'Normalised $e$-Population')
        if self._calib_denominator == 2:
            cur_angle = (1 + popt[0] / 100) * 90
            # self._prev_angle = (1 + popt[0] / 100) * 90
            ax.set_title(f"Actual X/2 angle: {cur_angle:.6f}\n"
                         f"Previous angle: {self._prev_angle:.6f}")
        else:
            cur_angle = (1 + popt[0] / 100) * 180
            # self._prev_angle = (1 + popt[0] / 100) * 180
            ax.set_title(f"Actual X angle: {cur_angle:.6f}\n"
                         f"Previous angle: {self._prev_angle:.6f}")
        self._prev_angle = cur_angle
        fit_data['angle'] = cur_angle
        ax.legend(['Raw', 'Fit'])
        fig.savefig(self._file_path + f'fitted_plot_{qubit_dataset}.png')
        if not self._dont_show_plot:
            fig.show()
        else:
            plt.close(fig)

        fit_data['n_vals'] = n_vals
        np.save(self._file_path + f'fitted_data_{qubit_dataset}.npy', fit_data)
        fit_data['pop_probs'] = pop_probs
        fit_data['fitted_pop_probs'] = fitted
        fit_data['calib_denominator'] = self._calib_denominator
        return fit_data

    def _post_process(self, data):
        self._fit_vals = []
        self._fit_data = []
        self._failed_qubits = []
        for qubit_dataset in self._qubit_datasets:
            try:
                fit_data = self._fit_single_qubit(qubit_dataset)
            except Exception as e:
                print(f"[ExpZICalibX] ERROR: fit failed for qubit '{qubit_dataset}': {e}")
                self._failed_qubits.append(qubit_dataset)
                self._fit_data.append({'qubit_name': qubit_dataset, 'data': None, 'error': str(e)})
                continue
            self._fit_data.append({'qubit_name': qubit_dataset, 'data': fit_data})
            #TODO: Generalise it for EF later?
            self._fit_vals.append({'qubit_obj': self._hal_QPU.get_qubit_obj(qubit_dataset),
                                    'Gate_Corr_Fac': fit_data['Gate_Corr_Fac']})
        if self._failed_qubits:
            print(f"[ExpZICalibX] {len(self._failed_qubits)} qubit(s) have no usable fit and will "
                  f"be skipped by update_qubits: {self._failed_qubits}")

    @staticmethod
    def plot_fitted_results(ax, data: dict, qubit_name=None):
        if 'n_vals' in data:
            data_x = data['n_vals']
        else:
            # Fallback for fit_data saved by an older version of this class that
            # didn't record n_vals: this reproduces the OLD x-axis --
            print("[ExpZICalibX] WARNING: 'n_vals' not found in saved fit data "
                  "(this was fitted with an older version) -- plotting against "
                  "iteration index, which is only correct if only_every_n was 1.")
            data_x = np.arange(0, len(data['pop_probs']), 1)
        data_y = data['pop_probs']
        fit = data['fitted_pop_probs']
        ax.set_ylabel(r'Normalised $e$-Population')
        ax.set_xlabel('Gates')
        ax.grid(visible=True, which='minor'); ax.grid(visible=True, which='major', color='k')
        ax.plot(data_x, data_y, 'kx')
        ax.plot(data_x, fit, 'ro-', lw=1)
        if qubit_name is not None:
            qstring = f'{qubit_name} '
        else:
            qstring = ''
        # r2 = data.get('r_squared', None)
        # r2_str = f" (R^2={r2:.3f})" if r2 is not None and not np.isnan(r2) else ""
        if data['calib_denominator'] == 2:
            ax.set_title(f"{qstring}Actual X/2 angle: {data['angle']:.6f}")
        else:
            ax.set_title(f"{qstring}Actual X angle: {data['angle']:.6f}")
        ax.legend(['Raw', 'Fit'])

    def update_qubits(self, reverse_parity=False):
        assert len(self._fit_vals) > 0, "Must run ExpZICalibX Experiment before qubits can be updated."
        if self._failed_qubits:
            print(f"[ExpZICalibX] Skipping update for qubit(s) with no usable fit: {self._failed_qubits}")
        while len(self._fit_vals) > 0:
            cur_fit = self._fit_vals.pop(0)
            if reverse_parity:
                correction = 2 - cur_fit['Gate_Corr_Fac']
            else:
                correction = cur_fit['Gate_Corr_Fac']
            if self._calib_denominator == 2:
                cur_fit['qubit_obj'].DriveGEAmplitudeXon2 *= correction
            elif self._calib_denominator == 1:
                cur_fit['qubit_obj'].DriveGEAmplitudeX *= correction