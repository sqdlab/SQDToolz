import numpy as np
import functools

class Miscellaneous:
    @staticmethod
    def get_units(val, sigFigs = 6):
        if isinstance(val, float) or isinstance(val, int):
            if val <= 0.0:
                return val

            thinspace = u"\u2009"
            def clip_val(value):
                return f'{value:.{sigFigs}g}'

            if val < 1e-6:
                return f'{clip_val(val*1e9)}{thinspace}n'
            if val < 1e-3:
                return f'{clip_val(val*1e6)}{thinspace}μ'
            if val < 1:
                return f'{clip_val(val*1e3)}{thinspace}m'
            if val < 1000:
                return val
            if val < 1e6:
                return f'{clip_val(val*1e-3)}{thinspace}k'
            if val < 1e9:
                return f'{clip_val(val*1e-6)}{thinspace}M'

            return f'{clip_val(val*1e-9)}{thinspace}G'
        else:
            return val

    @staticmethod
    def get_metric_multiplier(vals):
        if isinstance(vals, np.ndarray):
            pass
        elif isinstance(vals, (list,tuple)):
            vals = np.array(isinstance(vals, np.ndarray))
        else:
            vals = np.array([vals])
        
        vals = np.abs(vals)
        vals = vals[vals>0]
        if vals.size == 0:
            return 1, ''    #It's just zero - can't get units here...
        norm_fac = np.round(np.log10(vals).mean()) / 3
        if norm_fac > 0:
            norm_fac = int(norm_fac)*3
        else:
            norm_fac = int(np.floor(norm_fac)*3)
        
        if norm_fac == -9:
            norm_prefix = 'n'
        elif norm_fac == -6:
            norm_prefix = 'μ'
        elif norm_fac == -3:
            norm_prefix = 'm'
        elif norm_fac == 3:
            norm_prefix = 'k'
        elif norm_fac == 6:
            norm_prefix = 'M'
        elif norm_fac == 9:
            norm_prefix = 'G'
        elif norm_fac == 12:
            norm_prefix = 'T'
        else:
            norm_prefix = ''
        
        return 10**norm_fac, norm_prefix

    @staticmethod
    def line_intersections_with_box(a, b, c, bbox_x, bbox_y):
        """
        Basically given a line equation ax+by=c and a bounding box, it finds the two points
        on the box that give the line segment nicely.
        """
        # Unpack bounding box
        x_min, x_max = bbox_x
        y_min, y_max = bbox_y
        candidates = []
        #Intersections with vertical boundaries (x=x_min, x=x_max)
        for x in [x_min, x_max]:
            if b != 0:
                y = (c - a*x) / b
                if y_min <= y <= y_max:
                    candidates.append((x, y))
        #Intersections with horizontal boundaries (y=y_min, y=y_max)
        for y in [y_min, y_max]:
            if a != 0:
                x = (c - b*y) / a
                if x_min <= x <= x_max:
                    candidates.append((x, y))
        #Filter unique points to handle corners
        points = sorted(list(set(candidates)))
        return np.array(points) #Slices as ((x,y), (x,y))

    @staticmethod
    def line_intersection_two_segments(segment1, segment2):
        """
        The lines are given as segment1=((x1,y1),(x2,y2)) etc.
        """
        mx = segment1[0][0]
        my = segment1[0][1]
        nx = segment1[1][0]
        ny = segment1[1][1]
        px = segment2[0][0]
        py = segment2[0][1]
        qx = segment2[1][0]
        qy = segment2[1][1]
        
        t = 1/((nx-mx)*(py-qy) - (px-qx)*(ny-my)) * ((py-qy)*(px-mx) + (qx-px)*(py-my))
        return (mx+(nx-mx)*t, my+(ny-my)*t)

    @staticmethod
    def get_probability_of_basis_states(shot_values, num_qubit_states=2, correction_matrices=[]):
        """
        shot_values gives a list of measurements for every qubit (e.g. for 1 qubit it could be [[0,0,0,1,1,0,0,2,...]], while
        for 2 qubits it could be [[0,0,0,1,1,1,0,...], [1,1,1,0,0,1,2,...]])

        Returned list is basically ordered as binary for 2-state and ternary ordering for 3-state
        """
        num_shots = len(shot_values[0])
        num_qubits = len(shot_values)
        for cur_list in shot_values:
            assert len(cur_list) == num_shots, "The shot_values must have the same number of shots for each qubit."
        shot_values = np.array(shot_values)
        #Take out columns that have 2 in them if it's 2-state readout requested...
        if num_qubit_states == 2:
            shot_values = shot_values[:, ~np.any(shot_values == 2, axis=0)]
            num_shots = shot_values.shape[1]

        #Convert the data into binary/ternary...
        cur_shots = [shot_values[x]*num_qubit_states**x for x in range(num_qubits)]
        #Sum across it to find out which segment it belongs to (e.g. for 2 qubits, the combinations are 00,01,10,11 for the indices 0,1,2,3)
        cur_shots = np.sum(cur_shots, axis=0)
        #Gather the counts and calculate probabilities
        leProbs = np.array([np.sum(cur_shots==x)/num_shots for x in range(num_qubit_states**num_qubits)])

        if len(correction_matrices) > 0:
            assert len(correction_matrices) == num_qubits, "If supplying correction matrices, they must be one for every qubit."
            for m in range(num_qubits):
                assert correction_matrices[m].shape[0] == num_qubit_states and correction_matrices[m].shape[1] == num_qubit_states, f"The readout matrices must be {num_qubit_states}x{num_qubit_states} to match num_qubit_states."
            #
            if len(correction_matrices) == 1:
                correction_matrices = correction_matrices[0]
            else:
                correction_matrices = functools.reduce(np.kron,correction_matrices)
            leProbs = correction_matrices @ leProbs
            leProbs = Miscellaneous.project_vector_to_probability_simplex(leProbs)

        return leProbs

    @staticmethod
    def project_vector_to_probability_simplex(vec:np.ndarray):
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
