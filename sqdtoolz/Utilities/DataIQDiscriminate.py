import numpy as np
from sklearn import svm
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous

class DataIQDiscriminate:
    def __init__(self, calib_IQ_states:list[np.ndarray]):
        """
        Performs the linear-SVM-based state discrimination of readout IQ-points.

        calib_IQ_states given in a list of arrays [(counts1,IQ),(counts2,IQ),...] where the length of this list is
        either 2 or 3 and IQ=2. That is, the counts for the different states can be different...
        """
        self._calib_IQ_states = calib_IQ_states
        self._N = len(self._calib_IQ_states)
        self._num_counts = [x.shape[0] for x in self._calib_IQ_states]
        assert self._N == 2 or self._N == 3, "Number of states to classify must be either 2 or 3."
        #Perform SVM
        #Stack data into [counts,IQ]
        dataX = np.vstack([self._calib_IQ_states[x] for x in range(self._N)])
        datay = np.hstack([np.repeat(x, self._num_counts[x]) for x in range(self._N)])
        #
        leSVM = svm.SVC(kernel='linear', decision_function_shape='ovo') #One-to-One boundaries to ensure that they meet up in the middle
        self._leFit = leSVM.fit(dataX,datay)
        #
        #Calculate classification matrix:
        self._assigned_probs = []
        for m in range(self._N):
            cur_preds = self._leFit.predict(self._calib_IQ_states[m])
            self._assigned_probs.append([np.sum(cur_preds == x)/self._num_counts[x] for x in range(self._N)])
        self._assigned_probs = np.array(self._assigned_probs)

    @classmethod
    def fromZIcalibFileIOReader(cls, fileIOReaderObj):
        #This assumes that the file formats it in the order: G,E,F with the individual IQ pairs... As in, GI,GQ,EI,EQ,FI,FQ...
        calib_points = fileIOReaderObj.get_numpy_array()
        assert calib_points.shape[1] == 4 or calib_points.shape[1] == 6, "Invalid calibration file. The number of channels must be either 4 or 6 (i.e. 2 or 3 state discrimination)."
        if calib_points.shape[1] == 4:
            return cls([calib_points[:,0:2], calib_points[:,2:4]])
        else:
            return cls([calib_points[:,0:2], calib_points[:,2:4], calib_points[:,4:6]])

    def get_line_inequality(self, state1:int, state2:int):
        """
        Returns the SVM line inequality formatted as ax+by+c>0 where the inequality is True if assigning the region as state1.
        """
        assert state1 != state2, "Discrimination must be done between two different states."
        assert state1 < self._N and state1 >= 0, "State index must be zero-indexed up to the number of states that are being classified."
        assert state2 < self._N and state2 >= 0, "State index must be zero-indexed up to the number of states that are being classified."
        state1,state2 = min(state1,state2),max(state1,state2)
        abcEq0 = np.concatenate([self._leFit.coef_[state1+state2], [self._leFit.intercept_[state1+state2]]])    #It's the sum as it maps 01, 02 and 12...
        return abcEq0
    
    def get_assignment_probabilities(self):
        """
        Slices [P,A] with rows P being the prepared states and columns A being the assigned states. The values
        in each entry correspond to the probability of assigning state A given the prepared state P.
        """
        return self._assigned_probs*1.0

    def get_fidelities(self):
        return np.diag(self._assigned_probs)

    def get_average_fidelity(self):
        return np.mean(np.diag(self._assigned_probs))

    def plot_points(self, ax=None):
        if ax == None:
            fig, ax = plt.subplots(1)
        else:
            fig = None

        #Plot the raw data
        leCols = plt.rcParams['axes.prop_cycle'].by_key()['color']
        minX = np.max([np.max(x) for x in self._calib_IQ_states])
        minY = minX
        maxX = np.min([np.min(x) for x in self._calib_IQ_states])
        maxY = maxX
        for cur_feature in range(self._N):
            cur_data = self._calib_IQ_states[cur_feature][:,0], self._calib_IQ_states[cur_feature][:,1]
            minX = min(minX, np.min(cur_data[0]))
            maxX = max(maxX, np.max(cur_data[0]))
            minY = min(minY, np.min(cur_data[1]))
            maxY = max(maxY, np.max(cur_data[1]))
            ax.plot(*cur_data, 'o', alpha=0.2, color=leCols[cur_feature])
        #Plot the mean points
        for cur_feature in range(self._N):
            cur_data = self._calib_IQ_states[cur_feature][:,0], self._calib_IQ_states[cur_feature][:,1]
            ax.plot([np.mean(cur_data[0])], [np.mean(cur_data[1])], 'o', color=leCols[cur_feature], markeredgecolor='black')
        ax.set_xlim([minX,maxX])
        ax.set_ylim([minY,maxY])

        #Note that it's ax+by=c for this function...
        lePtsGE = Miscellaneous.line_intersections_with_box(self._leFit.coef_[0,0], self._leFit.coef_[0,1], -self._leFit.intercept_[0], (minX,maxX), (minY,maxY))
        if self._N == 2:
            #2-state plotting
            ax.plot(lePtsGE[:,0], lePtsGE[:,1], 'k-')
        else:
            #3-state plotting
            #Given that it is OVO, the lines should intersect at the same point...
            lePtsEF = Miscellaneous.line_intersections_with_box(self._leFit.coef_[2,0], self._leFit.coef_[2,1], -self._leFit.intercept_[2], (minX,maxX), (minY,maxY))
            lePtCentre = Miscellaneous.line_intersection_two_segments(lePtsGE, lePtsEF)

            #Trim the line segment so that it satisfies all boundaries in the SVM
            line_segs = []
            #Idea:
            #   Cull GE line with GF line (i.e. exclude the side classifying as F)
            #   Cull GF line with GE line (i.e. exclude the side classifying as E)
            #   Cull EF line with GE line (i.e. exclude the side classifying as G)  But sign needs to be flipped here...
            chk_features = [1,0,0]
            chk_signs = [1,1,-1]
            for cur_feature in range(self._N):
                cur_coefs = self._leFit.coef_[cur_feature]
                cur_int = self._leFit.intercept_[cur_feature]
                lePts = Miscellaneous.line_intersections_with_box(cur_coefs[0], cur_coefs[1], -cur_int, (minX,maxX), (minY,maxY))
                #Now check with another line to chop off the extraneous point...
                cur_coefs = self._leFit.coef_[chk_features[cur_feature]]
                cur_int = self._leFit.intercept_[chk_features[cur_feature]]
                for m in range(2):
                    if (lePts[m][0]*cur_coefs[0] + lePts[m][1]*cur_coefs[1] + cur_int)*chk_signs[cur_feature] >= 0:
                        break
                line_segs.append([lePtCentre, lePts[m]])
            line_segs = np.array(line_segs)

            #Debugging
            # lePts = Miscellaneous.line_intersections_with_box(self._leFit.coef_[0,0], self._leFit.coef_[0,1], -self._leFit.intercept_[0], (minX,maxX), (minY,maxY))
            # ax.plot([lePts[0,0], lePts[1,0]], [lePts[0,1], lePts[1,1]])
            # lePts = Miscellaneous.line_intersections_with_box(self._leFit.coef_[1,0], self._leFit.coef_[1,1], -self._leFit.intercept_[1], (minX,maxX), (minY,maxY))
            # ax.plot([lePts[0,0], lePts[1,0]], [lePts[0,1], lePts[1,1]])
            # lePts = Miscellaneous.line_intersections_with_box(self._leFit.coef_[2,0], self._leFit.coef_[2,1], -self._leFit.intercept_[2], (minX,maxX), (minY,maxY))
            # ax.plot([lePts[0,0], lePts[1,0]], [lePts[0,1], lePts[1,1]])
            # ax.plot([lePtCentre[0]], [lePtCentre[1]], 'bx')

            ax.plot(line_segs[0,:,0], line_segs[0,:,1], 'k-')
            ax.plot(line_segs[1,:,0], line_segs[1,:,1], 'k-')
            ax.plot(line_segs[2,:,0], line_segs[2,:,1], 'k-')
            
            ax.set_xlabel('I Channel')
            ax.set_ylabel('Q Channel')

        return fig

    def plot_assignment_matrix(self, ax=None, labels=['g','e','f'], sigFigs=4):
        if ax == None:
            fig, ax = plt.subplots(1)
        else:
            fig = None

        ax.imshow(self._assigned_probs, cmap='GnBu', vmin=0, vmax=1, aspect='equal')
        for i, j in np.ndindex(self._assigned_probs.shape): ax.text(j, i, f'{self._assigned_probs[i,j]:.{sigFigs}f}', ha='center', va='center', color='white' if i==j else 'black')
        # ax.set_colorbar()
        ticks = np.arange(self._N)
        tick_labels = [f'$|{labels[x]}\\rangle$' for x in range(self._N)]
        ax.set_xticks(ticks, tick_labels)
        ax.set_yticks(ticks, tick_labels)
        ax.set_xlabel('Assigned State')
        ax.set_ylabel('Prepared State')

        return fig

