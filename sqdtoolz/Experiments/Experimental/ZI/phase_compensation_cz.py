"""This module applies a Z rotation to compensate for accumulated phase in  
    qb --- [ h ] --- [ cz ] --- [ z (angle) ] --- [ h ] --- [ meas z ]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import laboneq.simple as lbeqs
from laboneq.core.types.enums import section_timing_mode

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
import numpy as np

@workflow.workflow(name="phase_compensation_cz")
def experiment_workflow(
    session: Session,
    qpu: QPU,
    qubits: QuantumElements | list[str] | str,
    rz_angles: QubitSweepPoints,
    coupler_name: str = None,
    main_or_aux: str = "main",
    temporary_parameters: dict[str | tuple[str, str, str], dict | QuantumParameters]
    | None = None,
    options: TuneUpWorkflowOptions | None = None,
) -> None:
    """The phase_compensation_cz Workflow.

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
        rz_angles:
            Array of angles to sweep in the Rz(theta) compensation pulse.
        main_or_aux:
            Choose whether to apply the compensation Rz gate to the coupler's
            'main', 'aux', or 'stationary' qubit, which are detected according
            to the signals on the coupler
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
        rz_angles,
        coupler_name,
        main_or_aux
    )
    compiled_exp = compile_experiment(session, exp)
    result = run_experiment(session, compiled_exp)
    workflow.return_(result)


@workflow.task
@dsl.qubit_experiment
def create_experiment(
    qpu: QPU,
    qubits: QuantumElements,
    rz_angles: QubitSweepPoints,
    coupler_name: str = None,
    main_or_aux: str = 'main',
    options: TuneupExperimentOptions | None = None,
) -> Experiment:
    """Creates a CZ phase compensation experiment. 

    Arguments:
        qpu:
            The qpu consisting of the original qubits and quantum operations.
        qubits:
            The qubits to run the experiments on. May be either a single
            qubit or a list of qubits.
        rz_angles:
            Array of angles to sweep in the Rz(theta) compensation pulse.
        main_or_aux:
            Choose whether to apply the compensation Rz gate to the coupler's
            'main', 'aux', or 'stationary' qubit, which are detected according
            to the signals on the coupler.
        coupler_name:
            Name of the coupler (str) to target with the CZ.
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

    assert main_or_aux.lower() in ['main', 'aux', 'stationary'], "Supply 'main_or_aux' as either 'main', 'stationary' or 'aux'."

    # find the coupler (if not supplied)
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

    # asserts
    if (the_coupler.parameters.AmplitudeAux != 0) and (the_coupler.parameters.AmplitudeAux is not None):
        assert the_coupler.signals['drive_comp_aux'] is not None, "Must assign a 'drive_comp_aux' signal in the coupler to apply phase compensation to the auxilliary qubit."
        assert the_coupler.signals['flux_aux'] is not None, "Must assign a 'flux_aux' signal in the coupler to apply AmplitudeAux."
    assert the_coupler.signals['drive_comp'] is not None, "Must assign a 'drive_comp' signal in the coupler to apply phase compensation to the main detuned qubit."
    assert the_coupler.signals['drive_comp_stationary'] is not None, "Must assign a 'drive_comp_stationary' signal in the coupler to apply phase compensation to the stationary qubit."

    # find the compensation qubit
    for q in qubits:
        if main_or_aux.lower() == 'main':
            if q.uid in the_coupler.signals['flux']:
                q_comp = q
        elif main_or_aux.lower() == 'stationary':
            if q.uid in the_coupler.signals['drive_comp_stationary']:
                q_comp = q
        else:
            if q.uid in the_coupler.signals['flux_aux']:
                q_comp = q

    # create sweep parameter for rz
    zangle_sweep_pars = SweepParameter(f"rz_angle", rz_angles, axis_name=f"rz_angle")

    # calculate_lengths
    l_flux = the_coupler.parameters.Length + q_comp.parameters.ge_drive_length

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
        # reset to g
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

        # sweep over rz angles
        with dsl.sweep(name="rz_angle_sweep", parameter=zangle_sweep_pars):
            if main_or_aux.lower() == 'aux':
                with dsl.section(name="pre_drive_and_cz", alignment=SectionAlignment.LEFT):
                    with dsl.section(name="pre_drive", alignment=SectionAlignment.LEFT, length=l_flux):
                        # [ h ]
                        qop.rz.omit_section(q_comp, angle=np.pi)
                        qop.ry.omit_section(q_comp, angle=np.pi/2)

                    with dsl.section(name="flux_pulse", alignment=SectionAlignment.RIGHT, length=l_flux):
                        # [ cz ]
                        qop.CZ.omit_section(the_coupler)
            else:
                with dsl.section(name="pre_drive_and_cz", alignment=SectionAlignment.LEFT):
                    with dsl.section(name="pre_drive", alignment=SectionAlignment.LEFT, length=l_flux):
                        # [ h ]
                        qop.rz.omit_section(q_comp, angle=np.pi)
                        qop.ry.omit_section(q_comp, angle=np.pi/2)

                    with dsl.section(name="flux_pulse", alignment=SectionAlignment.RIGHT, length=l_flux):
                        # [ cz ]
                        qop.CZ.omit_section(the_coupler)

            with dsl.section(name="main_phase_comp", alignment=SectionAlignment.RIGHT):
                # [ rz(theta) ]
                qop.rz.omit_section(q_comp, angle=zangle_sweep_pars)

            with dsl.section(name="post_drive", alignment=SectionAlignment.LEFT):
                # [ h ]
                qop.rz.omit_section(q_comp, angle=np.pi)
                qop.ry.omit_section(q_comp, angle=np.pi/2)

            with dsl.section(name="main_measure", alignment=SectionAlignment.LEFT):
                sec = qop.measure(q_comp, dsl.handles.result_handle(q_comp.uid))
                # Fix the length of the measure section
                sec.length = max_measure_section_length

                # reset all qubits
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

        for q in qubits:
            if opts.use_cal_traces:
                qop.calibration_traces.omit_section(
                    qubits=[q],
                    states=opts.cal_states,
                    active_reset=opts.active_reset,
                    active_reset_states=opts.active_reset_states,
                    active_reset_repetitions=opts.active_reset_repetitions,
                    measure_section_length=max_measure_section_length,
                )