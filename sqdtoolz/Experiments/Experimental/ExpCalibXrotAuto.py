import numpy as np
from sqdtoolz.Experiment import *
from sqdtoolz.Variable import VariablePropertyTransient
from sqdtoolz.HAL.WaveformGeneric import *
from sqdtoolz.HAL.WaveformSegments import *
from sqdtoolz.Utilities.DataFitting import *
from sqdtoolz.Experiments.Experimental.ExpCalibGE import *
from sqdtoolz.Utilities.QubitGates import QubitGatesBase

import matplotlib.pyplot as plt
import scipy.interpolate
import scipy.optimize
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous

class ExpCalibXrotAuto(Experiment):   
    def __init__(self, name, expt_config, qubit_gate_obj, gate_calib, ampl_offsets, num_samples, sample_skip_step=1, **kwargs):
        super().__init__(name, expt_config)

        # assert isinstance(qubit_gate_obj, QubitGatesBase), "qubit_gate_obj must be a QubitGates object (e.g. TransmonGates)"
        self._qubit_gate_obj = qubit_gate_obj

        if gate_calib == 'X':
            self._samples = np.arange(0, num_samples*2, 2)*sample_skip_step
        elif gate_calib == 'X/2':
            self._samples = np.arange(0, num_samples*sample_skip_step, sample_skip_step)*2+1
        else:
            assert False, "gate_calib must be: 'X' or 'X/2'"
        self._ampl_offsets = ampl_offsets
        
        #Calculate default load time via T1 of qubit or default to 80e-6
        def_load_time = self._qubit_gate_obj.get_qubit_SPEC()['GE T1'].Value * 6
        if def_load_time == 0:
            def_load_time = 80e-6
        #Override the load-time if one is specified explicitly
        self.load_time = kwargs.get('load_time', def_load_time)
        
        self.readout_time = kwargs.get('readout_time', 2e-6)
        
        self.normalise_reps = kwargs.get('normalise_reps', 10)

        self._gate_calib = gate_calib
        self._sweep_range = kwargs.get('sweep_range', (-0.5,0.5))
        
    def _run(self, file_path, sweep_vars=[], **kwargs):
        assert len(sweep_vars) == 0, "Cannot specify sweeping variables in this experiment."
        
        self._setup_progress_bar(**kwargs)
        self._expt_config.init_instruments()
        
        data_file = FileIOWriter(file_path + 'data.h5')
        varAmpl = VariableInternalTransient('AmplValue')
        varNumG = VariableInternalTransient('NumGates')

        self._qubit_gate_obj.calib_normalisation(self._expt_config, self.load_time, self.readout_time, file_path)
        self._file_path = file_path

        origAmplX = self._qubit_gate_obj.get_qubit_SPEC()['GE X-Gate Amplitude'].Value
        origAmplXon2 = self._qubit_gate_obj.get_qubit_SPEC()['GE X/2-Gate Amplitude'].Value

        for m, ampl_off in enumerate(self._ampl_offsets):
            if self._gate_calib == 'X':
                cur_gate = 'X'
                self._qubit_gate_obj.get_qubit_SPEC()['GE X-Gate Amplitude'].Value = origAmplX + ampl_off
            elif self._gate_calib == 'X/2':
                cur_gate = 'X/2'
                self._qubit_gate_obj.get_qubit_SPEC()['GE X/2-Gate Amplitude'].Value = origAmplXon2 + ampl_off

            for g in self._samples:
                cur_seq = [cur_gate]*g
                final_data = self._qubit_gate_obj.run_circuit(cur_seq, self._expt_config, self.load_time, self.readout_time)
                data_file.push_datapkt(final_data, [(varAmpl, self._ampl_offsets), (varNumG, self._samples)])
            self._update_progress_bar((m+1)/self._ampl_offsets.size)
        data_file.close()

        self._qubit_gate_obj.get_qubit_SPEC()['GE X-Gate Amplitude'].Value = origAmplX
        self._qubit_gate_obj.get_qubit_SPEC()['GE X/2-Gate Amplitude'].Value = origAmplXon2

        self.file_io_read_calib = FileIOReader(file_path + 'dataCalib.h5')

        return FileIOReader(file_path + 'data.h5')

    def _post_process(self, data):
        arr = data.get_numpy_array()
        probs = [self._qubit_gate_obj.normalise_data(x) for x in arr]

        sds = [np.std(y) for y in probs]

        fig, ax = plt.subplots(ncols=3); fig.set_figwidth(18); ax[1].grid(); ax[2].grid()

        leSpline = scipy.interpolate.UnivariateSpline(self._ampl_offsets, sds, k=2)
        leSpline.set_smoothing_factor(np.mean(np.diff(self._ampl_offsets)*2))
        fitX = np.linspace(self._ampl_offsets[0], self._ampl_offsets[-1], 50)

        sol = scipy.optimize.minimize(leSpline, np.mean(self._ampl_offsets))

        ax[0].pcolormesh(self._samples, self._ampl_offsets, probs)
        ax[0].set_xlabel('Number of Gates')
        ax[0].set_ylabel('Amplitude Offset')
        ax[0].set_title('Ex. Population (should be flat)')

        for cur_pops in probs:
            ax[1].plot(self._samples, cur_pops, 'x-')
        ax[1].legend([Miscellaneous.get_units(x) for x in self._ampl_offsets])
        ax[1].set_xlabel('Number of Gates')
        ax[1].set_ylabel('Excited State Population')
        ax[1].set_title('Population traces over gate count')

        ax[2].plot(fitX, leSpline(fitX), 'k')
        ax[2].plot(self._ampl_offsets, sds)
        ax[2].plot(sol.x, leSpline(sol.x), 'x')
        ax[2].set_xlabel('Amplitude Offset')
        ax[2].set_ylabel('SD in population')
        ax[2].set_title('Optimising Amplitude Offset')

        fig.show()
        fig.savefig(self._file_path + 'Fitted Parameters.png')

        self._opt_val = sol.x[0]

        return data
    
    def commit_to_SPEC(self):
        if self._gate_calib == 'X':
            self._qubit_gate_obj.get_qubit_SPEC()['GE X-Gate Amplitude'].Value += self._opt_val
        elif self._gate_calib == 'X/2':
            self._qubit_gate_obj.get_qubit_SPEC()['GE X/2-Gate Amplitude'].Value += self._opt_val
