from sqdtoolz.HAL.WaveformSegments import WFS_Gaussian, WFS_Constant
from sqdtoolz.HAL.WaveformGeneric import*
import numpy as np
import scipy.linalg

class QubitGatesBase:
    def get_available_gates(self):
        raise NotImplementedError()
    
    def generate_gates(self, gate_list):
        raise NotImplementedError()
    
    def get_qubit_SPEC(self):
        raise NotImplementedError()
    
    @staticmethod
    def get_rotation_from_Pauli_Matrix_Arb(rot_x, rot_y, rot_z, angle):
        nDotSigma = np.array([[0,rot_x],[rot_x,0]]) + 1j*np.array([[0,-rot_y],[rot_y,0]]) + np.array([[rot_z,0],[0,-rot_z]])
        return scipy.linalg.expm(-1j*angle/2*nDotSigma)

    @staticmethod
    def get_rotation_from_Pauli_Matrix(gate_name):
        if not hasattr(QubitGatesBase, '_pre_calc_gates'):
            QubitGatesBase._pre_calc_gates = {
                'I': np.identity(2),
                'X': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(1,0,0,np.pi),
                'X/2': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(1,0,0,np.pi/2),
                '-X/2': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(1,0,0,-np.pi/2),
                'Y': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(0,1,0,np.pi),
                'Y/2': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(0,1,0,np.pi/2),
                '-Y/2': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(0,1,0,-np.pi/2),
                'Z': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(0,0,1,np.pi),
                'Z/2': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(0,0,1,np.pi/2),
                '-Z/2': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(0,0,1,-np.pi/2)
                #TODO: Add more gates here!
                }
        assert gate_name in QubitGatesBase._pre_calc_gates, f"{gate_name} is not a recognised gate."
        return QubitGatesBase._pre_calc_gates[gate_name]

    @staticmethod
    def compute_rotation_Pauli_Matrices(rot_mat):
        #Returns (rot_x, rot_y, rot_z, angle) of the inverse matrix for rot_mat
        temp = scipy.linalg.logm(rot_mat) * 2j
        rot_vec = np.array([np.real(temp[1,0]), np.imag(temp[1,0]), temp[0,0]])
        angle = np.linalg.norm(rot_vec)
        if np.abs(angle) < 1e-9:
            return (0,0,0, angle)
        else:
            rot_vec = np.real(rot_vec / angle)
            return (rot_vec[0], rot_vec[1], rot_vec[2], angle)

    @staticmethod
    def compute_inverse_rotation_Pauli_Matrices(rot_mat):
        #Returns (rot_x, rot_y, rot_z, angle) of the inverse matrix for rot_mat
        temp = scipy.linalg.logm(rot_mat) / 1j * 2
        rot_vec = np.array([np.real(temp[1,0]), np.imag(temp[1,0]), temp[0,0]])
        angle = np.linalg.norm(rot_vec)
        if np.abs(angle) < 1e-9:
            return (0,0,0, angle)
        else:
            rot_vec = np.real(rot_vec / angle)
            return (rot_vec[0], rot_vec[1], rot_vec[2], angle)


    @staticmethod
    def convert_Pauli_rotation_to_natural(rot_x, rot_y, rot_z, angle):
        while angle < 0:
            angle += 2*np.pi
        while angle >= 2*np.pi:
            angle -= 2*np.pi
        #TODO: Expand in future to other gates...
        if np.abs(angle) < 1e-9 or np.abs(angle - 2*np.pi) < 1e-9:
            return 'I'
        if np.abs(rot_x) > 0.999:
            prefix = 'X'
            rot_P = rot_x
        elif np.abs(rot_y) > 0.999:
            prefix = 'Y'
            rot_P = rot_y
        elif np.abs(rot_z) > 0.999:
            prefix = 'Z'
            rot_P = rot_z
        else:
            #Return the off-axis rotations here...
            assert False, f"Unhandled rotation type over axis ({rot_x}, {rot_y}, {rot_z}) for angle {angle}."
        
        #Handle on-axis rotations...
        if rot_P > 0:
            if np.abs(angle-np.pi) < 1e-9:
                return f'{prefix}'
            if np.abs(angle-np.pi/2) < 1e-9:
                return f'{prefix}/2'
            if np.abs(angle-3*np.pi/2) < 1e-9:
                return f'-{prefix}/2'
            assert False, f"Cannot write this angle {angle} naturally."
        if rot_P < 0:
            if np.abs(angle-np.pi) < 1e-9:
                return f'{prefix}'
            if np.abs(angle-np.pi/2) < 1e-9:
                return f'-{prefix}/2'
            if np.abs(angle-3*np.pi/2) < 1e-9:
                return f'{prefix}/2'
            assert False, f"Cannot write this angle {angle} naturally."

