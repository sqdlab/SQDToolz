from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
from sqdtoolz.Experiments.Experimental.ExpZICalibX import ExpZICalibX
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.DataFitting import*
from laboneq_applications.experiments import iq_blobs
from sqdtoolz.Variable import VariablePropertyTransient
from laboneq_applications.experiments import time_traces
import numpy as np

class ExpZIActiveResetTuneup():
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._name = name
        self._expt_config = expt_config
        self._hal_QPU = hal_QPU
        self._qubit_ids = qubit_ids
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        self._update_qubit = kwargs.pop('update_qubit_params', True)
        self._reset_time = kwargs.pop('reset_time', 0.1e-6)
        self._num_gates = kwargs.pop('Xcalib_gates', 50)
        self._states = kwargs.pop('states', "ge")
        self._reset_repititions = kwargs.pop('reset_repititions', 3)
        self._skip_Xcal = kwargs.pop("skip_gate_calibration", False)
        self._num_repititions = self._expt_config._hal_ACQ.NumRepetitions

    def run(self,lab):
        lab.group_open(self._name)
        ## X/2 gate calibration (run twice to check parity)
        if not self._skip_Xcal:
            for qubit in self._qubit_ids:
                qubit_obj = self._hal_QPU.get_qubit_obj(qubit)
                qubit_obj.ResetTime = np.max([5*qubit_obj.T1GE,200e-6])
                qubit_obj.IntegrationKernelType = 'default'
                print(qubit)
                exp = ExpZICalibX(f'Xcalib_{qubit}',self._expt_config, self._hal_QPU, [qubit], 1, num_gates=self._num_gates)
                lab.run_single(exp)
                result = exp._fit_data['Corr_Fac_Pct']
                exp.update_qubits()

                exp = ExpZICalibX(f'Xcalib_{qubit}', self._expt_config,self._hal_QPU, [qubit], 1, num_gates=self._num_gates)
                lab.run_single(exp)

                

                if exp._fit_data['Corr_Fac_Pct'] > result:
                    reverse_parity = True
                else:
                    reverse_parity = False
                exp.update_qubits(reverse_parity=reverse_parity)
                exp = ExpZICalibX(f'Xcalib_{qubit}', self._expt_config, self._hal_QPU, [qubit], 1, num_gates=3*self._num_gates)
                lab.run_single(exp)
            exp.update_qubits(reverse_parity=reverse_parity)
        ## IQ Blobs passive reset > 90 % fidelity
        #TODO Replace with custom IQ_blobs
        exp = ExpZIqubit(f'blobs_{self._name}',self._expt_config, iq_blobs, self._hal_QPU, self._qubit_ids, states=self._states, ZI_plot=False)
        lab.run_single(exp)
        self._qubit_fidelities = self._expt_config._hal_ACQ._temp.tasks["analysis_workflow"].output
        ## Optimal Integration Kernels
        #TODO: some kind of assert so ZI memory limitations arent reached...
        self._expt_config._hal_ACQ.NumRepetitions = 2**14
        self._expt_config.commit()

        for qubit in self._qubit_ids:
            qubit_obj = self._hal_QPU.get_qubit_obj(qubit)
            assert self._qubit_fidelities[qubit] > 0.8, "Single Qubit fidelity must be > 0.8 before attempting active reset, try re-tuning qubit."
            assert np.abs(qubit_obj.ReadoutLO - qubit_obj.ReadoutFrequency) < 500e6, "Readout LO must be closer to resonator frequency for optimal integration weights"
            exp = ExpZIqubit('integration_weights_{qubit}', self._expt_config, time_traces, self._hal_QPU, [qubit], states=self._states, update=True, ZI_plot=False)
            lab.run_single(exp)
            qubit_obj.ResetTime = self._reset_time
            qubit_obj.IntegrationKernelType = 'optimal'
        self._expt_config._hal_ACQ.NumRepetitions = self._num_repititions
        self._expt_config.commit()
        ## Active Reset Rabi check

        ## IQ Blobs active reset > 90 % fidelity
        exp = ExpZIqubit(f'blobs_active_reset_{self._name}', self._expt_config, iq_blobs, self._hal_QPU, self._qubit_ids, states=self._states, update=True, ZI_plot=True,
                 active_reset=True, active_reset_repetitions=self._reset_repititions, active_reset_states=self._states)
        lab.run_single(exp)
        lab.group_close()
