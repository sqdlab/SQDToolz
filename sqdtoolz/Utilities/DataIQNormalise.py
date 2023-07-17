import numpy as np
from sqdtoolz.Utilities.FileIO import FileIOReader

class DataIQNormalise:
    def __init__(self, calib_IQ_state_0, calib_IQ_state_1):
        self._calib_pts_IQ_state_0 = calib_IQ_state_0
        self._calib_pts_IQ_state_1 = calib_IQ_state_1

    @classmethod
    def calibrateFromFile(cls, file_path, iq_indices=[0,1], calibPts0_first=True):
        #This assumes that the points are arranged as N state_0 points and N state_1 points unless calibPts0_first is False
        cur_data = FileIOReader(file_path)
        calib_points = cur_data.get_numpy_array()
        calib_0, calib_1 = DataIQNormalise._get_data_from_fileioreader(calib_points, iq_indices, calibPts0_first)
        return cls(calib_0, calib_1)

    @classmethod
    def calibrateFromFileIOReader(cls, fileIOReaderObj, iq_indices=[0,1], calibPts0_first=True):
        calib_points = fileIOReaderObj.get_numpy_array()
        calib_0, calib_1 = DataIQNormalise._get_data_from_fileioreader(calib_points, iq_indices, calibPts0_first)
        return cls(calib_0, calib_1)
    
    @classmethod
    def calibrateFromArray(cls, array_IQs, calibPts0_first=True):
        calib_0, calib_1 = DataIQNormalise._get_data_from_fileioreader(array_IQs, [0,1], calibPts0_first)
        return cls(calib_0, calib_1)

    @staticmethod
    def _get_data_from_fileioreader(calib_points, iq_indices, calibPts0_first):
        numCalibPts = calib_points.shape[0]
        assert numCalibPts % 2 == 0, "The number of calibration points must be an even number (i.e. N for state 0 and N for state 1)"
        numCalibPts = int(numCalibPts / 2)

        if calibPts0_first:
            calib_0 = calib_points[:numCalibPts,[iq_indices[0],iq_indices[1]]]
            calib_1 = calib_points[numCalibPts:,[iq_indices[0],iq_indices[1]]]
        else:
            calib_1 = calib_points[:numCalibPts,[iq_indices[0],iq_indices[1]]]
            calib_0 = calib_points[numCalibPts:,[iq_indices[0],iq_indices[1]]]

        return (calib_0, calib_1)
    
    
    def normalise_data(self, iq_data_array, normalise_to_unity=True, ax=None):
        #iq_data_array is a Nx2 array

        calibG = np.mean(self._calib_pts_IQ_state_0, axis=0)
        calibE = np.mean(self._calib_pts_IQ_state_1, axis=0)

        #Shift Data to origin
        normData = iq_data_array - calibG

        #Rotate Data
        vecSig = calibE - calibG
        angleRot = -np.arctan2(vecSig[1], vecSig[0])

        rotMat = np.array([[np.cos(angleRot), -np.sin(angleRot)],[np.sin(angleRot), np.cos(angleRot)]])
        normData = rotMat @ normData.T

        if normalise_to_unity:
            #Just take I component of the dataset
            finalData = normData[0]/np.linalg.norm(vecSig)
        else:
            finalData = normData

        if ax != None:
            ax.plot(self._calib_pts_IQ_state_0[:,0],self._calib_pts_IQ_state_0[:,1], 'o')
            ax.plot(self._calib_pts_IQ_state_1[:,0],self._calib_pts_IQ_state_1[:,1], 'o')
            ax.plot(iq_data_array[:,0], iq_data_array[:,1], 'ko', alpha=0.5)
            ax.set_xlabel('I'); ax.set_ylabel('Q')
            ax.grid(visible=True, which='minor'); ax.grid(visible=True, which='major', color='k')

        return finalData



