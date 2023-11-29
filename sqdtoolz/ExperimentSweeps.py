import numpy as np

class ExperimentSweepBase:
    def get_sweep_indices(self, array_indices, array_shape):
        raise NotImplementedError()


class ExSwpSnake(ExperimentSweepBase):
    def __init__(self, snake_ind):
        self._snake_ind = snake_ind
    
    def get_sweep_indices(self, array_indices, array_shape):
        if self._snake_ind == 0:
            return array_indices
        assert self._snake_ind <= len(array_shape), f"Index {self._snake_ind} exceeds the number of sweeping dimensions ({len(array_shape)} in this case)."
        
        if self._snake_ind == len(array_shape)-1:
            jump = 1
        else:
            jump = int(np.prod(array_shape[self._snake_ind+1:]))
        
        snake_size = array_shape[self._snake_ind]

        outer_sweep_offset = int(np.prod(array_shape[:self._snake_ind]))
        snake_offset = snake_size*jump

        ret_indices = array_indices*1
        for m in range(1, outer_sweep_offset, 2):
            if jump == 1:
                ret_indices[m*snake_offset:(m+1)*snake_offset] = array_indices[m*snake_offset:(m+1)*snake_offset][::-1]
            else:
                for v in range(snake_size):
                    ret_indices[m*snake_offset+v*jump:m*snake_offset+(v+1)*jump] = array_indices[m*snake_offset+(snake_size-v-1)*jump:m*snake_offset+(snake_size-v)*jump]
        
        return ret_indices

class ExSwpRandom(ExperimentSweepBase):
    def __init__(self, snake_ind):
        self._snake_ind = snake_ind
    
    def get_sweep_indices(self, array_indices, array_shape):
        assert self._snake_ind <= len(array_shape), f"Index {self._snake_ind} exceeds the number of sweeping dimensions ({len(array_shape)} in this case)."
        
        if self._snake_ind == len(array_shape)-1:
            jump = 1
        else:
            jump = int(np.prod(array_shape[self._snake_ind+1:]))
        
        snake_size = array_shape[self._snake_ind]

        outer_sweep_offset = int(np.prod(array_shape[:self._snake_ind]))
        snake_offset = snake_size*jump

        ret_indices = array_indices*1
        for m in range(outer_sweep_offset):
            if jump == 1:
                rng = np.random.default_rng()
                ord1 = np.arange(snake_offset); rng.shuffle(ord1)
                ret_indices[m*snake_offset:(m+1)*snake_offset] = array_indices[m*snake_offset:(m+1)*snake_offset][ord1]
            else:
                rng = np.random.default_rng()
                ord1 = np.arange(snake_size); rng.shuffle(ord1)
                for v in range(snake_size):
                    ret_indices[m*snake_offset+v*jump:m*snake_offset+(v+1)*jump] = array_indices[m*snake_offset+ord1[v]*jump:m*snake_offset+(ord1[v]+1)*jump]
        
        return ret_indices

if __name__ == '__main__':
    ExSwpRandom(0).get_sweep_indices(np.arange(10), (10,))
    ExSwpRandom(0).get_sweep_indices(np.arange(3*10*5), (3,10,5))
