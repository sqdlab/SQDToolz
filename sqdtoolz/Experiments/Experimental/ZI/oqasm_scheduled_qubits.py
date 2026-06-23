# Copyright 2024 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0

"""This module defines the amplitude-rabi experiment.

In this experiment, we sweep the amplitude of a drive pulse on a given qubit transition
in order to determine the pulse amplitude that induces a rotation of pi.

The amplitude-rabi experiment has the following pulse sequence:

    qb --- [ prep transition ] --- [ x180_transition ] --- [ measure ]

If multiple qubits are passed to the `run` workflow, the above pulses are applied
in parallel on all the qubits.
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


import numpy as np

@workflow.workflow(name="oqasm_scheduled_qubits")
def experiment_workflow(
    session: Session,
    qpu: QPU,
    qubits: QuantumElements | list[str] | str,
    openqasm_schedule,
    coordinate_system: str = 'RH',
    # TODO: Update the type hint for the temporary_parameters argument when the new
    # qubit class is available. Same for other experiment workflows.
    temporary_parameters: dict[str | tuple[str, str, str], dict | QuantumParameters]
    | None = None,
    options: TuneUpWorkflowOptions | None = None,
) -> None:
    """The Amplitude Rabi Workflow.

    The workflow consists of the following steps:

    - [create_experiment]()
    - [compile_experiment]()
    - [run_experiment]()
    - [analysis_workflow]()
    - [update_qpu]()

    !!! version-changed "Deprecated in version 26.1.0."
        The `qubits` argument of type `QuantumElements` is deprecated.
        Please pass `qubits` of type `list[str] | str` instead, i.e., the quantum
        element UIDs instead of the quantum element instances.

    Arguments:
        session:
            The connected session to use for running the experiment.
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on, passed by UID. May be either a single
            qubit or a list of qubits.
        openqasm_schedule:
            The openqasm3-based schedule given by ParseOpenQASM.create_schedule
        coordinate_system:
            Coordinate system to use for x, y and z axes - either LH or RH for left/right handed.
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
        ```
    """
    temp_qpu = temporary_qpu(qpu, temporary_parameters)
    qubits = temporary_quantum_elements_from_qpu(temp_qpu, qubits)

    exp = create_experiment(
        temp_qpu,
        qubits,
        openqasm_schedule,
        coordinate_system
        # quarter_time=quarter_time,
    )
    compiled_exp = compile_experiment(session, exp)
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
    openqasm_schedule,
    coordinate_system: str = 'RH',
    options: TuneupExperimentOptions | None = None,
) -> Experiment:
    """Creates an Amplitude Rabi experiment Workflow.

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on. May be either a single
            qubit or a list of qubits.
        openqasm_schedule:
            The openqasm3-based schedule given by ParseOpenQASM.create_schedule
        coordinate_system:
            Coordinate system to use for x, y and z axes - either LH or RH for left/right handed.
        options:
            The options for building the experiment.
            See [TuneupExperimentOptions] and [BaseExperimentOptions] for
            accepted options.
            Overwrites the options from [TuneupExperimentOptions] and
            [BaseExperimentOptions].

    Returns:
        experiment:
            The generated LabOne Q experiment instance to be compiled and executed.
            NOTE: The experiment will initialise the qubits and then right-align the
            list of respective gates such that measurements are done simultaneously
            and  immediately after the execution of said list of gates.

    Raises:
        ValueError:
            If the experiment uses calibration traces and the averaging mode is
            sequential.
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

    # We will fix the length of the measure section to the longest section among
    # the qubits to allow the qubits to have different readout and/or
    # integration lengths.
    max_measure_section_length = qpu.measure_section_length(qubits)
    qop = qpu.quantum_operations
    with dsl.acquire_loop_rt(
        count=opts.count,
        averaging_mode=opts.averaging_mode,
        acquisition_type=opts.acquisition_type,
        repetition_mode=opts.repetition_mode,
        repetition_time=opts.repetition_time,
        reset_oscillator_phase=opts.reset_oscillator_phase,
    ):
        ###################
        with dsl.section(name="init"):
            init_section_uid = dsl.active_section().uid
            if opts.active_reset:
                qop.active_reset(
                    qubits,
                    active_reset_states=opts.active_reset_states,
                    number_resets=opts.active_reset_repetitions,
                    measure_section_length=max_measure_section_length,
                )
            else:
                for q in qubits:
                    qop.passive_reset(q)
        ###################
        le_UIDs = []
        with dsl.section(name="Main", play_after=init_section_uid):
            for m,cur_section in enumerate(openqasm_schedule['commands']):
                if cur_section['after'] != None:
                    after = le_UIDs[cur_section['after']]
                else:
                    after = None
                with dsl.section(name=f"sec{m}", alignment=SectionAlignment.LEFT, play_after=after):
                    current_section_uid = dsl.active_section().uid
                    le_UIDs.append(current_section_uid)

                    if isinstance(cur_section['qubit_index'], (list,tuple)):
                        pass
                    else:
                        #Process Single-Qubit operations
                        cur_qubit = qubits[cur_section['qubit_index']]
                        for cur_gate in cur_section['sequence']:
                            if cur_gate[0] == 'X' or cur_gate[0] == 'Y':
                                if (np.abs(cur_gate[1]-np.pi/2) < 1e-7):
                                    ampl = params['amplitude_pi2']
                                elif (np.abs(cur_gate[1]+np.pi/2) < 1e-7):
                                    ampl = -params['amplitude_pi2']
                                else:
                                    ampl = None
                            if cur_gate[0] == 'X':
                                qop.rx(cur_qubit, cur_gate[1], amplitude=ampl)
                            elif cur_gate[0] == 'Y':
                                qop.rx(cur_qubit, cur_gate[1], amplitude=ampl)
                            elif cur_gate[0] == 'Z':
                                if coordinate_system == 'RH':
                                    qop.rz(cur_qubit, -cur_gate[1])
                                else:
                                    qop.rz(cur_qubit, cur_gate[1])
                            elif cur_gate[0] == 'D':
                                if cur_gate[1] > 0:
                                    qop.delay(cur_qubit, cur_gate[1])
                            elif cur_gate[0] == 'Measure':
                                qop.measure(cur_qubit, dsl.handles.result_handle(cur_qubit.uid))
                pass

        for q in qubits:
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