class TransmonGates(QubitGatesBase):
    def __init__(self, wmft_drive_func, spec_qubit, envelope='Gaussian'):
        self._wfmt_qubit_drive = wmft_drive_func
        self._spec_qubit = spec_qubit
        if envelope == 'Gaussian':
            self._env_func = WFS_Gaussian
        elif envelope == 'Constant':
            self._env_func = WFS_Constant
        else:
            assert False, "Envelope must be Gaussian or Constant."
    
    def get_qubit_SPEC(self):
        return self._spec_qubit

    def get_available_gates(self):
        #TODO: Add freq_offset along with phase_off to the WFMT to enable Hadamards?
        return ['I', 'X', 'X/2', '-X/2', 'Y', 'Y/2', '-Y/2']

    def generate_gates(self, gate_list, gate_set_prefix='gate'):
        assert isinstance(gate_list, (list, tuple)), "gate_list must be given as a list of valid gates."
        ret_gates = []
        for m, cur_gate in enumerate(gate_list):
            if cur_gate == 'I':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(), self._spec_qubit['GE X-Gate Time'].Value, 0.0))
            elif cur_gate == 'X':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(), self._spec_qubit['GE X-Gate Time'].Value, self._spec_qubit['GE X-Gate Amplitude'].Value))
            elif cur_gate == 'X/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
            elif cur_gate == '-X/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_segment=np.pi), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
            elif cur_gate == 'Y':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_segment=np.pi/2), self._spec_qubit['GE X-Gate Time'].Value, self._spec_qubit['GE X-Gate Amplitude'].Value))
            elif cur_gate == 'Y/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_segment=np.pi/2), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
            elif cur_gate == '-Y/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_segment=3*np.pi/2), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
            else:
                assert False, f"Gate \'{cur_gate}\' is not a valid gate."
        return ret_gates
    
    def run_circuit(self, gate_list, expt_config, load_time, readout_time):
        wfm = WaveformGeneric(['qubit'], ['readout'])
        wfm.set_waveform('qubit', [
            WFS_Constant("SEQPAD", None, -1, 0.0),
            WFS_Constant("init", None, load_time, 0.0)]+
            self.generate_gates(gate_list)
            +[
            WFS_Constant("pad", None, 5e-9, 0.0),
            WFS_Constant("read", None, readout_time, 0.0)
        ])
        wfm.set_digital_segments('readout', 'qubit', ['read'])
        self._temp_vars = expt_config.update_waveforms(wfm)
        expt_config.prepare_instruments()

        smpl_data = expt_config.get_data()['data']
        ch_names = sorted([x for x in smpl_data['data']])
        assert len(ch_names) == 2, "The acquisition and processing should only return two channels in the output for I and Q respectively."
        i_val, q_val = smpl_data['data'][ch_names[0]], smpl_data['data'][ch_names[1]]

        return {
            'data' : {
                'CH_I' : np.array([i_val]),
                'CH_Q' : np.array([q_val]),
            },
            'parameters' : []
        }

# QubitGatesBase.compute_inverse_rotation_Pauli_Matrices( QubitGatesBase.get_rotation_from_Pauli_Matrix('X') )
# a=0