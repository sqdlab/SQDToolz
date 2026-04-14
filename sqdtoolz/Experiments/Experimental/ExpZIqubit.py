from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.ZI.ZIACQ import ZIACQ
from laboneq.workflow.logbook import LoggingStore, DEFAULT_LOGGING_STORE, FolderStore
import logging
from laboneq.laboneq_logging import set_log_dir
#
import inspect
from laboneq.workflow.tasks import compile_experiment
from laboneq.pulse_sheet_viewer import pulse_sheet_viewer
#
from laboneq.simulator.output_simulator import OutputSimulator
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
from bokeh.plotting import figure, save
from bokeh.models import ColumnDataSource, WheelZoomTool, PanTool, BoxZoomTool, ResetTool
from bokeh.layouts import gridplot
from bokeh.resources import CDN
from bokeh.embed import file_html
import numpy as np

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
        if hasattr(options, 'close_figures'):
            options.close_figures(not self._plot_ZI)

        leQPU, leQubits, leQcouplers = self._hal_QPU.get_ZI_parameters()
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
        leSession.connect(do_emulation=kwargs.get('debug_skip_experiment',False))
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
                        options=options,
                        **self._args)
            compiled_exp = compile_experiment(leSession, temp_exp)
        if print_pulse_sheet:
            pulse_sheet_viewer.show_pulse_sheet(file_path+'timing_diagram', compiled_exp)
            output_sim = OutputSimulator(compiled_exp)
            max_time = kwargs.get('raw_pulse_sheet_duration', output_sim.max_output_length)
            #
            #Get all pulses/signals from the experiment
            dict_data = {}
            for cur_qubit in leQubits:
                cur_signals = cur_qubit.signals
                for cur_signal in cur_signals:
                    cur_logical_signal = cur_signals[cur_signal]
                    cur_phys_channel_uid = leACQ._instr_zi.device_setup.logical_signal_by_uid(cur_logical_signal).physical_channel
                    #
                    cur_name = cur_logical_signal 
                    if hasattr(cur_phys_channel_uid, 'calibration'):
                        if hasattr(cur_phys_channel_uid.calibration, 'local_oscillator'):
                            if hasattr(cur_phys_channel_uid.calibration.local_oscillator, 'frequency'):
                                cur_freq = cur_phys_channel_uid.calibration.local_oscillator.frequency
                                if cur_freq > 0:
                                    cur_name += f' (LO={Miscellaneous.get_units(cur_freq)}Hz)'
                    dict_data[cur_name] = output_sim.get_snippet(cur_phys_channel_uid, 0, max_time)
            #
            #Use Bokeh to plot it in a nice HTML format (ctrl for x-zoom)
            # Build channel dict
            channels = {}
            for cur_ch in dict_data:
                ch = {'time': dict_data[cur_ch].time}
                if dict_data[cur_ch].wave.dtype == np.dtype('complex128'):
                    ch['real'] = np.real(dict_data[cur_ch].wave)
                    ch['imag'] = np.imag(dict_data[cur_ch].wave)
                else:
                    ch['value'] = dict_data[cur_ch].wave
                channels[cur_ch] = ch
            plots = []
            for name, data in channels.items():
                plot_kwargs = {}
                if plots:
                    plot_kwargs['x_range'] = plots[0].x_range
                #
                wheel_zoom = WheelZoomTool(dimensions="width")
                wheel_zoom.modifiers = {"ctrl": True}
                p = figure(
                    title=name, x_axis_label="Time (s)", y_axis_label="Value",
                    tools="",
                    active_scroll=wheel_zoom,
                    sizing_mode="stretch_width", height=200,
                    **plot_kwargs)
                p.add_tools(
                    PanTool(dimensions="width"),
                    wheel_zoom,
                    BoxZoomTool(dimensions="width"),
                    ResetTool())
                if 'value' in data:
                    source = ColumnDataSource({'time': data['time'], 'value': data['value']})
                    p.line(x="time", y="value", source=source,
                        line_width=2, color='black', legend_label="value")
                else:
                    source_real = ColumnDataSource({'time': data['time'], 'real': data['real']})
                    source_imag = ColumnDataSource({'time': data['time'], 'imag': data['imag']})
                    p.line(x="time", y="real", source=source_real,
                        line_width=2, color='red', legend_label="real")
                    p.line(x="time", y="imag", source=source_imag,
                        line_width=2, color='blue', legend_label="imag")
                p.legend.click_policy = "hide"
                plots.append(p)
            grid = gridplot([[p] for p in plots],
                            sizing_mode="stretch_width",
                            merge_tools=True)
            html = file_html(grid, CDN, "Channels")
            html = html.replace("height: 100%;", "min-height: 100%;")
            html = html.replace("display: flow-root;", "")
            with open(file_path+'timing_diagram_raw.html', "w") as f:
                f.write(html)

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
        
        if kwargs.pop('debug_skip_experiment', False):
            print('Not running experiment')
            return

        kwargs['skip_init_instruments'] = True

        leData = super()._run(file_path, sweep_vars, **kwargs)

        # folder_store.deactivate()
        # logging_store.deactivate()
        
        return leData

    def _post_process(self, data):
        pass
