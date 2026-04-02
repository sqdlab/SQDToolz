from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.ZI.ZIACQ import ZIACQ
from laboneq.workflow.logbook import LoggingStore, DEFAULT_LOGGING_STORE, FolderStore
import logging
from laboneq.laboneq_logging import set_log_dir
#
import inspect
from laboneq.workflow.tasks import compile_experiment
from laboneq.pulse_sheet_viewer import pulse_sheet_viewer

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
        self._show_pulse_sheet = kwargs.pop('show_pulse_sheet', False)
    
    def _run(self, file_path, sweep_vars=[], **kwargs):
        self._expt_config.init_instruments()

        leACQ = self._expt_config._hal_ACQ
        assert isinstance(leACQ, ZIACQ), "The ExperimentConfiguration must have a ZIACQ object as its acquisition HAL."
        options = self._workflow_module.experiment_workflow.options()
        leACQopts = leACQ.get_ZI_parameters()
        for x in leACQopts:
            getattr(options, x)(leACQopts[x])
        if hasattr(options, 'update'):
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
        
        set_log_dir(file_path)
        # lePythonLogs = logging.basicConfig(filename=file_path + 'app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        DEFAULT_LOGGING_STORE.deactivate()
        # logging_store = LoggingStore(logger=lePythonLogs, rich=True)
        # logging_store.activate()
        leLogger = logging.getLogger("laboneq")

        # folder_store = FolderStore(file_path)
        # folder_store.activate()
        leSession = leACQ._get_ZI_session()
        leSession.connect(do_emulation=False)
        for handler in leLogger.handlers:
            if isinstance(handler, logging.StreamHandler):
                leLogger.removeHandler(handler)
        
        sig = inspect.signature(self._workflow_module.create_experiment)
        zi_exp_params = list(sig.parameters.keys())
        if 'qubit' in zi_exp_params:
            qubit_kwarg = {'qubit': leQubits[0]}
        else:
            qubit_kwarg = {'qubits': leQubits}
        
        print_pulse_sheet = kwargs.pop('print_pulse_sheet',True)
        print_est_time =  kwargs.pop('print_estimated_execution_time',True)
        if print_pulse_sheet or print_est_time:
            temp_exp = self._workflow_module.create_experiment(
                        leQPU,
                        **qubit_kwarg,
                        **self._args)
            compiled_exp = compile_experiment(leSession, temp_exp)
        if print_pulse_sheet:
            pulse_sheet_viewer.show_pulse_sheet(file_path+'timing_diagram', compiled_exp)
        if print_est_time:      
            print(f"Expected Runtime: {compiled_exp.estimated_runtime:.3f}s")

        exp_workflow = self._workflow_module.experiment_workflow(
            session=leSession,
            qpu=leQPU,
            **qubit_kwarg,
            options=options,
            **self._args
        )

        self._expt_config._hal_ACQ._cur_workflow = exp_workflow
        
        kwargs['skip_init_instruments'] = True

        leData = super()._run(file_path, sweep_vars, **kwargs)

        # folder_store.deactivate()
        # logging_store.deactivate()
        
        return leData

    def _post_process(self, data):
        pass
