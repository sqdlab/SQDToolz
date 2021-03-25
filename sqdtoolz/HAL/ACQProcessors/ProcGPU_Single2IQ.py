from  sqdtoolz.HAL.ACQProcessor import ACQProcessor
from multiprocessing.pool import ThreadPool
import cupy as cp
import numpy as np
import cupyx.scipy.ndimage
import scipy.signal

class ProcGPU_Single2IQ(ACQProcessor):
    def __init__(self):
        self.tp_GPU = ThreadPool(processes=1)
        self.cur_async_handle = None

        self.pipeline = []
        self.cur_data_queue = []
        self.cur_data_processed_I = []
        self.cur_data_processed_Q = []

        #DDC variables
        self._ddc_cur_freq_smplrt = (0,0)
        self._ddc_req_freq_smplrt = (0,0)

    def pass_data(self, arr):
        assert arr.shape[0] == 1, "Currently this class does not support multiple channels."

        self.cur_data_queue.append(arr[0])
        #Start a new thread - otherwise, the thread will automatically check and pop the new array for processing
        if self.cur_async_handle == None:
            self.cur_async_handle = self.tp_GPU.apply_async(self._process_all)
        elif self.cur_async_handle.ready():
            self.cur_async_handle = self.tp_GPU.apply_async(self._process_all)
        self._process_all()

    def get_all_data(self):
        #Wait until ready
        while not self.ready():
            continue
        return (np.concatenate(self.cur_data_processed_I), np.concatenate(self.cur_data_processed_Q))

    def ready(self):
        if self.cur_async_handle == None:
            return True
        return self.cur_async_handle.ready()

    def _process_all(self):
        while (len(self.cur_data_queue) > 0):
            cur_data = self.cur_data_queue.pop()
            
            #Run DDC
            cp_I, cp_Q = self._proc_ddc(cur_data)
            cur_sample_rate = self._ddc_cur_freq_smplrt[1]
            
            #Make a deep copy in case pipeline changes...
            for cur_proc in self.pipeline:
                if cur_proc['type'] == 'FIR_LP':
                    nyq_rate = cur_sample_rate*0.5
                    freq_cutoff_norm = cur_proc['cut_off_hertz']/nyq_rate
                    myFilt_vals = cp.array(scipy.signal.firwin(cur_proc['num_taps'], freq_cutoff_norm, window=cur_proc['window']))
                    cp_I = cupyx.scipy.ndimage.convolve1d(cp_I, myFilt_vals)
                    cp_Q = cupyx.scipy.ndimage.convolve1d(cp_Q, myFilt_vals)
            
            self.cur_data_processed_I.append(cp.asnumpy(cp_I))
            self.cur_data_processed_Q.append(cp.asnumpy(cp_Q))
            del cp_I
            del cp_Q

    def reset_pipeline(self):
        self.pipeline.clear()

    def set_ddc_params(self, sample_rate, ddc_frequency_hertz):
        self._ddc_req_freq_smplrt = (ddc_frequency_hertz, sample_rate)

    def add_FIR_LP(self, num_taps, cut_off_hertz, window='hamming'):
        self.pipeline += [{
            'type' : 'FIR_LP',
            'num_taps' : num_taps,
            'cut_off_hertz' : cut_off_hertz,
            'window' : window
        }]

    def _proc_ddc(self, cur_data):
        samples = cur_data.shape[-1]    #Can be (reps, segments, samples) or (segments, samples), so choose the last index...
        
        ddc_frequency_hertz, sample_rate = self._ddc_req_freq_smplrt
        cur_frequency, cur_sample_rate = self._ddc_cur_freq_smplrt
        #Create a new cosine|sine array if the frequency or sample-rate has changed. Done here instead of set_ddc_params as the
        #array is a function of the number of samples in the current dataset...
        if cur_frequency != ddc_frequency_hertz or cur_sample_rate != sample_rate:
            self._ddc_cur_freq_smplrt = (ddc_frequency_hertz, sample_rate)
            omega = 2*cp.pi*ddc_frequency_hertz/sample_rate
            #TODO: Investigate the following thought later. One could tie up both the sines and cosines via a vstack and call
            #a single multiply command at the expense of a slight reshape or duplication. The trade-off is calling the data
            #array once versus the better cache performance on calling sine/cosine separately - the second approach is taken
            #for convenience here...
            #TODO: Also investigate the idea of calculating sine/cosine on CPU and passing onto GPU instead of using the GPU...
            self._cp_cosines = cp.cos(omega*cp.arange(samples))
            self._cp_sines = cp.sin(omega*cp.arange(samples))
        #Perform the actual DDC...
        cur_data_gpu = cp.array(cur_data)
        cp_I = cp.multiply(cur_data_gpu, self._cp_cosines)
        cp_Q = cp.multiply(cur_data_gpu, self._cp_sines)

        del cur_data_gpu    #Perhaps necessary
        return (cp_I, cp_Q)

        
def runme():
    new_proc = ProcGPU_Single2IQ()
    new_proc.set_ddc_params(1, 0.1)
    new_proc.add_FIR_LP(40, 0.01)

    data_size = 1024*1024#*40
    omega = 2*np.pi*0.1
    data = np.exp(-(np.arange(data_size)-200)**2/10000)*np.sin(omega*np.arange(data_size)+1.5+1.5)
    num_reps = 3
    num_segs = 4
    cur_data = np.hstack([data]*(num_reps*num_segs)).reshape(num_reps,num_segs,data.size)

    new_proc.pass_data([cur_data])

    i_vals, q_vals = new_proc.get_all_data()

    import matplotlib.pyplot as plt
    # print(dataIQ[-1])
    plt.plot(i_vals[0][0])
    plt.plot(q_vals[0][0])
    plt.plot(data)
    plt.show()

    a = 0


if __name__ == '__main__':
    runme()
        