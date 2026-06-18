from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import iq_blobs
from sqdtoolz.Variable import VariablePropertyTransient
import numpy as np

class ExpZIActiveResetTuneup(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._qubit_ids = qubit_ids
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        self._update_qubit = kwargs.pop('update_qubit_params', True)
        
        
        super().__init__(name, expt_config, iq_blobs, hal_QPU, [qubit_ids], **kwargs)