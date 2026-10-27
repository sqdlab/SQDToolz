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
from laboneq.core.types.enums import section_timing_mode

import laboneq
from laboneq import workflow
from laboneq.simple import (
    AveragingMode,
    Experiment,
    SectionAlignment,
    SweepParameter,
    dsl,
    Calibration, Oscillator, SignalCalibration
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
    avail_aux_lines:dict = {},
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
        coordinate_system,
        avail_aux_lines
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
    avail_aux_lines:dict = {},
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

    #Process custom pulses (if any)
    #For readout pulses, there is a restriction on the SHFQC that it can only be of one shape throughout the entire experiment run.
    #Thus, track and ensure that only one is used.
    #And it turns out to be in vain... It'll be kept here in case it changes in the future...
    readout_pulses = {}
    #Strategy is to scale the amplitudes of the pulses as required. However, ZI caps amplitudes in [0,1]. So cache and adjust accordingly in end...
    readout_cache = []
    lePulses = {}
    for cur_section in openqasm_schedule['commands']:
        if cur_section['custom_waveform']:
            for cur_pulse in cur_section['sequence']:
                if cur_pulse['type'] == 'play':
                    new_uid = f'uid_pulse_{len(lePulses)}'
                    if 'delay' in cur_pulse:
                        continue
                    match cur_pulse['waveform_var']['type']:
                        case "gaussian":
                            new_pulse = lbeqs.pulse_library.gaussian(
                                uid=new_uid,
                                length=cur_pulse['waveform_var']['length'],
                                amplitude=cur_pulse['waveform_var']['amplitude'],
                                sigma=cur_pulse['waveform_var'].get('sigma', 0.25)
                            )
                        case "constant":
                            new_pulse = lbeqs.pulse_library.const(
                                uid=new_uid,
                                length=cur_pulse['waveform_var']['length'],
                                amplitude=cur_pulse['waveform_var']['amplitude']
                            )
                        #####
                        case "sampled":
                            if cur_pulse['waveform_var']['samples'].dtype == np.complex128:
                                new_pulse = lbeqs.pulse_library.sampled_pulse_complex(uid=new_uid, samples=cur_pulse['waveform_var']['samples'])
                            else:
                                new_pulse = lbeqs.pulse_library.sampled_pulse_real(uid=new_uid, samples=cur_pulse['waveform_var']['samples'])
                    found = False
                    cur_pulse['zi_pulse_params'] = {}
                    if not cur_pulse['frame_var'].line_id in ['aux', 'measure']:  #Measure pulses must each have their own pulse object...
                        for cur_cached_pulse in lePulses:
                            new_pulse.uid = lePulses[cur_cached_pulse].uid  #This is just to make the comparison == work...
                            if lePulses[cur_cached_pulse] == new_pulse:
                                found = True
                                new_uid = cur_cached_pulse
                                break
                    else:
                        cur_qind = cur_pulse['frame_var'].qubit_id
                        if cur_qind in readout_pulses:
                            #Check if it's matching constant/gaussian etc.
                            if cur_pulse['waveform_var']['type'] != 'sampled':
                                assert readout_pulses[cur_qind].function == cur_pulse['waveform_var']['type'], f"Cannot change the pulse shape (from {readout_pulses[cur_qind].function} to {cur_pulse['waveform_var']['type']}) of readout during an experiment run for a given readout channel (qubit ${cur_qind})."
                                assert readout_pulses[cur_qind].length == cur_pulse['waveform_var']['length'], f"Cannot change the pulse length (from {readout_pulses[cur_qind].length} to {cur_pulse['waveform_var']['length']}) of readout during an experiment run for a given readout channel (qubit ${cur_qind})."
                                assert readout_pulses[cur_qind].amplitude == cur_pulse['waveform_var']['amplitude'], f"For now, one cannot change the pulse amplitude (from {readout_pulses[cur_qind].amplitude} to {cur_pulse['waveform_var']['amplitude']}) of readout during an experiment run for a given readout channel (qubit ${cur_qind})."
                                # cur_pulse['zi_pulse_params']['amplitude'] = cur_pulse['waveform_var']['amplitude']
                            else:
                                cur_ratios = cur_pulse['waveform_var']['samples'] / readout_pulses[cur_qind].samples
                                assert np.nanmax(cur_ratios)-np.nanmin(cur_ratios) < 1e-12, f"Cannot change the pulse shape of readout during an experiment run for a given readout channel (qubit ${cur_qind})."
                                assert np.nanmax(cur_ratios) >= 0, f"Cannot scale the pulse shape by a negative amplitude for a given readout channel (qubit ${cur_qind})."
                                assert np.nanmax(cur_ratios) == 1.0, f"For now, even the amplitudes must remain constant over multiple measurement pulses for a given readout channel (qubit ${cur_qind})."
                                cur_pulse['zi_pulse_params']['amplitude'] = np.nanmax(cur_ratios)
                                readout_cache.append(cur_pulse)
                            found = True
                            new_uid = readout_pulses[cur_qind].uid
                        else:
                            if cur_pulse['waveform_var']['type'] == 'sampled':
                                cur_pulse['zi_pulse_params']['amplitude'] = 1.0
                            readout_pulses[cur_qind] = new_pulse
                    if not found:
                        new_pulse.uid = new_uid
                        lePulses[new_uid] = new_pulse
                    cur_pulse['zi_pulse'] = lePulses[new_uid]
            pass
    #Only uncomment this block if multiple pulses with different amplitudes on the same readout line is ever allowed...
    # max_ampls = [0]*len(qubits)
    # for cur_cached_pulse in readout_cache:
    #     cur_qind = cur_cached_pulse['frame_var'].qubit_id
    #     max_ampls[cur_qind] = max(max_ampls[cur_qind], cur_cached_pulse['zi_pulse_params']['amplitude'])
    # for cur_cached_pulse in readout_cache:
    #     cur_qind = cur_cached_pulse['frame_var'].qubit_id
    #     cur_cached_pulse['zi_pulse_params']['amplitude'] /= max_ampls[cur_qind]
    for m in range(len(qubits)):
        if not m in readout_pulses:
            readout_pulses[m] = qubits[m].parameters.readout_pulse
        #Only uncomment this block if multiple pulses with different amplitudes on the same readout line is ever allowed...
        # else:
        #     if isinstance(readout_pulses[m], laboneq.dsl.experiment.pulse.PulseSampled):
        #         readout_pulses[m].samples = readout_pulses[m].samples / max_ampls[m]
    #
    #So now collate all non-qubit reserved readout pulses and look into adding the logical signal mapping to the SHFQC...
    calib = dsl.experiment_calibration()
    for cur_id in readout_pulses:
        if not isinstance(cur_id, str):
            continue    #It's a qubit reservation
        assert cur_id in avail_aux_lines, f"The auxiliary readout line {cur_id} (feedline and tone reservation) is not available in this hardware setup/arrangement. Available ones are: {[x for x in avail_aux_lines]}."
        dsl.add_signal(f"{cur_id}_measure", connect_to=f"/logical_signal_groups/{avail_aux_lines[cur_id]}/measure")
        dsl.add_signal(f"{cur_id}_acquire", connect_to=f"/logical_signal_groups/{avail_aux_lines[cur_id]}/acquire")
        calib[f"{cur_id}_measure"] = SignalCalibration(oscillator=Oscillator(uid=f"{cur_id}_osc", frequency=0.01e9))
        calib[f"{cur_id}_acquire"] = SignalCalibration(oscillator=Oscillator(uid=f"{cur_id}_osc", frequency=0.01e9))

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
                with dsl.section(name=f"sec{m}", alignment=SectionAlignment.LEFT, play_after=after, section_timing_mode=section_timing_mode.SectionTimingMode.STRICT):
                    current_section_uid = dsl.active_section().uid
                    le_UIDs.append(current_section_uid)
                    if cur_section['custom_waveform']:
                        for cur_pulse in cur_section['sequence']:
                            cur_signal_line = cur_pulse['frame_var']
                            if cur_signal_line.line_id == 'aux':
                                cur_signal_line = f'{cur_signal_line.qubit_id}_measure'
                            else:
                                cur_signal_line = f'{qubits[cur_signal_line.qubit_id].uid}/{cur_signal_line.line_id}'
                            if cur_pulse['type'] == 'play':
                                if 'delay' in cur_pulse:
                                    dsl.delay(signal=cur_signal_line, time=cur_pulse['delay'])
                                else:
                                    dsl.play(signal=cur_signal_line, pulse=cur_pulse['zi_pulse'], **cur_pulse['zi_pulse_params'])
                            elif cur_pulse['type'] == 'pulse_attribute':
                                if 'set_phase_val' in cur_pulse:
                                    dsl.play(signal=cur_signal_line,pulse=None, set_oscillator_phase=cur_pulse['set_phase_val'])
                                elif 'shift_phase_val' in cur_pulse:
                                    dsl.play(signal=cur_signal_line,pulse=None, increment_oscillator_phase=cur_pulse['shift_phase_val'])
                                elif 'set_frequency_val' in cur_pulse:
                                    qop.set_frequency(qubits[cur_signal_line], cur_pulse['set_frequency_val'])
                    elif isinstance(cur_section['qubit_index'], (list,tuple)):
                        cur_qinds = [x for x in cur_section['qubit_index']]
                        cur_qubits = [qubits[x] for x in cur_qinds]
                        edges = [edge for edge in qpu.topology.edges() if {edge.source_node.uid, edge.target_node.uid}=={cur_qubits[0].uid, cur_qubits[1].uid}]
                        assert len(edges) == 1, "QPU with multiple couplers unsupported for now..."
                        # edges = [edge for edge in edges if isinstance(edge.quantum_element, TunableTransmonCouplerFixed)]
                        cur_coupler = edges[0].quantum_element
                        assert cur_section['sequence'][0] == 'ctrl', "Non ctrl-A 2QGs not supported for now..."
                        assert cur_section['sequence'][1][0] == 'Z', "Only CZ gates supported natively for now..."
                        assert np.abs(cur_section['sequence'][1][1]-np.pi) < 1e-7, "Only CZ gates supported natively for now..."
                        qop.CZ(cur_coupler)
                    else:
                        #Process Single-Qubit operations
                        cur_qubit = qubits[cur_section['qubit_index']]
                        for cur_gate in cur_section['sequence']:
                            if cur_gate[0] == 'X' or cur_gate[0] == 'Y':
                                if (np.abs(cur_gate[1]-np.pi/2) < 1e-7):
                                    ampl = cur_qubit.parameters.ge_drive_amplitude_pi2
                                elif (np.abs(cur_gate[1]+np.pi/2) < 1e-7):
                                    ampl = -cur_qubit.parameters.ge_drive_amplitude_pi2
                                else:
                                    ampl = None
                            if cur_gate[0] == 'X':
                                qop.rx(cur_qubit, cur_gate[1], amplitude=ampl)
                            elif cur_gate[0] == 'Y':
                                qop.ry(cur_qubit, cur_gate[1], amplitude=ampl)
                            elif cur_gate[0] == 'Z':
                                if coordinate_system == 'RH':
                                    qop.rz(cur_qubit, -cur_gate[1])
                                else:
                                    qop.rz(cur_qubit, cur_gate[1])
                            elif cur_gate[0] == 'D':
                                if cur_gate[1] > 0:
                                    qop.delay(cur_qubit, cur_gate[1])
                            elif cur_gate[0] == 'Measure':
                                qop.measure(cur_qubit, dsl.handles.result_handle(cur_gate[1]))
                            elif cur_gate[0] == 'Reset':
                                qop.passive_reset(cur_qubit)
                pass

        # for q in qubits:
        #     qop.passive_reset(q)
        # if opts.use_cal_traces:
        #     qop.calibration_traces.omit_section(
        #         qubits=qubits,
        #         states=opts.cal_states,
        #         active_reset=opts.active_reset,
        #         active_reset_states=opts.active_reset_states,
        #         active_reset_repetitions=opts.active_reset_repetitions,
        #         measure_section_length=max_measure_section_length,
        #     )
