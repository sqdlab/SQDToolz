from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ZI import cryo_scope
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sqdtoolz.Utilities.FileIO import FileIODirectory
from pathlib import Path
import sqdtoolz as stz

class ExpZIFluxscope(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._expt_config= expt_config
        self._hal_QPU = hal_QPU
        self._isY = 0 #Will be passed to cryo_scope to determine x90 or y90
        self._qubit_ids = qubit_ids
        assert len(self._qubit_ids)==2, "Also must define a second qubit as Will attempt to optimise a pulse specific to each coupler element"
        

        self._amplitudes = kwargs.get('amplitudes', np.linspace(0.1,1.0,10))
        self._lengths = kwargs.get('lengths', np.linspace(10e-9, 100e-9, 10))
        self._return_data = []
        super().__init__(name, expt_config, cryo_scope, hal_QPU, qubit_ids, 
                         lengths = self._lengths, 
                         amplitudes=self._amplitudes,
                         y90 = bool(self._isY), #pass bool to cryoscope
                         **kwargs
                         )
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Supply the pulse amplitudes/lengths when defining the Experiment object."
        var_xy = VariablePropertyTransient('Axis', self, '_isY')
        super()._run(file_path, sweep_vars=[(var_xy, np.array([1, 0]))], **kwargs)
    
    def _post_process(self, data):
        qubit = self._qubit_ids[0]
        data = self.retrieve_last_dataset(qubit)
        #amplitudes, lengths
        XY = data.param_names
        arr = data.get_numpy_array()
        self._return_data
        





    

        
