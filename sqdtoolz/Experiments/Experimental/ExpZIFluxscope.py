from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Experiments.Experimental.ZI import cryo_scope
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sqdtoolz.Utilities.FileIO import FileIODirectory
from pathlib import Path
import sqdtoolz as stz

class ExpZIFluxscope:
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._name = name
        self._expt_config= expt_config
        self._hal_QPU = hal_QPU
        self._isY = 0 #Will be passed to cryo_scope to determine x90 or y90
        self._qubit_ids = qubit_ids
        self._kwargs = kwargs
        assert len(self._qubit_ids)==2, "Also must define a second qubit as Will attempt to optimise a pulse specific to each coupler element"
        

        self._amplitudes = kwargs.get('amplitudes', np.linspace(0.1,1.0,10))
        self._lengths = kwargs.get('lengths', np.linspace(10e-9, 100e-9, 10))
        self.data = {}

    def run(self, lab, **kwargs):
        qubit = self._qubit_ids[0]
        lab.group_open(self._name)
        exp_X = ExpZIqubit(f'cryoscope_{qubit}_X', self._expt_config, cryo_scope, self._hal_QPU, self._qubit_ids, 
                         lengths = self._lengths, 
                         amplitudes=self._amplitudes,
                         y90 = False,
                         **self._kwargs
                         )
        lab.run_single(exp_X, **kwargs)

        dataX = exp_X.retrieve_last_dataset(qubit)
        self.data['X'] = dataX.get_numpy_array()

        exp_Y = ExpZIqubit(f'cryoscope_{qubit}_Y', self._expt_config, cryo_scope, self._hal_QPU, self._qubit_ids, 
                        lengths = self._lengths, 
                        amplitudes=self._amplitudes,
                        y90 = True,
                        **self._kwargs
                        )
        lab.run_single(exp_Y, **kwargs)

        dataY = exp_Y.retrieve_last_dataset(qubit)
        self.data['Y'] = dataY.get_numpy_array()

        lab.group_close()

        





    

        
