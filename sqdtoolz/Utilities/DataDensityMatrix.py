import itertools
import numpy as np
import scipy.optimize
import matplotlib.pyplot as plt
import functools

class DataDensityMatrix:
    def __init__(self, density_matrix):
        self._rho = density_matrix
        self._num_qubits = int(np.log2(density_matrix.shape[0]))
        self._eigs = np.linalg.eigvalsh(density_matrix)

    @classmethod
    def fromDataViewer(cls, dataviewer, dataviewer_reg='c', readout_correction_matrices=[]):
        """
        This assumes that the data was taken with ExpZIQASM and that the data in register
        dataviewer_reg is structured as the Pauli ordering of measurements. For example, for
        two qubits, it'd be II, IX, IY, IZ, XI, XX etc. So in this case it'd be such that every
        two entries correspond to an array of qubit shots for the first and second qubit
        respectively. If it is an I measurement, the array slot will be ignored in this analysis,
        so it may be None.
        """
        data = dataviewer.get_data(dataviewer_reg)
        return cls(DataDensityMatrix.generate_rho_from_shot_data(data, dataviewer.get_number_of_shots(), readout_correction_matrices))

    @classmethod
    def fromShotData(cls, shot_data, num_shots, readout_correction_matrices=[]):
        """
        Given N qubits, this function takes in a list divided into groups of N where each group corresponds
        to the measurements taken in the Pauli-ordering of measurements (for example, for two qubits, it'd
        be II, IX, IY, IZ, XI, XX etc.). Each group of N has arrays of size given by the number of shots
        (optionally can be None if it is an I-measurement...) with the values being 0,1,2.
        """
        return cls(DataDensityMatrix.generate_rho_from_shot_data(shot_data, num_shots, readout_correction_matrices))

    @staticmethod
    def _project_vector_to_probability_simplex(vec:np.ndarray):
        """
        Projects a vector onto the probability simplex (sum(x) = 1, x >= 0)
        using the projection algorithm given by Lagrange multipliers.
        """
        #Sort entries by descending order
        u = np.sort(vec)[::-1]
        #Find largest K and get lambda
        cssv = np.cumsum(u)
        ind = np.arange(1, vec.size + 1)
        cond = u + (1.0 / ind) * (1.0 - cssv) > 0
        #K is the last index where the condition is True
        K = ind[cond][-1]
        lambda_val = (cssv[K - 1] - 1.0) / K
        #Calculate xi
        return np.maximum(vec - lambda_val, 0)

    @staticmethod
    def generate_rho_from_shot_data(data, num_shots, readout_correction_matrices=[]):
        """
        This assumes that the data was taken with ExpZIQASM and that the data in register
        dataviewer_reg is structured as the Pauli ordering of measurements. For example, for
        two qubits, it'd be II, IX, IY, IZ, XI, XX etc. So in this case it'd be such that every
        two entries correspond to an array of qubit shots for the first and second qubit
        respectively. If it is an I measurement, the array slot will be ignored in this analysis,
        so it may be None.
        """
        num_measurements = len(data)
        N = 0
        while (N+1) * 4**(N+1) <= num_measurements:
            N += 1
        assert N*4**N==num_measurements, "The number of measurements/qubits do not correspond. For N qubits, there should be N*4^N measurements..."
        if len(readout_correction_matrices) > 0:
            assert len(readout_correction_matrices) == N, "When supplying 'readout_correction_matrices', the number of matrices must match the number of qubits."
        #Assuming that data is divided into groups of N (for N qubits) for each measurement type (e.g. IXZI etc.)
        #Also assuming that measurement of 1-state gives -1 eigenvalue for X/Y/Z...
        measurements = [''.join(item) for item in itertools.product(['I','X','Y','Z'], repeat=N)]
        #
        expectation_values = []
        for m,cur_measurement in enumerate(measurements):
            if m == 0:
                expectation_values.append(1.0)
                continue
            cur_data_set = data[m*N:(m+1)*N]
            #
            #Gather current operators that are not identity
            non_id_inds = [x for x in range(N) if cur_measurement[x]!='I']
            cur_dataset_non_id = [cur_data_set[x] for x in non_id_inds]
            #Convert the data subset into binary...
            cur_dataset_non_id = [cur_dataset_non_id[x]*2**x for x in range(len(cur_dataset_non_id))]
            #Sum across it to find out which segment it belongs to (e.g. for 2 non-identity slots, the combinations are 00,01,10,11 for the indices 0,1,2,3)
            cur_dataset_non_id = np.sum(cur_dataset_non_id, axis=0)
            #Gather the counts and calculate probabilities
            leProbs = np.array([np.sum(cur_dataset_non_id==x)/num_shots for x in range(2**len(non_id_inds))])

            if len(readout_correction_matrices) > 0:
                ro_corr = [readout_correction_matrices[x] for x in non_id_inds]
                if len(ro_corr) == 1:
                    ro_corr = ro_corr[0]
                else:
                    ro_corr = functools.reduce(np.kron,ro_corr)
                leProbs = ro_corr @ leProbs
            leProbs = DataDensityMatrix._project_vector_to_probability_simplex(leProbs)
            #The bit_count counts the number of 1s in the binary representation of the integer. Then calculate if it's even/odd parity and map to -1/+1
            expectation_values.append(np.sum([leProbs[x] * (1-2*((x).bit_count()%2)) for x in range(leProbs.shape[0])], axis=0))
            a=0
        #
        return DataDensityMatrix.estimate_rho_from_expectations(np.array(expectation_values))

    @staticmethod
    def estimate_rho_from_expectations(expectation_values):
        """
        Reconstruct an N-qubit physical density matrix from expectation values
        of all N-qubit Pauli strings.

        expectation_values should contain the expectation values corresponding to
        the Pauli strings in the ordering:
            II...I, II...X, II...Y, II...Z, ..., ZZ...Z

        i.e. the ordering generated by itertools.product(['I','X','Y','Z'], repeat=N).
        """
        #Number of Pauli operators = 4^N
        n_paulis = len(expectation_values)
        N = int(np.log2(n_paulis)/2)
        assert 4**N == n_paulis, f"Expected 4^N expectation values, but got {n_paulis}."

        I = np.eye(2, dtype=complex)
        X = np.array([[0, 1], [1, 0]], dtype=complex)
        Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        Z = np.array([[1, 0], [0, -1]], dtype=complex)
        paulis = {'I': I,'X': X,'Y': Y,'Z': Z}
        pauli_strings = list(itertools.product(['I', 'X', 'Y', 'Z'], repeat=N))

        #Create the Pauli tensor-product operators...
        E_ops = []
        for pauli_string in pauli_strings:
            E = np.array([[1]], dtype=complex)
            for p in pauli_string:
                E = np.kron(E, paulis[p])
            E_ops.append(E)

        dim = 2**N
        n_params = 2 * dim * dim

        def params_to_rho(params):
            #First dim^2 are real components, while second dim^2 are imaginary components
            T_real = params[:dim**2].reshape((dim, dim))
            T_imag = params[dim**2:].reshape((dim, dim))
            T = T_real + 1j * T_imag
            #Guarantee Hermitian & positive semidefiniteness
            rho_unnorm = T.conj().T @ T
            #Normalize trace to 1
            trace_val = np.trace(rho_unnorm).real
            if trace_val < 1e-12:
                return np.eye(dim, dtype=complex) / dim  #A bit harsh - could just divide and make it positive...?
            return rho_unnorm / trace_val

        def objective_function(params):
            rho = params_to_rho(params)
            predicted = np.array([np.trace(rho @ E).real for E in E_ops])   #Calculate tr(rho*pauli) to get expectation value
            return np.sum((predicted - expectation_values)**2)              #Compare with measured expectation value

        init_params = np.random.uniform(-1, 1, n_params)
        result = scipy.optimize.minimize(objective_function, init_params, method='BFGS')

        reconstructed_rho = params_to_rho(result.x)

        return reconstructed_rho

    def get_purity(self):
        return np.trace(self._rho @ self._rho).real

    def get_fidelity_pure_state(self, target_state):
        """
        Fidelity between a reconstructed density matrix and a pure
        target state given in the usual computational basis.

        Parameters
        ----------
        target_state : ndarray, shape (2^N)
            Target pure state |psi>. Does not need to be normalized;
            it will be normalized internally.

        Returns
        -------
        float
            State fidelity in [0, 1].
        """
        psi = np.asarray(target_state, dtype=complex).reshape(-1)
        assert self._rho.shape[0] == len(psi), "Target_state dimension must match density matrix size."
        psi_norm = np.linalg.norm(psi)
        assert psi_norm > 0, "Target_state must be non-zero in magnitude."
        psi = psi / psi_norm

        #Don't need to use Uhlmann fidelity here. Just go <psi|rho|psi>
        F = np.vdot(psi, self._rho @ psi)
        F = float(np.real_if_close(F))
        return float(np.clip(F, 0.0, 1.0))


    def plot3D(self, target_state=None, use_abs_phase=False, extra_title='', save_path=None):
        """
        Plot the real part of the density matrix as a 3D bar plot.

        The reconstructed density matrix is taken from self._rho and the
        number of qubits from self._num_qubits.

        Parameters
        ----------
        target_state : array-like, optional
            Target pure state vector |psi>. If provided, its density matrix
            |psi><psi| is shown as transparent red bars underneath the
            reconstructed state.
        use_abs_phase : bool
            If True, then the two plots will be magnitude/phase instead of
            real/imag...

        Notes
        -----
        Computational basis states are shown on both axes.

        Colors:
            Blue  = reconstructed state
            Red   = target state
            Purple = overlap between target and reconstructed state
        """

        # ------------------------------------------------------------------
        # Validate reconstructed density matrix
        # ------------------------------------------------------------------
        rho = np.asarray(self._rho, dtype=complex)
        n_qubits = self._num_qubits
        dim = 2 ** n_qubits

        target_rho = None
        if target_state is not None:
            psi = np.asarray(target_state, dtype=complex).reshape(-1)
            assert self._rho.shape[0] == len(psi), "Target_state dimension must match density matrix size."
            psi_norm = np.linalg.norm(psi)
            assert psi_norm > 0, "Target_state must be non-zero in magnitude."
            psi = psi / psi_norm
            target_rho = np.outer(psi, psi.conj())

        basis_labels = [rf"$|{i:0{n_qubits}b}\rangle$" for i in range(dim)]

        xpos, ypos = np.meshgrid(np.arange(dim), np.arange(dim))
        xpos = xpos.flatten()
        ypos = ypos.flatten()
        zpos = np.zeros_like(xpos, dtype=float)

        dx = dy = 0.7

        if use_abs_phase:
            actual_vals = [np.abs(rho).flatten(), np.angle(rho).flatten()]
            z_labels = ['Magnitude', 'Argument']
        else:
            actual_vals = [np.real(rho).flatten(), np.imag(rho).flatten()]
            z_labels = ['Real part', 'Imag part']
        if target_rho is not None:
            if use_abs_phase:
                target_vals = [np.abs(target_rho).flatten(), np.angle(target_rho).flatten()]
            else:
                target_vals = [np.real(target_rho).flatten(), np.imag(target_rho).flatten()]

        fig = plt.figure(); fig.set_figwidth(12); fig.set_figheight(10)
        axs = [None, None]
        axs[0] = fig.add_subplot(1, 2, 1, projection="3d")
        axs[1] = fig.add_subplot(1, 2, 2, projection="3d")
        #Hack on the position of the title; may not work for more than 2 qubits?
        if target_rho is None:
            fig.suptitle("Density matrix" + extra_title, y=0.7)
        else:
            fig.suptitle("Density matrix" + extra_title + "\nblue = reconstructed, red = target, purple = overlap", y=0.7)

        for m,ax in enumerate(axs):
            if target_rho is not None:
                ax.bar3d(xpos, ypos, zpos, dx, dy, target_vals[m], color="red", alpha=0.10, shade=False)
            ax.bar3d(xpos, ypos, zpos, dx, dy, actual_vals[m], color="steelblue", alpha=0.75, shade=True)

            ax.set_box_aspect(None, zoom=0.85)   #Hack to get z-axis labels to appear in frame...
            ax.set_xticks(np.arange(dim) + dx / 2)
            ax.set_yticks(np.arange(dim) + dy / 2)
            ax.set_xticklabels(basis_labels, rotation=45, ha="right")
            ax.set_yticklabels(basis_labels, rotation=-45, ha="left")
            ax.set_xlabel("Column basis state", labelpad=15)
            ax.set_ylabel("Row basis state", labelpad=15)
            ax.set_zlabel(z_labels[m])

            max_val = np.max(np.abs(actual_vals[m]))
            if target_rho is not None:
                max_val = max(max_val, np.max(np.abs(target_vals[m])))
            max_val = max(max_val, 1e-12)
            if m == 0 and use_abs_phase:
                ax.set_zlim(0, 1.1 * max_val)
            else:
                ax.set_zlim(-1.1 * max_val, 1.1 * max_val)
            ax.view_init(elev=25, azim=-55)
        fig.tight_layout()
        if save_path is not None:
            fig.savefig(save_path)

    @staticmethod
    def generate_tomography_qasm(state_prep, num_qubits, qasm_header_str=None, save=None, qasm_include="stdgates_transmon_fixed_coupler.inc"):
        '''
        Generates a QASM script which does full N-qubit tomography
        for a given state_prep, which is a string containing a QASM script 
        for preparation of a target state (for example, a two qubit Bell state).

        The tomography is ordered such that the bases are measured according 
        to the standard arrangement of Pauli matrices: 
            II...I, II...X, II...Y, II...Z, ..., ZZ...Z
        
        The start of the QASM script (qasm_header_str) with the include file, 
        and the register setup defaults to:
            f"""OPENQASM 3;
            include "{qasm_include}";

            bit[{((num_qubits*4)**num_qubits)/2}] c;
            qubit[{num_qubits}] q;
            """
        
        The qasm script is returned as a string, or can be saved as a file by 
        passing a filename to the save argument, for example: save="test.qasm".
        '''
        assert isinstance(num_qubits, int)
        assert isinstance(state_prep, str)
        #
        N = int(num_qubits)
        if qasm_header_str is None:
            qasm_str = f'OPENQASM 3;\ninclude "{qasm_include}";\n\nbit[{int(((N*4)**N)/2)}] c;\nqubit[{N}] q;\n'
        else:
            qasm_str = qasm_header_str
        
        paulis = sorted({'I', 'X', 'Y', 'Z'})
        pauli_combinations = list(itertools.product(paulis, repeat=N))
        # imports, register etc.
        for m, bases in enumerate(pauli_combinations):
            assert len(bases)==N
            qasm_str += f"\n//"
            for b in range(N):
                qasm_str += f"{bases[b]}"
            qasm_str += "\n" + state_prep + "delay[0] q;\n"
            # do rotations to measure different bases
            for q in range(N):
                if bases[q]=='X':
                    qasm_str += f"ry(-pi/2) q[{q}];\n"
                if bases[q]=='Y':
                    qasm_str += f"rx(pi/2) q[{q}];\n"
            # add delay before measurements 
            qasm_str += "delay[0] q;\n"
            # measures
            for c in range(N):
                if bases[c] != 'I':
                    qasm_str += f"c[{m*N + c}] = measure q[{c}];\n"

        if save is not None: 
            assert isinstance(save, str)
            if not save.endswith(".qasm"):
                save += ".qasm"
            with open(save, "w") as f:
                f.write(qasm_str)

        return qasm_str

    def generate_simulated_shots(num_qubits, state_vector, num_repetitions, readout_confusion_matrices = []):
        """
        Basically generates simulated shot-measurements for density-matrix reconstruction. It then performs
        density matrix reconstruction and returns the shot-data, the DataDensityMatrix object used in
        reconstruction and the pure-state fidelity.

        This generates a list where each entry is data structured as the Pauli ordering of measurements.
        For example, for two qubits, it'd be II, IX, IY, IZ, XI, XX etc. So in this case it'd be such that every
        two entries correspond to an array of qubit shots for the first and second qubit
        respectively. If it is an I measurement, it's basically a Z (i.e. ignore it...).

        It also includes readout_confusion_matrices to simulate readout infidelity (it's structured as:
        Row = assigned, column = actual). It's 2x2 and done for G and E only.
        """
        psi = np.array(state_vector)
        assert psi.size == 2**num_qubits, f"The state-vector must have {2**num_qubits} entries for {num_qubits} qubits (only {state_vector.size} entries supplied)."
        #
        assert len(readout_confusion_matrices) == num_qubits or len(readout_confusion_matrices) == 0, "When supplying readout_confusion_matrices, the list must be a 2x2 matrix for EVERY individual qubit."

        rng = np.random.default_rng()

        pauli_matrices = [np.array([[1,0],[0,1]]), np.array([[0,1],[1,0]]), np.array([[0,-1j],[1j,0]]), np.array([[1,0],[0,-1]])]
        #This is the set of unitary operators needed to change basis before the Z-measurement...
        pauli_map = {'I': np.identity(2), 'X': np.array([[1,1],[1,-1]])/np.sqrt(2), 'Y': np.array([[1,-1j],[1,1j]])/np.sqrt(2), 'Z': np.identity(2)}

        measurements = [''.join(item) for item in itertools.product(['I','X','Y','Z'], repeat=num_qubits)]

        shots = [None]*num_qubits
        for m,cur_measurement in enumerate(measurements):
            if m == 0:
                continue
            
            cur_op = [np.identity(2) for x in range(num_qubits)]
            for ind, pauli in enumerate(cur_measurement):
                if pauli == 'I':
                    continue    #Pauli I does not contribute...
                cur_op[ind] = pauli_map[pauli]
            psi_rot = functools.reduce(np.kron,cur_op) @ psi
            p_comps = np.abs(psi_rot)**2
            #Sample the probabilities to get shots
            sampled_indices = rng.choice(psi.size, size=num_repetitions, p=p_comps) #i.e. choosing index 0-2^N for 00, 01, 10, 11 etc...
            for n in range(num_qubits-1,-1,-1):
                cur_qubit_shots_temp = (2**n & sampled_indices)>>n   #i.e. slicing out the nth bit for the nth qubit...
                #
                cur_qubit_shots = cur_qubit_shots_temp * 1
                #Add readout infidelity
                r = np.random.random(cur_qubit_shots_temp.shape)
                #
                if len(readout_confusion_matrices) > 0:
                    p_0_to_1 = readout_confusion_matrices[n][1,0]
                    p_1_to_0 = readout_confusion_matrices[n][0,1]
                    cur_qubit_shots[(cur_qubit_shots_temp == 0) & (r < p_0_to_1)] = 1
                    cur_qubit_shots[(cur_qubit_shots_temp == 1) & (r < p_1_to_0)] = 0
                #
                shots.append(cur_qubit_shots)
        ddm = DataDensityMatrix.fromShotData(shots, num_repetitions, [np.linalg.inv(readout_confusion) for readout_confusion in readout_confusion_matrices])
        fidelity = ddm.get_fidelity_pure_state(psi)
        return shots, ddm, fidelity
