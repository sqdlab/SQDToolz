from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
from sqdtoolz.Utilities.DataDensityMatrix import DataDensityMatrix
from sqdtoolz.Experiments.Experimental.ExpZIQASM import ExpZIQASM
from sqdtoolz.Experiments.Experimental.ExpZIQASMDataViewer import ExpZIQASMDataViewer
from sqdtoolz.Utilities.DataDensityMatrix import DataDensityMatrix
from sqdtoolz.HAL.ZI.QuantumElements import TunableTransmonCouplerFixed

class ExpZIBellStateFidelity(ExpZIqubit):   
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):

        assert len(qubit_ids)==2, "Must provide exactly two qubits in qubit_ids, e.g. ['Q0', 'Q2']."

        self._name = name
        self._qubit_ids = qubit_ids
        self._hal_QPU = hal_QPU
        self._config = expt_config

        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        self._update_coupler = kwargs.pop('update', True)
        self._readout_correction = kwargs.pop('readout_correction', 'ge')
        assert self._readout_correction in ['ge', 'gef', None], "Provide readout_correction as 'ge', 'gef' or None."

        self._q1_object = self._hal_QPU.get_qubit_obj(qubit_ids[0])
        self._q2_object = self._hal_QPU.get_qubit_obj(qubit_ids[1])

        self._qasm_path = kwargs.pop('save_qasm_path', f'BellStateTomography{qubit_ids[0]}{qubit_ids[1]}.qasm')

        kwargs['coordinate_system'] = kwargs.get('coordinate_system', 'RH')
        assert kwargs['coordinate_system'] in ['LH', 'RH'], "The 'coordinate_system' must be either LH or RH for left/right handed."

        state_prep = """reset q[0];
reset q[1];
h q[0];
h q[1];
cz q[0], q[1];
h q[1];
"""     
        print(f"Building QASM script...")
        self._qasm_full = DataDensityMatrix.generate_tomography_qasm(state_prep, num_qubits=2, save=self._qasm_path)

        self._file_path = None
        self._purity = None
        self._fidelity = None
        
    def run(self, lab):
        all_qubits = [i[0][0] for i in self._hal_QPU._qubits]
        exp = ExpZIQASM(self._name, self._config, self._hal_QPU, all_qubits, self._qasm_path)

        qregs = exp.get_qubit_regs()
        exp.set_qubit_reg_to_ZI_mappings({('q',0): self._qubit_ids[1],('q',1): self._qubit_ids[0]})
        assert len(qregs) <= len(self._qubit_ids), f"The QASM script needs {len(qregs)} while only {len(self._qubit_ids)} qubits have been specified."

        lab.run_single(exp, override_ACQ_params={'AcquisitionMode': 'DISCRIMINATION', 'AveragingOrder': 'SingleShot'})
        self._file_path = exp._file_path

    def post_process(self, use_abs_phase=False, readout_correction=None):
        if readout_correction != None:
            self._readout_correction = readout_correction

        ledv = ExpZIQASMDataViewer(self._file_path)
        ledv.get_inner_slicing_vars()
        #
        if self._readout_correction is not None and self._q1_object.CorrectionMatrix[self._readout_correction] is not None and self._q2_object.CorrectionMatrix[self._readout_correction] is not None:
            leRho = DataDensityMatrix.fromDataViewer(ledv, readout_correction_matrices=[self._q1_object.CorrectionMatrix[self._readout_correction], self._q2_object.CorrectionMatrix[self._readout_correction]])
        elif self._readout_correction is not None:
            print("Unable to apply readout correction as CorrectionMatrix was not found in qubit attributes. Please check the selected correction matrix (i.e. 'ge' or 'gef') is present. Continuing without readout correction.")
            leRho = DataDensityMatrix.fromDataViewer(ledv)
        else:
            leRho = DataDensityMatrix.fromDataViewer(ledv)
        self._fidelity = leRho.get_fidelity_pure_state([1,0,0,1])*100
        leRho.plot3D([1,0,0,1], use_abs_phase=use_abs_phase, extra_title=f' - {self._qubit_ids[0]}{self._qubit_ids[1]}: $F={self._fidelity:.4f}$', save_path=self._file_path + 'BellState.png')
        self._purity = leRho.get_purity() 
        if self._update_coupler:
            cpl = self._hal_QPU.get_coupler_obj_from_qubits(self._qubit_ids[0], self._qubit_ids[1], TunableTransmonCouplerFixed)
            cpl.FidelityBell = self._fidelity
        