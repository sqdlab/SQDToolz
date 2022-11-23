from sqdtoolz.Experiment import*
from sqdtoolz.Utilities.DataFitting import*
import numpy as np

class ExpResistanceIVs(Experiment):
    def __init__(self, name, expt_config, VAR_volt_set, volt_array, VAR_volt_sense, VAR_current, **kwargs):
        #NOTE: Do not provide voltage sweeping variable; just have other variables (e.g. a dummy variable. Anything
        #provided will be prepended as further outer loops to the already present dummy and voltage sweeps. Also,
        #rec_params will already record sense voltage and current. So only add in additional ones (e.g. temperature
        #as required). Also VAR_volt_sense can be same as VAR_volt_set - doesn't really matter...
        super().__init__(name, expt_config)

        self._VAR_volt_set = VAR_volt_set
        self._volt_array = volt_array
        self._VAR_volt_sense = VAR_volt_sense
        self._VAR_current = VAR_current

        self._average_other_params = kwargs.get('average_other_params', False)

    def _init_aux_datafiles(self):
        self._init_data_file('ResistanceFits')

    def _mid_process(self):
        if self._has_completed_iteration(self._inner_sweep_var_name):
            vals = self._query_current_array_iteration('rec_params', self._inner_sweep_var_name)
           
            voltages = vals[:,0]
            currents = vals[:,1]

            try:
                m,b = np.polyfit(voltages, currents,1)
                resistance = 1/abs(m)
            except:
                resistance = np.nan

            data_dict = { 'Resistance' : resistance, 'CurrentOffset' : b }
            if self._average_other_params and vals.shape[1] > 2:
                for m in range(2,vals.shape[1]):
                    data_dict[self._other_rec_params[m-2]] = np.mean(vals[:,m])

            data_pkt = {
                'parameters' : [],
                'data' : data_dict
            }
            self._push_data_mid_iteration('ResistanceFits', self._inner_sweep_var_name, data_pkt)

    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) > 0, "Must provide sweeping parameter - e.g. even a dummy variable..."
        my_sweep_vars = [(self._VAR_volt_set, self._volt_array)]
        rec_params = kwargs.get('rec_params', [])
        self._inner_sweep_var_name = sweep_vars[-1][0].Name
        self._other_rec_params = [x[2] for x in rec_params] #Check Laboratory function on resolution rules... TODO: Make this a function...
        kwargs['rec_params'] = [(self._VAR_volt_sense, 'Value', self._VAR_volt_sense.Name), (self._VAR_current, 'Value', self._VAR_current.Name)] + rec_params
        return super()._run(file_path, sweep_vars + my_sweep_vars, **kwargs)
