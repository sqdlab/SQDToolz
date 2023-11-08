from sqdtoolz.Experiment import*
from sqdtoolz.Utilities.DataFitting import*
import numpy as np

class ExpResistanceIVsFast(Experiment):
    def __init__(self, name, expt_config, current_index=0, volt_index=1, **kwargs):
        super().__init__(name, expt_config)

        self._current_index = current_index
        self._volt_index = volt_index

        self._average_other_params = kwargs.get('average_other_params', False)

    def _init_aux_datafiles(self):
        self._init_data_file('ResistanceFits')

    def _mid_process(self):
        if self._has_completed_iteration(self._inner_sweep_var_name):
            vals = self._query_current_array_iteration('data', self._inner_sweep_var_name)
           
            voltages = vals[:,self._volt_index]
            currents = vals[:,self._current_index]

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
        rec_params = kwargs.get('rec_params', [])
        self._inner_sweep_var_name = sweep_vars[-1][0].Name
        return super()._run(file_path, sweep_vars, **kwargs)
