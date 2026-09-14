from sqdtoolz.Experiments.Experimental.ExpZIqubit import ExpZIqubit
import matplotlib.pyplot as plt
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from laboneq_applications.experiments import dispersive_shift
import numpy as np
from sqdtoolz.Utilities.DataIQDiscriminate import DataIQDiscriminate
from sqdtoolz.Experiments.Experimental.ExpZIBlobs import ExpZIBlobs

class ExpZIResOptimal(ExpZIqubit):
    def __init__(self, name, expt_config, hal_QPU, qubit_ids, **kwargs):
        self._dont_show_plot = kwargs.pop('dont_show_plot', False)
        assert (not 'update' in kwargs) or ('update' in kwargs and not kwargs['update']), "Don't set 'update=True'. Use update_qubits_by_fidelity(state_fidelity='ge'), or update_qubits_by_separation(transition='ge')."
        kwargs['update'] = False
        # self._fit_vals = []
        assert 'states' in kwargs, "Must provide the states to measure traces over; e.g. 'ge' or 'gef'"
        self._states = kwargs['states']
        self._calc_single_shot_fidelities = kwargs.pop('calc_single_shot_fidelities', False)
        if self._calc_single_shot_fidelities:
            kwargs['do_analysis'] = False   #The default ZI analysis will fail in this mode...
            if self._states != 'gef':
                print('Setting states="gef".')
                self._states = 'gef'
        self._fit_data = {}
        self._readout_fidelity = 0.0
        super().__init__(name, expt_config, dispersive_shift, hal_QPU, qubit_ids, **kwargs)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        if self._calc_single_shot_fidelities:
            kwargs['override_ACQ_params'] = {'AveragingOrder': "SingleShot"}
        return super()._run(file_path, sweep_vars, **kwargs)

    def _post_process(self, data):
        #This experiment only supports one qubit at a time...
        leDatasets = [self.retrieve_last_dataset(self._qubit_ids[0] + '_' + x) for x in self._states]
        arrs = [leDatasets[m].get_numpy_array() for m in range((len(self._states)))]

        leCols = plt.rcParams['axes.prop_cycle'].by_key()['color']
        if self._calc_single_shot_fidelities:
            freqs = leDatasets[0].param_vals[1]
            norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(freqs)  #Should all be the same anyway...

            fig = plt.figure(figsize=(8, 10))
            gs = fig.add_gridspec(5, 4)

            # First three rows each span all four columns
            ax_mag = fig.add_subplot(gs[0, :])
            axSeps = fig.add_subplot(gs[1, :], sharex=ax_mag)
            axFids = fig.add_subplot(gs[2, :], sharex=ax_mag)
            
            ax_mag.grid(); axSeps.grid(); axFids.grid()

            axFids.set_ylabel('State Fidelities')

            axFids.set_xlabel(f'Readout Frequency ({norm_prefix}Hz)')
        else:
            freqs = leDatasets[0].param_vals[0]
            norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(freqs)  #Should all be the same anyway...
            fig, axs = plt.subplots(nrows=2)
            ax_mag = axs[0]
            axSeps = axs[1]
            ax_mag.grid(); axSeps.grid()
        ax_mag.set_xlabel(f'Readout Frequency ({norm_prefix}Hz)')
        axSeps.set_xlabel(f'Readout Frequency ({norm_prefix}Hz)')
        axSeps.set_ylabel('IQ separation')
        fig.suptitle(f"{self._qubit_ids[0]} readout")

        ax_phase = ax_mag.twinx()

        handles = []
        for m in range(len(self._states)):
            if self._calc_single_shot_fidelities:
                arr = np.mean(arrs[m],axis=0)
            else:
                arr = arrs[m]
            mag = np.sqrt(arr[:, 0]**2 + arr[:, 1]**2)
            phase = np.unwrap(np.arctan2(arr[:, 1], arr[:, 0]))
            # Plot magnitude and capture the line object
            line, = ax_mag.plot(freqs/norm_fac, mag, label=self._states[m])
            handles.append(line)
            # Use the same colour for phase, but dashed
            ax_phase.plot(freqs/norm_fac, phase,':',color=line.get_color())

        ax_mag.set_ylabel('Magnitude')
        ax_phase.set_ylabel('Phase (rad) (dotted)')
        ax_mag.legend(handles=handles)


        if len(self._states) == 2:
            combs = [[0,1]]
        else:
            combs = [(0,1), (1,2), (0,2)]

        all_diffs = []
        maxSepInds = []
        for m in range(len(combs)):
            if self._calc_single_shot_fidelities:
                arr1 = np.mean(arrs[combs[m][0]],axis=0)
                arr2 = np.mean(arrs[combs[m][1]],axis=0)
            else:
                arr1 = arrs[combs[m][0]]
                arr2 = arrs[combs[m][1]]
            cur_diff = np.linalg.norm(arr1 - arr2, axis=1)
            axSeps.plot(freqs/norm_fac, cur_diff, color=leCols[m])
            maxSepInds.append(np.argmax(cur_diff))
            axSeps.plot([freqs[maxSepInds[-1]]/norm_fac], [cur_diff[maxSepInds[-1]]], 'o', color=leCols[m], label='_nolegend_')
            all_diffs.append(cur_diff)
        if len(self._states) == 3:
            cur_diff = np.sum(all_diffs, axis=0)
            axSeps.plot(freqs/norm_fac, cur_diff, color=leCols[m+1])
            maxSepInds.append(np.argmax(cur_diff))
            axSeps.plot([freqs[maxSepInds[-1]]/norm_fac], [cur_diff[maxSepInds[-1]]], 'o', color=leCols[m+1], label='_nolegend_')
        if len(self._states) == 2:
            axSeps.legend(['ge'])
            leTitlesSS = ['G','E','Mean']
        else:
            axSeps.legend(['ge', 'ef', 'gf', 'gef'])
            leTitlesSS = ['GE','EF','GF','GEF']
            leStates = ['g', 'e', 'f']

        if self._calc_single_shot_fidelities:
            #FIDELITY
            leIQDiscsAll = []
            leFidsAll = []
            # ge, ef, gf combos
            for k in range(len(self._states)):
                leIQDiscs = [DataIQDiscriminate([arrs[x][:,m,:] for x in combs[k]]) for m in range(freqs.size)]
                leIQDiscsAll.append(leIQDiscs)

                leFids = [leIQDiscs[m].get_fidelities() for m in range(freqs.size)]
                leFids = np.array(leFids)
                leFidsAll.append(leFids)
            # gef
            leIQDiscs = [DataIQDiscriminate([arrs[x][:,m,:] for x in range(len(self._states))]) for m in range(freqs.size)]
            leIQDiscsAll.append(leIQDiscs)
            leFidsAll.append(np.array([leIQDiscs[m].get_fidelities() for m in range(freqs.size)]))

            #Gather fidelity data for each state the total
            fidData = []
            for m in range(len(self._states)):
                fidData.append((leFidsAll[m][:,0] + leFidsAll[m][:,1])/2)
            fidData.append(np.mean(leFidsAll[len(self._states)], axis=1))

            maxFidInds = []
            axFirst = None
            for m in range(len(fidData)):
                axFids.plot(freqs/norm_fac, fidData[m], color = leCols[m])
                maxFidInds.append(np.argmax(fidData[m]))
                axFids.plot(freqs[maxFidInds[-1]]/norm_fac, [fidData[m][maxFidInds[-1]]], 'o', color=leCols[m], label='_nolegend_')

                if axFirst == None:
                    ax = fig.add_subplot(gs[3, m])
                    axFirst = ax
                    ax.set_ylabel('Q Channel')
                else:
                    ax = fig.add_subplot(gs[3, m])
                if m==3:
                    leIQDiscsAll[m][maxFidInds[-1]].plot_points(ax)
                else:
                    leIQDiscsAll[m][maxFidInds[-1]].plot_points(ax, [leCols[combs[m][0]], leCols[combs[m][1]]])
                ax.set_title(leTitlesSS[m])
                ax.set_xlabel('I Channel')
                ax.set_yticklabels([])
                ax.set_xticklabels([])
                #
                axA = fig.add_subplot(gs[4, m])
                if m == 3:
                    leIQDiscsAll[m][maxFidInds[-1]].plot_assignment_matrix(axA, sigFigs=2)
                else:
                    leIQDiscsAll[m][maxFidInds[-1]].plot_assignment_matrix(axA, sigFigs=2, labels=[leStates[combs[m][0]].lower(), leStates[combs[m][1]].lower()])
                self._readout_fidelity = (leIQDiscsAll[m][maxFidInds[-1]].get_average_fidelity()*100)
                axA.set_title(f"Mean: {self._readout_fidelity:.4g}%")
                if m > 0:
                    ax.set_ylabel('')
                    axA.set_ylabel('')
                    axA.set_yticklabels([])

            if len(self._states) == 2:
                axFids.legend(['G','E','Mean'])
            else:
                axFids.legend(['ge','ef','gf','gef'], loc='lower right')

            self._fit_data = {'freqs':freqs, 'maxSepIndices':maxSepInds, 'maxFidIndices':maxFidInds, 'discriminators':leIQDiscs}
        else:
            self._fit_data = {'freqs':freqs, 'maxSepIndices':maxSepInds}

        # fig.subplots_adjust(hspace=0.1)
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
        qubit_obj = self._hal_QPU.get_qubit_obj(self._qubit_ids[0])
        transition = transition.lower()
        if len(self._states) == 2:
            assert transition in ['ge', 'total'], "Invalid transition (must be either 'ge' or 'total')"
            ind = 0
        else:
            assert transition in ['ge', 'ef', 'gf', 'total'], "Invalid transition (must be either 'ge', 'ef', 'gf' or 'total')"
            ind = ['ge', 'ef', 'gf', 'total'].index(transition)
        qubit_obj.ReadoutFrequency = float( self._fit_data['freqs'][ self._fit_data['maxSepIndices'][ind] ] )
        qubit_obj.FidelityReadout = self._readout_fidelity

    def update_qubits_by_fidelity(self, state_fidelity:str='gef'):
        """
        state_fidelity is given as 'ge', 'ef', 'gf' or 'gef' (can capitalise etc.) to take the highest of the respective fidelities as the point.
        """
        assert len(self._fit_data) > 0, "Must run experiment first."
        assert self._calc_single_shot_fidelities, "Must run the experiment in single-shot by setting calc_single_shot_fidelities to True."
        qubit_obj = self._hal_QPU.get_qubit_obj(self._qubit_ids[0])
        state_fidelity = state_fidelity.lower()
        if len(self._states) == 2:
            assert state_fidelity in ['ge'], "Invalid state (must 'ge')"
            ind = ['ge'].index(state_fidelity)
        else:
            assert state_fidelity in ['ge', 'ef', 'gf', 'gef'], "Invalid state (must be either 'ge', 'ef', 'gf' or 'gef')"
            ind = ['ge', 'ef', 'gf', 'gef'].index(state_fidelity)
        qubit_obj.ReadoutFrequency = float( self._fit_data['freqs'][ self._fit_data['maxFidIndices'][ind] ] )
        qubit_obj.FidelityReadout = self._readout_fidelity

    def print_best_frequencies_by_separation(self):
        assert len(self._fit_data) > 0, "Must run experiment first."
        print(f"{self._qubit_ids[0]}")
        if len(self._states) == 2:
            print(f"Max GE: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxSepIndices'][0] ])}Hz\n")
        else:
            print(f"Max GE: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxSepIndices'][0] ])}Hz")
            print(f"Max EF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxSepIndices'][1] ])}Hz")
            print(f"Max GF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxSepIndices'][2] ])}Hz\n")

    def print_best_frequencies_by_fidelity(self):
        assert len(self._fit_data) > 0, "Must run experiment first."
        assert self._calc_single_shot_fidelities, "Must run the experiment in single-shot by setting calc_single_shot_fidelities to True."
        print(f"{self._qubit_ids[0]}")
        print(f"Max GE: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidIndices'][0] ])}Hz")
        print(f"Max EF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidIndices'][1] ])}Hz")
        if len(self._states) == 2:
            print(f"Max Mean: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidIndices'][2] ])}Hz\n")
        else:
            print(f"Max GF: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidIndices'][2] ])}Hz")
            print(f"Max Mean: {Miscellaneous.get_units(self._fit_data['freqs'][ self._fit_data['maxFidIndices'][3] ])}Hz\n")

    def plot_blobs(self, frequency):
        assert len(self._fit_data) > 0, "Must run experiment first."
        assert self._calc_single_shot_fidelities, "Must run the experiment in single-shot by setting calc_single_shot_fidelities to True."
        ind = np.argmin(np.abs(frequency-self._fit_data['freqs']))
        ExpZIBlobs.plot_fitted_results(self._fit_data['discriminators'][ind], f"(Frequency: {Miscellaneous.get_units(self._fit_data['freqs'][ind])}Hz)")