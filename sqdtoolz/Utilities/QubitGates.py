from sqdtoolz.HAL.WaveformSegments import WFS_Gaussian, WFS_Constant
from sqdtoolz.HAL.WaveformGeneric import*
import numpy as np
import scipy.linalg
from sqdtoolz.Utilities.FileIO import FileIOWriter
from sqdtoolz.Variable import VariableInternalTransient
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise

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
                '-Z/2': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(0,0,1,-np.pi/2),
                'H': QubitGatesBase.get_rotation_from_Pauli_Matrix_Arb(1/np.sqrt(2),0,1/np.sqrt(2),np.pi)
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
    def __init__(self, wmft_drive_func, spec_qubit, envelope='Gaussian', arb_rot_func='simple_sine', **kwargs):
        #simple_sine uses the Pi-rotation amplitude and calculates the required fraction for the demanded angle...
        self._wfmt_qubit_drive = wmft_drive_func
        self._spec_qubit = spec_qubit
        if envelope == 'Gaussian':
            self._env_func = WFS_Gaussian
        elif envelope == 'Constant':
            self._env_func = WFS_Constant
        else:
            assert False, "Envelope must be Gaussian or Constant."

        self._pulse_pad = kwargs.get('pulse_pad', 0)

        #TODO: Investigate more sophisticated arbitrary rotation calibration - e.g. spline interpolation?
        assert arb_rot_func=='simple_sine', "The arbitrary rotation function must be either: 'simple_sine' or ..."
        self._arb_rot_func = arb_rot_func

        if not "GE -X/2-Gate Phase" in spec_qubit:
            spec_qubit.add("GE -X/2-Gate Phase", np.pi)
        if not "GE Y/2-Gate Phase" in spec_qubit:
            spec_qubit.add("GE Y/2-Gate Phase", np.pi/2)
        if not "GE -Y/2-Gate Phase" in spec_qubit:
            spec_qubit.add("GE -Y/2-Gate Phase", -np.pi/2)
        if not "GE Y-Gate Phase" in spec_qubit:
            spec_qubit.add("GE Y-Gate Phase", np.pi/2)
        
        self.norm_calib = None

    def calib_normalisation(self, expt_config, load_time, readout_time, file_path = None, fileName = 'dataCalib.h5'):
        store_to_file = isinstance(file_path, str)
        if store_to_file:
            data_fileC = FileIOWriter(file_path + fileName)
            varInd = VariableInternalTransient('State')
        final_dataG = self.run_circuit(['I'], expt_config, load_time, readout_time)
        final_dataE = self.run_circuit(['X'], expt_config, load_time, readout_time)
        if store_to_file:
            data_fileC.push_datapkt(final_dataG, [(varInd, np.arange(2))])
            data_fileC.push_datapkt(final_dataE, [(varInd, np.arange(2))])
            data_fileC.close()
            self.norm_calib = DataIQNormalise.calibrateFromFile(file_path + fileName)
        else:
            self.norm_calib = DataIQNormalise(np.array([[final_dataG['data']['CH_I'][0][0], final_dataG['data']['CH_Q'][0][0]]]), np.array([[final_dataE['data']['CH_I'][0][0], final_dataE['data']['CH_Q'][0][0]]]))

    def normalise_data(self, data):
        #data given as Nx2 array of N IQ-values...
        return self.norm_calib.normalise_data(data)

    def get_qubit_SPEC(self):
        return self._spec_qubit

    def get_available_gates(self):
        #TODO: Add freq_offset along with phase_off to the WFMT to enable Hadamards?
        return ['I', 'X', 'X/2', '-X/2', 'Y', 'Y/2', '-Y/2', 'Z', 'Z/2', '-Z/2', 'H']

    def generate_gates(self, gate_list, gate_set_prefix='gate'):
        assert isinstance(gate_list, (list, tuple)), "gate_list must be given as a list of valid gates."
        ret_gates = []
        phase_offset = 0
        for m, cur_gate in enumerate(gate_list):
            if isinstance(cur_gate, (tuple, list)):
                assert len(cur_gate) == 2, "Arbitrary rotations must be specified as a tuple - e.g. ('Rx',0.02)."
                if cur_gate[0] == 'Rz':
                        angle = cur_gate[1] % (2*np.pi)
                        phase_offset = phase_offset + angle  # in case prev gate was also Rz
                else:
                    #Calculate the amplitude for the rotation
                    if self._arb_rot_func == 'simple_sine':
                        angle = cur_gate[1] % (2*np.pi)
                        if angle > np.pi:
                            angle = angle - 2*np.pi
                        ampl =  self._spec_qubit['GE X-Gate Time'].Value * angle/(np.pi)
                    #
                    if cur_gate[0] == 'Rx':
                        ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset), self._spec_qubit['GE X-Gate Time'].Value, ampl))
                    elif cur_gate[0] == 'Ry':
                        ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset, phase_segment=np.pi/2), self._spec_qubit['GE X-Gate Time'].Value, ampl))
                    else:
                        assert False, "The gate type for arbitrary rotations must be 'Rx', 'Ry' or 'Rz'."
                    phase_offset = 0
            elif cur_gate == 'I':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset), self._spec_qubit['GE X-Gate Time'].Value, 0.0))
                phase_offset = 0
            elif cur_gate == 'X':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset), self._spec_qubit['GE X-Gate Time'].Value, self._spec_qubit['GE X-Gate Amplitude'].Value))
                phase_offset = 0
            elif cur_gate == 'X/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
                phase_offset = 0
            elif cur_gate == '-X/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset, phase_segment=self._spec_qubit['GE -X/2-Gate Phase'].Value), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
                phase_offset = 0
            elif cur_gate == 'Y':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset, phase_segment=self._spec_qubit['GE Y-Gate Phase'].Value), self._spec_qubit['GE X-Gate Time'].Value, self._spec_qubit['GE X-Gate Amplitude'].Value))
                phase_offset = 0
            elif cur_gate == 'Y/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset, phase_segment=self._spec_qubit['GE Y/2-Gate Phase'].Value), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
                phase_offset = 0
            elif cur_gate == '-Y/2':
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset, phase_segment=self._spec_qubit['GE -Y/2-Gate Phase'].Value), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
                phase_offset = 0
            elif cur_gate == 'Z':
                phase_offset = phase_offset + np.pi
            elif cur_gate == 'Z/2':
                phase_offset = phase_offset + np.pi/2
            elif cur_gate == '-Z/2':
                phase_offset = phase_offset - np.pi/2
            elif cur_gate == 'H':
                #Check link: https://www.quantum-inspire.com/kbase/hadamard/
                #Basically we run a Z gate followed by a Y_pi/2 and then a 
                phase_offset += np.pi
                ret_gates.append(self._env_func(f"{gate_set_prefix}{m}", self._wfmt_qubit_drive.apply(phase_offset=phase_offset, phase_segment=self._spec_qubit['GE Y/2-Gate Phase'].Value), self._spec_qubit['GE X/2-Gate Time'].Value, self._spec_qubit['GE X/2-Gate Amplitude'].Value))
                phase_offset = 0
            else:
                assert False, f"Gate \'{cur_gate}\' is not a valid gate."
                
            if self._pulse_pad > 0:
                ret_gates.append(WFS_Constant(f"gate_pad{m}", None, self._pulse_pad, 0.0))
        return ret_gates
    
    def run_circuit(self, gate_list, expt_config, load_time, readout_time):
        i_val, q_val = self.run_circuit_direct(gate_list, expt_config, load_time, readout_time)

        return {
            'data' : {
                'CH_I' : np.array([i_val]),
                'CH_Q' : np.array([q_val]),
            },
            'parameters' : []
        }
    
    def run_circuit_direct(self, gate_list, expt_config, load_time, readout_time, normalise=False):
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
        if normalise and self.norm_calib != None:
            return self.norm_calib.normalise_data(np.array([[i_val[0], q_val[0]]]))[0]
        else:
            return i_val, q_val

# QubitGatesBase.compute_inverse_rotation_Pauli_Matrices( QubitGatesBase.get_rotation_from_Pauli_Matrix('X') )
# a=0