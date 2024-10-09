"""
This Experiment performs a qubit flux sweep. At each flux step, we need to first perform a resonator spectroscopy, find the peak, and then perform a qubit spectroscopy.

While each resonator spectroscopy is saved in a separate file, the qubit flux sweep is saved to one file.
"""

from sqdtoolz.Experiment import *
from sqdtoolz.Experiments.Experimental.ExpPeakScouterIQ import ExpPeakScouterIQ

class ExpQubitFluxSweep(Experiment):
    """
    This Experiment performs a qubit flux sweep. At each flux step, we need to first perform a resonator spectroscopy, find the peak, and then perform a qubit spectroscopy.

    While each resonator spectroscopy is saved in a separate file, the qubit flux sweep is saved to one file.

    Use resonator flux sweep to find a good range for the resonator frequency. Qubit frequency range should go lower than the ideal qubit frequency, and not much higher than the ideal.

    Inputs:
    - name (str): name of experiment for the file to be saved as.
    - exp_config (ExperimentConfiguration): custom experiment configuration.
    - VAR_flux (VAR): variable for the flux.
    - flux_range (array): values to which the flux will be set to.
    - VAR_res_freq (VAR): variable for the resonator frequency.
    - res_freq_range (array): values to which the resonator frequency will be set to.
    - SPEC_res (SPEC): experiment specification for the resonator spectroscopy.
    - VAR_qb_freq (VAR): variable for the qubit frequency.
    - qb_freq_range (array): values to which the qubit frequency will be set to.

    Outputs:
    - run function returns data file

    """


    def __init__(self, name, exp_config, VAR_flux, flux_range, VAR_res_freq, res_freq_range, SPEC_res, VAR_qb_freq, qb_freq_range, **kwargs):
        super().__init__(name, exp_config)
        
        self._VAR_flux = VAR_flux
        self._flux_range = flux_range

        self._VAR_res_freq = VAR_res_freq
        self._res_freq_range = res_freq_range

        self._VAR_qb_freq = VAR_qb_freq
        self._qb_freq_range = qb_freq_range

        self._SPEC_res = SPEC_res
        self._res_is_trough = kwargs.get('res_is_trough', True)
        self._res_fit_fano_res = kwargs.get('res_fit_fano_res', True)

        self._exp_config_res = kwargs.get('exp_config_res', exp_config)

    def _res_sweep(self):
        exp = ExpPeakScouterIQ('ResonatorSpec', self._exp_config_res, param_centre = self._SPEC_res['Frequency'], 
            param_width=self._SPEC_res['LineWidth'], is_trough=self._res_is_trough, fit_fano_res=self._res_fit_fano_res)
        temp_data = exp._run(self._temp_file_path + f'resFit_{self._ind}/', [(self._VAR_res_freq, self._res_freq_range)], **self._temp_kwargs)
        exp._post_process(temp_data)
        temp_data.release()
        #
        self._ind += 1

    def _mid_process(self):
        if self._has_completed_iteration(self._VAR_qb_freq.Name):
            self._res_sweep()


    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."
        
        self._ind = 0
        self._temp_file_path = file_path
        self._temp_kwargs = kwargs

        self._res_sweep()

        sweep_vars = [(self._VAR_flux, self._flux_range), (self._VAR_qb_freq, self._qb_freq_range)]

        return super()._run(file_path, sweep_vars, **kwargs)





