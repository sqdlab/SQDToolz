from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.ZI.ZIACQ import ZIACQ
from laboneq.workflow.logbook import LoggingStore

class ExpZIqubit(Experiment):
    def __init__(self, name, expt_config, workflow_module, hal_QPU, qubit_ids, **kwargs):
        super().__init__(name, expt_config)

        self._workflow_module = workflow_module
        self._hal_QPU = hal_QPU
        self._qubit_ids = qubit_ids
        self._update_params = kwargs.pop('update', False)
        self._normalise_data = kwargs.pop('use_cal_traces', True)
        self._transition = kwargs.pop('transition', 'ge')
        self._plot_ZI = kwargs.pop('ZI_plot', False)
        self._args = kwargs
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        self._expt_config.init_instruments()

        leACQ = self._expt_config._hal_ACQ
        assert isinstance(leACQ, ZIACQ), "The ExperimentConfiguration must has a ZIACQ object as its acquisition HAL."
        options = self._workflow_module.experiment_workflow.options()
        leACQopts = leACQ.get_ZI_parameters()
        for x in leACQopts:
            getattr(options, x)(leACQopts[x])
        getattr(options, 'update')(self._update_params)
        #TODO: Put this into an options parser/dictionary...
        if hasattr(options, 'use_cal_traces'):
            getattr(options, 'use_cal_traces')(self._normalise_data)
        if hasattr(options, 'transition'):
            getattr(options, 'transition')(self._transition)
        options.close_figures(not self._plot_ZI)

        leQPU, leQubits = self._hal_QPU.get_ZI_parameters()
        #Get integer indices of the qubits to select (from names, integers or a mix of both)
        leQubitInds = [self._hal_QPU._resolve_qubit_index(x) for x in self._qubit_ids]
        #Get associated ZI Qubit objects
        leQubits = [leQubits[x] for x in leQubitInds]
        
        logging_store = LoggingStore()
        logging_store.activate()
        leSession = leACQ._get_ZI_session()
        leSession.connect(do_emulation=False)
        try:#TODO: Don't do this...
            exp_workflow = self._workflow_module.experiment_workflow(
                session=leSession,
                qpu=leQPU,
                qubits=leQubits,
                options=options,
                **self._args
            )
        except:
            exp_workflow = self._workflow_module.experiment_workflow(
                session=leSession,
                qpu=leQPU,
                qubit=leQubits[0],
                options=options,
                **self._args
            )
        self._expt_config._hal_ACQ._cur_workflow = exp_workflow
        
        kwargs['skip_init_instruments'] = True

        leData = super()._run(file_path, sweep_vars, **kwargs)

        logging_store.deactivate()  #TODO: Figure out how to access/store this metadata...
        return leData

    def _post_process(self, data):
        pass
