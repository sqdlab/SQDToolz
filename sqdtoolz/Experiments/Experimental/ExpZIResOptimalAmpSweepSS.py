from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from laboneq_applications.experiments import dispersive_shift
import numpy as np
from sqdtoolz.Utilities.DataIQDiscriminate import DataIQDiscriminate
from sqdtoolz.Experiments.Experimental.ExpZIBlobs import ExpZIBlobs
from sqdtoolz.Variable import VariablePropertyTransient
from matplotlib.lines import Line2D

class ExpZIResOptimalAmpSweepSS(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. This is just a diagnostic experiment."
        kwargs['update'] = False
        assert isinstance(qubit_ids, list) and len(qubit_ids)==1, "Provide only a single qubit, i.e. qubit_ids=['Q0']."
        self._fit_vals = []
        self._states = 'gef'
        self._fit_data = {}
        self._qubit = hal_QPU.get_qubit_obj(qubit_ids[0])
        self._amplitude_range = kwargs.pop('amplitude_range', np.linspace(0.01, 0.9, 10))
        self._readout_fidelity = 0.0
        self._initial_amp = self._qubit.ReadoutAmplitude
        super().__init__(name, expt_config, dispersive_shift, hal_QPU, qubit_ids, **kwargs)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        # if self._calc_single_shot_fidelities:
        kwargs['override_ACQ_params'] = {'AveragingOrder': "SingleShot"}
        var_ampl = VariablePropertyTransient('Amplitude', self._hal_QPU.get_qubit_obj(self._qubit_ids[0]), 'ReadoutAmplitude')
        return super()._run(file_path, sweep_vars=[(var_ampl, self._amplitude_range)], **kwargs)

    def _post_process(self, data):
        # Reset the readout amplitude (can update to max fidelity by calling update_qubits_by_fidelity e.g.)
        self._qubit.ReadoutAmplitude = self._initial_amp

        #This experiment only supports one qubit at a time...
        leDatasets = [self.retrieve_last_dataset(self._qubit_ids[0] + '_' + x) for x in self._states]

        # each of the arrs corresponds to a state
        arrs = [leDatasets[m].get_numpy_array() for m in range((len(self._states)))]

        leCols = plt.rcParams['axes.prop_cycle'].by_key()['color']

        freqs = leDatasets[0].param_vals[2]
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(freqs)  #Should all be the same anyway...

        fig = plt.figure(figsize=(10,12))
        fig.suptitle(f"{self._qubit_ids[0]} single shot readout")
        gs = fig.add_gridspec(5, 5, width_ratios=[1, 1, 1, 1, 0.08])

        # First three rows each span all five columns
        axSepsG = fig.add_subplot(gs[0, 0])
        axSepsE = fig.add_subplot(gs[0, 1])
        axSepsF = fig.add_subplot(gs[0, 2])
        axSepsMean = fig.add_subplot(gs[0, 3])
        axSepsCBar = fig.add_subplot(gs[0, 4])

        axFidsG = fig.add_subplot(gs[1, 0])
        axFidsE = fig.add_subplot(gs[1, 1])
        axFidsF = fig.add_subplot(gs[1, 2])
        axFidsMean = fig.add_subplot(gs[1, 3])
        axFidCBar = fig.add_subplot(gs[1, 4])

        axFidsG.set_ylabel('Readout Amplitude')
        axSepsG.set_ylabel('Readout Amplitude')

        if len(self._states) == 3:
            axSeps = [axSepsG, axSepsE, axSepsF, axSepsMean]
            axFids = [axFidsG, axFidsE, axFidsF, axFidsMean]
            leTitlesSS = ['G','E','F','Mean']
            combos = ['GE', 'EF', 'GF' ,'Mean']
        else:
            axSeps = [axSepsG]
            axFids = [axFidsG, axFidsE, axFidsMean]
            leTitlesSS = ['G','E','Mean']
            combos = ['GE']

        for m, ax in enumerate(axSeps):
            ax.set_xlabel(f'Readout Frequency ({norm_prefix}Hz)')
            ax.set_title(combos[m])
            if m > 0:
                ax.set_ylabel('')
                ax.set_ylabel('')
                ax.set_yticklabels([])
        for  m, ax in enumerate(axFids):
            ax.set_xlabel(f'Readout Frequency ({norm_prefix}Hz)')
            if m > 0:
                ax.set_ylabel('')
                ax.set_ylabel('')
                ax.set_yticklabels([])

        if len(self._states) == 2:
            combs = [[0,1]]
        else:
            combs = [(0,1), (1,2), (0,2)]

        all_diffs = []
        maxSepInds = []
        maxSepFreqInds = []
        maxSepAmpInds = []
        for m in range(len(combs)):
            arr1 = np.mean(arrs[combs[m][0]], axis=1)
            arr2 = np.mean(arrs[combs[m][1]], axis=1)

            cur_diff = np.linalg.norm(arr1 - arr2, axis=2)
            maxSepInds.append(np.argmax(cur_diff))
            all_diffs.append(cur_diff)
        if len(self._states) == 3:
            cur_diff = np.sum(all_diffs, axis=0)
            all_diffs.append(cur_diff)
            maxSepInds.append(np.argmax(cur_diff))

        # IQ SEPERATION
        sep_vmin = min(d.min() for d in all_diffs)
        sep_vmax = max(d.max() for d in all_diffs)

        pcSep = None
        for m, cur_diff in enumerate(all_diffs):
            pcSep = axSeps[m].pcolor(freqs/norm_fac, self._amplitude_range, cur_diff, cmap='plasma', vmin=sep_vmin, vmax=sep_vmax)
            row, col = np.unravel_index(maxSepInds[m], cur_diff.shape)
            axSeps[m].plot([freqs[col]/norm_fac], [self._amplitude_range[row]], 'o', color=leCols[m], label='_nolegend_',  markeredgecolor='black')
            maxSepFreqInds.append(col)
            maxSepAmpInds.append(row)

        fig.colorbar(pcSep, cax=axSepsCBar, label='Separation (a.u.)', ticks=[])

        #FIDELITY
        leIQDiscsAll = []
        leFidsAll = []
        # ge, ef, gf combos
        for k in range(len(self._states)):
            leIQDiscs = [[DataIQDiscriminate([arrs[x][n,:,m,:] for x in combs[k]]) for m in range(freqs.size)] for n in range(self._amplitude_range.size)] 
            leIQDiscsAll.append(leIQDiscs)

            leFids = [[leIQDiscs[n][m].get_fidelities() for m in range(freqs.size)] for n in range(self._amplitude_range.size)]
            leFids = np.array(leFids)
            leFidsAll.append(leFids)
        # gef
        leIQDiscs = [[DataIQDiscriminate([arrs[x][n,:,m,:] for x in range(len(self._states))]) for m in range(freqs.size)] for n in range(self._amplitude_range.size)]
        leIQDiscsAll.append(leIQDiscs)
        leFidsAll.append(np.array([[leIQDiscs[n][m].get_fidelities() for m in range(freqs.size)] for n in range(self._amplitude_range.size)]))

        #Gather fidelity data for each state, calculate the total (mean)
        fidData = []
        for m in range(len(self._states)):
            fidData.append((leFidsAll[m][:,:,0] + leFidsAll[m][:,:,1])/2)
        fidData.append(np.mean(leFidsAll[len(self._states)], axis=2))

        fid_vmin = min(fd.min() for fd in fidData)
        fid_vmax = max(fd.max() for fd in fidData)

        maxFidInds = []
        maxFidFreqInds = []
        maxFidAmpInds = []
        axFirst = None
        for m in range(len(fidData)):
            pcFid = axFids[m].pcolor(freqs/norm_fac, self._amplitude_range, fidData[m], cmap='plasma', vmin=fid_vmin, vmax=fid_vmax)
            maxFidInds.append(np.argmax(fidData[m]))
            row, col = np.unravel_index(maxFidInds[-1], fidData[m].shape)
            axFids[m].plot(freqs[col]/norm_fac, self._amplitude_range[row], 'o', color=leCols[m], label='_nolegend_', markeredgecolor='black')
            maxFidFreqInds.append(col) # saves frequency index for m'th max fidelity
            maxFidAmpInds.append(row) # saves amplitude index for m'th max fidelity

            # BLOBS
            # plot 'best' blobs
            if axFirst == None:
                ax = fig.add_subplot(gs[2, m])
                axFirst = ax
                ax.set_ylabel('Q Channel')
                ax.set_xlabel('I Channel')
            else:
                ax = fig.add_subplot(gs[2, m])
                ax.set_xlabel('I Channel')
            amp, freq = np.unravel_index(maxFidInds[-1], fidData[m].shape)
            if m == 3:
                leIQDiscsAll[m][amp][freq].plot_points(ax)
            else:
                leIQDiscsAll[m][amp][freq].plot_points(ax, [leCols[combs[m][0]], leCols[combs[m][1]]])
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            #
            # CONFUSION MATRICIES
            axA = fig.add_subplot(gs[3, m])
            if m != 3:
                leIQDiscsAll[m][amp][freq].plot_assignment_matrix(axA, sigFigs=2, labels=[leTitlesSS[combs[m][0]].lower(), leTitlesSS[combs[m][1]].lower()])
            else:
                leIQDiscsAll[m][amp][freq].plot_assignment_matrix(axA, sigFigs=2)
            self._readout_fidelity = (leIQDiscsAll[m][amp][freq].get_average_fidelity()*100)
            axA.set_title(f"Mean: {self._readout_fidelity:.4g}%")
            if m > 0:
                ax.set_ylabel('')
                axA.set_ylabel('')

        fig.colorbar(pcFid, cax=axFidCBar, label='Fidelity', ticks=[])

        legendAxBlob = fig.add_subplot(gs[2, 4])
        legendAxBlob.axis('off')
        proxies = [Line2D([0], [0], marker='o', color='w', markerfacecolor=leCols[i], markeredgecolor='black', markersize=8) for i in range(len(self._states))]
        if len(self._states) == 3:
            legendAxBlob.legend(proxies, ['G', 'E', 'F'], loc='center', frameon=False)
        else:
            legendAxBlob.legend(proxies, ['G', 'E'], loc='center', frameon=False)

        self._fit_data = {'freqs':freqs, 'amps':self._amplitude_range, 'maxSepAmpIndices':maxSepAmpInds, 'maxSepFreqIndices':maxSepFreqInds, 'maxFidAmpIndices':maxFidAmpInds, 'maxFidFreqIndices':maxFidFreqInds, 'discriminators':leIQDiscs}

        fig.tight_layout()
        fig.savefig(self._file_path + f'fitted_plot_{self._qubit_ids[0]}.png')
        if not self._dont_show_plot:
            fig.show()
        else:
            plt.close(fig)

    def update_qubits_by_separation(self, transition:str='Total'):
        """
        transition is given as 'ge', 'ef', 'gf' or 'Total' (can capitalise etc.)
        """
        assert len(self._fit_data) > 0, "Must run experiment first."
        transition = transition.lower()
        if len(self._states) == 2:
            assert transition in ['ge', 'total'], "Invalid transition (must be either 'ge' or 'total')"
            ind = 0
        else:
            assert transition in ['ge', 'ef', 'gf', 'total'], "Invalid transition (must be either 'ge', 'ef', 'gf' or 'total')"
            ind = ['ge', 'ef', 'gf', 'total'].index(transition)
        self._qubit.ReadoutFrequency = float( self._fit_data['freqs'][self._fit_data['maxSepFreqIndices'][ind]] )
        self._qubit.ReadoutAmplitude = float( self._fit_data['amps'][self._fit_data['maxSepAmpIndices'][ind]] )
        self._qubit.FidelityReadout = self._readout_fidelity

    def update_qubits_by_fidelity(self, state_fidelity:str='gef'):
        """
        state_fidelity is given as 'ge', 'ef', 'gf' or 'gef' (can capitalise etc.) to take the highest of the respective fidelities as the point.
        """
        assert len(self._fit_data) > 0, "Must run experiment first."
        state_fidelity = state_fidelity.lower()
        assert state_fidelity in ['ge', 'ef', 'gf', 'gef'], "Invalid state (must be either 'ge', 'ef', 'gf' or 'gef')"
        ind = ['ge', 'ef', 'gf', 'gef'].index(state_fidelity)
        self._qubit.ReadoutFrequency = float( self._fit_data['freqs'][self._fit_data['maxFidFreqIndices'][ind]] )
        self._qubit.ReadoutAmplitude = float( self._fit_data['amps'][self._fit_data['maxFidAmpIndices'][ind]] )
        self._qubit.FidelityReadout = self._readout_fidelity

    def print_best_parameters_by_separation(self):
        assert len(self._fit_data) > 0, "Must run experiment first."
        print(f"Max GE: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxSepFreqIndices'][0] ])}Hz, {self._fit_data['amps'][ self._fit_data['maxSepAmpIndices'][0] ]:.3f} amplitude")
        print(f"Max EF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxSepFreqIndices'][1] ])}Hz, {self._fit_data['amps'][ self._fit_data['maxSepAmpIndices'][1] ]:.3f} amplitude")
        print(f"Max GF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxSepFreqIndices'][2] ])}Hz, {self._fit_data['amps'][ self._fit_data['maxSepAmpIndices'][2] ]:.3f} amplitude")

    def print_best_parameters_by_fidelity(self):
        assert len(self._fit_data) > 0, "Must run experiment first."
        print(f"Max GE: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidFreqIndices'][0] ])}Hz, {self._fit_data['amps'][ self._fit_data['maxFidAmpIndices'][0] ]:.3f} amplitude")
        print(f"Max EF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidFreqIndices'][1] ])}Hz, {self._fit_data['amps'][ self._fit_data['maxFidAmpIndices'][1] ]:.3f} amplitude")
        print(f"Max GF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidFreqIndices'][2] ])}Hz, {self._fit_data['amps'][ self._fit_data['maxFidAmpIndices'][2] ]:.3f} amplitude")
        print(f"Max Mean: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidFreqIndices'][3] ])}Hz, {self._fit_data['amps'][ self._fit_data['maxFidAmpIndices'][3] ]:.3f} amplitude")

    def plot_blobs(self, frequency, amplitude):
        assert len(self._fit_data) > 0, "Must run experiment first."
        assert self._calc_single_shot_fidelities, "Must run the experiment in single-shot by setting calc_single_shot_fidelities to True."
        ind_freq = np.argmin(np.abs(frequency-self._fit_data['freqs']))
        ind_amp = np.argmin(np.abs(amplitude-self._fit_data['amps']))
        ExpZIBlobs.plot_fitted_results(self._fit_data['discriminators'][ind_amp][ind_freq], f"($f_r=${Miscellaneous.get_units(self._fit_data['freqs'][ind_freq])}Hz, {self._fit_data['amps'][ind_amp]} amplitude)")