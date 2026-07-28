"""This module defines the amplitude-rabi experiment.

In this experiment we measure the flux pulse distortion on a qubit utilisng the flux scope protocol

The fluxscope experiment has the following pulse sequence:

    qb --- [ prep transition ] --- [flux pulse] --- [delay] --- [ x180_transition ] --- [ measure ]
    
If multiple qubits are passed to the `run` workflow, the above pulses are applied
in parallel on all the qubits.

Qubit must be prepared in a flux sensitive area e.g. away from sweet spot
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import laboneq.simple as lbeqs

from laboneq import workflow
from laboneq.simple import (
    AveragingMode,
    Experiment,
    SectionAlignment,
    SweepParameter,
    dsl,
)
from laboneq.workflow.tasks import (
    compile_experiment,
    run_experiment,
)

from laboneq_applications.analysis.amplitude_rabi import analysis_workflow
from laboneq_applications.core import validation
from laboneq_applications.experiments.options import (
    TuneupExperimentOptions,
    TuneUpWorkflowOptions,
)
from laboneq_applications.tasks import (
    temporary_qpu,
    temporary_quantum_elements_from_qpu,
    update_qpu,
)
from laboneq.pulse_sheet_viewer import pulse_sheet_viewer

if TYPE_CHECKING:
    from laboneq.dsl.quantum import QuantumParameters
    from laboneq.dsl.quantum.qpu import QPU
    from laboneq.dsl.session import Session

    from laboneq_applications.typing import QuantumElements, QubitSweepPoints

from sqdtoolz.HAL.ZI.QuantumElements.TunableTransmonCouplerFixed import TunableTransmonCouplerFixed

@workflow.workflow(name="fluxscope")
def experiment_workflow(
    session: Session,
    qpu: QPU,
    qubits: QuantumElements | list[str] | str,
    delays: QubitSweepPoints,
    frequencies: QubitSweepPoints,
    temporary_parameters: dict[str | tuple[str, str, str], dict | QuantumParameters]
    | None = None,
    options: TuneUpWorkflowOptions | None = None,
) -> None:
    """The fluxscope Workflow.

    The workflow consists of the following steps:

    - [create_experiment]()
    - [compile_experiment]()
    - [run_experiment]()
    - [analysis_workflow]()
    - [update_qpu]()

    Arguments:
        session:
            The connected session to use for running the experiment.
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on, passed by UID. May be either a single
            qubit or a list of qubits.
        delays:
            delays (in seconds) In between start of flux pulse and x180 excitation
        frequencies:
            the frequencies (Hz) scanned by the qubit charge drive excitation pulse in order to find the qubit after
            during flux pulse
        temporary_parameters:
            The temporary parameters with which to update the quantum elements and
            topology edges. For quantum elements, the dictionary key is the quantum
            element UID. For topology edges, the dictionary key is the edge tuple
            `(tag, source node UID, target node UID)`.
        options:
            The options for building the workflow.
            In addition to options from [WorkflowOptions], the following
            custom options are supported:
                - create_experiment: The options for creating the experiment.

    Returns:
        WorkflowBuilder:
            The builder of the experiment workflow.

    Example:
        ```python
        options = TuneUpExperimentWorkflowOptions()
        options.create_experiment.count = 10
        options.create_experiment.transition = "ge"
        qpu = QPU(
            quantum_elements=[TunableTransmonQubit("q0"), TunableTransmonQubit("q1")],
            quantum_operations=TunableTransmonOperations(),
        )
        temp_qubits = qpu.copy_quantum_elements()
        result = experiment_workflow(
            session=session,
            qpu=qpu,
            qubits=temp_qubits,
            amplitudes=[
                np.linspace(0, 1, 11),
                np.linspace(0, 0.75, 11),
            ],
            options=options,
        ).run()
        ```
    """
    temp_qpu = temporary_qpu(qpu, temporary_parameters)
    qubits = temporary_quantum_elements_from_qpu(temp_qpu, qubits)

    dsl = create_experiment(
        temp_qpu,
        qubits,
        delays,
        frequencies,
    )
    compiled_exp = compile_experiment(session, dsl)
    result = run_experiment(session, compiled_exp)
    # with workflow.if_(options.do_analysis):
    #     analysis_results = analysis_workflow(result, qubits, amplitudes)
    #     qubit_parameters = analysis_results.output
    #     with workflow.if_(options.update):
    #         update_qpu(qpu, qubit_parameters["new_parameter_values"])
    workflow.return_(result)


@workflow.task
@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    delays: QubitSweepPoints,
    frequencies: QubitSweepPoints,
    amplitude_aux: float=None,
    coupler_name:str = None,
    options: TuneupExperimentOptions | None = None,
) -> Experiment:
    """Creates an Amplitude Rabi experiment Workflow.

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on. May be either a single
            qubit or a list of qubits.
        delays:
            delays (in seconds) In between start of flux pulse and x180 excitation
        frequencies:
            the frequencies (Hz) scanned by the qubit charge drive excitation pulse in order to find the qubit after
            during flux pulse
        options:
            The options for building the experiment.
            See [TuneupExperimentOptions] and [BaseExperimentOptions] for
            accepted options.
            Overwrites the options from [TuneupExperimentOptions] and
            [BaseExperimentOptions].

    Returns:
        experiment:
            The generated LabOne Q experiment instance to be compiled and executed.

    Raises:
        ValueError:
            If the qubits and qubit_amplitudes are not of the same length.

        ValueError:
            If qubit_amplitudes is not a list of numbers when a single qubit is passed.

        ValueError:
            If qubit_amplitudes is not a list of lists of numbers.

        ValueError:
            If the experiment uses calibration traces and the averaging mode is
            sequential.

    Example:
        ```python
        options = {
            "count": 10,
            "transition": "ge",
            "averaging_mode": "cyclic",
            "acquisition_type": "integration_trigger",
            "cal_traces": True,
        }
        options = TuneupExperimentOptions(**options)
        qpu = QPU(
            quantum_elements=[TunableTransmonQubit("q0"), TunableTransmonQubit("q1")],
            quantum_operations=TunableTransmonOperations(),
        )
        temp_qubits = qpu.copy_quantum_elements()
        create_experiment(
            qpu=qpu,
            qubits=temp_qubits,
            amplitudes=[
                np.linspace(0, 1, 11),
                np.linspace(0, 0.75, 11),
            ],
            options=options,
        )
        ```
    """
    # Define the custom options for the experiment
    opts = TuneupExperimentOptions() if options is None else options
    if (
        opts.use_cal_traces
        and AveragingMode(opts.averaging_mode) == AveragingMode.SEQUENTIAL
    ):
        raise ValueError(
            "'AveragingMode.SEQUENTIAL' (or {AveragingMode.SEQUENTIAL}) cannot be used "
            "with calibration traces because the calibration traces are added "
            "outside the sweep."
        )
    if coupler_name == None:
        cpl_cands = qpu.topology[:, qubits[0], qubits[1]] + qpu.topology[:, qubits[1], qubits[0]]
        the_coupler = None
        for cur_cpl in cpl_cands:
            cur_qelem = cur_cpl.quantum_element
            if isinstance(cur_qelem, TunableTransmonCouplerFixed):
                the_coupler = cur_qelem
        assert the_coupler != None, f"Could not find a suitable \'TunableTransmonCouplerFixed\' coupler for qubits \'{qubits[0]}\' and \'{qubits[1]}\'. Maybe provide coupler_name explicitly."
    else:
        the_coupler = qpu[coupler_name]
        assert isinstance(the_coupler, TunableTransmonCouplerFixed), f"The coupler \'{coupler_name}\' is not a \'TunableTransmonCouplerFixed\' type."

    sweep_frequency = SweepParameter(f"frequency", frequencies, axis_name=f"qubit_frequency")
    sweep_delay = SweepParameter(f"delay", delays, axis_name=f"flux_delay")

    # We will fix the length of the measure section to the longest section among
    # the qubits to allow the qubits to have different readout and/or
    # integration lengths.
    max_measure_section_length = qpu.measure_section_length(qubits)
    qop = qpu.quantum_operations

    with dsl.acquire_loop_rt(
        uid="shots",
        count=opts.count,
        averaging_mode=opts.averaging_mode, #CYCLIC
        acquisition_type=opts.acquisition_type, #INTEGRATION
    ):
        with dsl.sweep(uid="frequency_sweep", parameter=sweep_frequency):
            # inner sweep - delay between start of qubit excitation pulse and start of flux pulse
            with dsl.sweep(uid="sweep", parameter=sweep_delay):
                qop.set_frequency(qubits[0], sweep_frequency)
                if opts.active_reset:
                    qop.active_reset(
                        qubits,
                        active_reset_states=opts.active_reset_states,
                        number_resets=opts.active_reset_repetitions,
                        measure_section_length=max_measure_section_length,
                    )
                # flux pulse
                with dsl.section(uid="qubit_excitation"):
                    qop.CZ.omit_section(the_coupler)
                    qop.delay.omit_section(qubits[0], time=sweep_delay)  # delay is swept
                    qop.x180.omit_section(qubits[0])
                # readout and data acquisition
                with dsl.section(name="main_measure"):
                    for q in qubits:
                        sec = qop.measure(q, dsl.handles.result_handle(q.uid))
                        # Fix the length of the measure section
                        sec.length = max_measure_section_length
                        qop.passive_reset(q)

            if opts.use_cal_traces:
                qop.calibration_traces.omit_section(
                    qubits=qubits,
                    states=opts.cal_states,
                    active_reset=opts.active_reset,
                    active_reset_states=opts.active_reset_states,
                    active_reset_repetitions=opts.active_reset_repetitions,
                    measure_section_length=max_measure_section_length,
                )

#Delays and frequencies need to specified at run time. Some knowledge about CZ pulse gate parameters will be required
#By default the fluxscope utilises the amplitude and time parameters by the CZ dsl pulse that lives in TunableTransmonCouplerFixed,
#This should probably re re-done so that you can perform flux_scope on an arbitrary single qubit. i.e. no couplers called here
#Alternativley we could extract the exact required delay time from TunableTransmonCouplerFixed ? 

#Tested in simulation mode with ZI_test_fluxscope.py