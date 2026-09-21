# Building a density matrix with an OpenQASM script
This example shows how to make use of functions within SQDToolz to automatically generate a QASM script to do full $N$-qubit tomography in the $\{I,X,Y,Z\}$ bases on a given state. We also show how to make use of the inbuilt post-processing functions to easily fgenerate and visualise the resulting density matrix $\rho$. 


## Example: Two-qubit Bell state
This example shows how to create the QASM script for a two-qubit Bell state, and perform tomography. We then show how to run the experiment, and do post-processing.

### 1: Creating the QASM script
We first define the QASM script to generate a two-qubit Bell state, and pass this to `DataDensityMatrix.generate_tomography_qasm` as follows:
```python
from sqdtoolz.Utilities.DataDensityMatrix import DataDensityMatrix

state_prep = """reset q[0];
reset q[1];
h q[0];
h q[1];
cz q[0], q[1];
h q[1];
"""

qasm_full = DataDensityMatrix.generate_tomography_qasm(state_prep, num_qubits=2, save="qasm_twoQubitBellState.qasm")
```
In the above snippet, we generate `qasm_twoQubitBellState.qasm`, and assign the qasm script to the variable `qasm_full`. For each shot, the qasm script measures the Bell state along all combinations of axes on the two qubits - as requred to generate the density matrix $\rho$, and assigns each measurement to a classical bit $c$. The tomography is ordered such that the bases are measured according to the standard arrangement of Pauli matrices: 
            $\qquad II...I, II...X, II...Y, II...Z, ..., ZZ...Z$.

For example, the section of the `qasm_full` corresponding to the $XY$ measurement is shown here:

```openqasm 3
//XY
reset q[0];
reset q[1];
h q[0];
h q[1];
cz q[0], q[1];
h q[1];
delay[0] q;
ry(-pi/2) q[0];
rx(pi/2) q[1];
delay[0] q;
c[12] = measure q[0];
c[13] = measure q[1];
```

It can be seen that a $Y_{-\pi/2}$ gate is applied on the first qubit to measure along $X$, and a $X_{\pi/2}$ gate on the second qubit to make a projective measurement along $Y$. 

For two qubits, there are 16 different measurement pairs ($II, IX, IY, ... , YZ, ZZ$), requiring a total of 32 classical bits (two bits per measurement pair). A `None` value is written to each bit corresponding to an $I$ measurement (this is handled later, in post-processing). The first few lines of `qasm_full` are therefore:

```openqasm 3
OPENQASM 3;
include "stdgates_transmon_fixed_coupler.inc";

bit[32] c;
qubit[2] q;
```

### 2: Running the experiment
Now that we have created the qasm script, we can simply execut it with `ExpZIQASM` as follows:

```python
from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.Experiments.Experimental.ExpZIQASM import ExpZIQASM

lab = Laboratory(instr_config_file = "NQCT_Fridge_01.yaml", save_dir = r"C:/NQCTtemp/QuantWare-D2/Data/")
lab.cold_reload_last_configuration()

acq_params = {}
acq_params['AcquisitionMode'] = "DISCRIMINATION"
acq_params['AveragingOrder'] = 'SingleShot'

exp = ExpZIQASM('test', lab.CONFIG('ZI'), lab.HAL('QPU'), ['Q0', 'Q1', 'Q2', 'Q3', 'Q4'], 'qasm_bellState.qasm')

qregs = exp.get_qubit_regs()
exp.set_qubit_reg_to_ZI_mappings({('q',0):'Q1',('q',1):'Q2'})

lab.run_single(exp, override_ACQ_params=acq_params)
```

Note that we explicitly override the ZI acquisition parameters to be in single shot discrimination mode. This is essential for QASM density matrix creation. We also have the flexibility of changing the mapping between QASm qubits, and physical qubits using the `exp.set_qubit_reg_to_ZI_mappings` function. 

### 3: Post-processing to create the density matrix
To retrieve the data, we make use of `ExpZIQASmDataViewer` as follows:
```python
from sqdtoolz.Experiments.Experimental.ExpZIQASMDataViewer import ExpZIQASMDataViewer

ledv = ExpZIQASMDataViewer('C:/Data/2026-08-27/160437-test/')
ledv.get_inner_slicing_vars()

# ledv.get_data('c', 3)
data = ledv.get_data('c') 
```
The output data will then have an inner slicing variable `c`, with `c[0]` containing an array of 0's, 1's, and (possibly) 2's corresponding to each shot in the measurement. Note that each pair of classical bits (i.e. `c[0]` and `c[1]`) correspond to the first measurement combination $II$.

```python
from sqdtoolz.Utilities.DataDensityMatrix import DataDensityMatrix

leRho = DataDensityMatrix.fromDataViewer(ledv)
leRho.plot3D([1,0,0,1], use_abs_phase=True)
leRho.get_purity(), leRho.get_fidelity_pure_state([1,0,0,1])
```

The above snippet processes the `ExpZIQASmDataViewer` object to generate the density matrix and produce a 3D skyscraper plot. The state purity $\text{Tr}(\rho^2)$, and the pure state fidelity $F=\bra{\Psi}\rho\ket{\Psi}$ can also be directly calculated.

### Correcting for readout infidelity

`DataDensityMatrix.fromDataViewer(dataviewer, dataviewer_reg='c', readout_correction_matrices=[])` accepts an optional `readout_correction_matrices` argument: a list of one $2\times2$ readout-confusion-correction matrix per qubit (row = assigned outcome, column = actual outcome), applied to each measured Pauli-expectation's probability distribution before it's converted into an expectation value. When more than one qubit's non-identity operator appears in a given Pauli string, the relevant per-qubit matrices are combined via a Kronecker product before being applied. After correction, the resulting probabilities are re-projected onto the physical probability simplex (`sum(p) = 1, p >= 0`) to guard against small negative/over-unity values introduced by the correction. If supplied, the list must have exactly as many entries as there are qubits in the tomography (i.e. it must match `num_qubits`); leave it as the default `[]` to skip correction entirely.

### Alternative/testing entry points

Besides `fromDataViewer`, two other constructors are available:
- `DataDensityMatrix.fromShotData(shot_data, num_shots, readout_correction_matrices=[])`: builds the density matrix directly from a list of shot arrays already in Pauli-ordering (the same structure `fromDataViewer` extracts from the data viewer), for cases where the raw shot data comes from somewhere other than `ExpZIQASMDataViewer`.
- `DataDensityMatrix.generate_simulated_shots(num_qubits, state_vector, num_repetitions, readout_confusion_matrices=[])` (static): generates simulated Pauli-ordered shot data for a given ideal state vector (optionally injecting readout infidelity via per-qubit $2\times2$ confusion matrices), reconstructs the density matrix from it, and returns the shot data, the resulting `DataDensityMatrix` object, and the pure-state fidelity — useful for sanity-checking the reconstruction/correction pipeline against a known state without running real hardware.