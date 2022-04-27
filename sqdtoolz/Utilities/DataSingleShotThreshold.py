import numpy as np
from sqdtoolz.Utilities.FileIO import FileIOReader
from sqdtoolz.Utilities.DataIQNormalise import DataIQNormalise
import matplotlib.pyplot as plt

class DataSingleShotThreshold:
    def __init__(self, data_GE_Reps_IQ, iq_indices=[0,1]):
        assert len(data_GE_Reps_IQ.shape) == 3, "ThData must be 3-dimensional - i.e. slicing on G/E, repetitions, IQ-values."
        self._data_GE_Reps_IQ = data_GE_Reps_IQ
        self._iq_indices = iq_indices
        self.opt_thresh = None

    @classmethod
    def calibrateFromFile(cls, file_path, iq_indices=[0,1]):
        #This assumes that the points are arranged as N state_0 points and N state_1 points unless calibPts0_first is False
        cur_data = FileIOReader(file_path)
        calib_points = cur_data.get_numpy_array()
        return cls(calib_points, iq_indices)

    @classmethod
    def calibrateFromFileIOReader(cls, fileIOReaderObj, iq_indices=[0,1]):
        calib_points = fileIOReaderObj.get_numpy_array()
        return cls(calib_points, iq_indices)
    
    def calc_threshold(self, dont_plot=False):
        arr = self._data_GE_Reps_IQ

        self.data_norm = DataIQNormalise.calibrateFromArray(np.vstack(arr)[:,self._iq_indices], True)
        raw_g = arr[0][:,self._iq_indices]
        data_g = self.data_norm.normalise_data(raw_g, normalise_to_unity=False).T
        raw_e = arr[1][:,self._iq_indices]
        data_e = self.data_norm.normalise_data(raw_e, normalise_to_unity=False).T

        temp = np.concatenate([data_g[:,0], data_e[:,0]])
        threshs = np.linspace(np.min(temp), np.max(temp), 1000)
        max_fidelity, opt_thresh = 0, threshs[0]
        for cur_thresh in threshs:
            fid_g = np.count_nonzero(data_g[:,0] < cur_thresh) / data_g[:,0].size
            fid_e = np.count_nonzero(data_e[:,0] > cur_thresh) / data_e[:,0].size
            cur_fid = 0.5*(fid_g+fid_e)
            if cur_fid > max_fidelity:
                max_fidelity = cur_fid
                opt_thresh = cur_thresh


        self.opt_thresh = opt_thresh
        fid_g = np.count_nonzero(data_g[:,0] < opt_thresh) / data_g[:,0].size
        fid_e = np.count_nonzero(data_e[:,0] > opt_thresh) / data_e[:,0].size

        if not dont_plot:
            fig, axs = plt.subplots(1, 3); fig.set_figwidth(20)

            axs[0].plot(raw_g[:,0], raw_g[:,1], 'bx', alpha=0.4)
            axs[0].plot(raw_e[:,0], raw_e[:,1], 'rx', alpha=0.4)
            axs[0].set_xlabel('I')
            axs[0].set_ylabel('Q')
            axs[0].legend(['Ground', 'Excited'])

            axs[1].plot(data_g[:,0], data_g[:,1], 'bx', alpha=0.4)
            axs[1].plot(data_e[:,0], data_e[:,1], 'rx', alpha=0.4)
            axs[1].set_xlabel('I')
            axs[1].set_ylabel('Q')
            axs[1].legend(['Ground', 'Excited'])

            num_bins = int(data_g.shape[0]/20)
            counts, bins = np.histogram(data_g[:,0], bins=num_bins, density=True)#, histtype=u'step' )
            hist_g_x, hist_g_y = (bins[1::]+bins[0:-1:])/2, counts
            counts, bins = np.histogram(data_e[:,0], bins=num_bins, density=True)#, histtype=u'step' )
            hist_e_x, hist_e_y = (bins[1::]+bins[0:-1:])/2, counts

            axs[2].plot(hist_g_x, hist_g_y)
            axs[2].plot(hist_e_x, hist_e_y)

            axs[2].vlines(opt_thresh, 0,max(np.max(hist_g_y), np.max(hist_e_y)), 'k')
            axs[2].set_xlabel('Rotated Value (I)')
            axs[2].set_ylabel('PDF')

            axs[1].vlines(opt_thresh, min(np.min(data_g[:,1]), np.min(data_e[:,1])), max(np.max(data_g[:,1]), np.max(data_e[:,1])), 'k')

            return fid_g, fid_e, max_fidelity, opt_thresh, fig, axs
        else:
            return fid_g, fid_e, max_fidelity, opt_thresh

    def threshold_data(self, arr_reps_IQ, dont_threshold=False):
        assert self.opt_thresh != None, "Must run calc_threshold() first."

        rot_data = self.data_norm.normalise_data(arr_reps_IQ, normalise_to_unity=False).T

        if dont_threshold:
            return rot_data
        else:
            return 0.5* ( 1+np.sign(rot_data[:,0] - self.opt_thresh) )
