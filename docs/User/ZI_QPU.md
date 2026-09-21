# Setting up ZI QPU objects

In the ZI workflow, we begin by defining a QPU object, to which we add qubits (`ZI.ZIQubit`) and couplers (`ZI.ZIQuantumElement`).

```python
import sqdtoolz as stz

lab = stz.Laboratory(instr_config_file = "NQCT-02.yaml", save_dir = "/home/")
lab.load_instrument('zi_boxes')

# Define qubits and signal channels
stz.ZI.ZIQubit('Q0', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', "SIGOUTS/0"))
stz.ZI.ZIQubit('Q1', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', "SIGOUTS/1"))

# Define coupler between Q0 and Q1 (Q1 is flux-pulsed, Q0 is the stationary qubit)
ZIQuantumElement('C01', lab, TunableTransmonCouplerFixed,
    flux='Q1/flux', drive_comp='Q1/drive', drive_comp_stationary='Q0/drive')

# Define QPU
stz.SOFTqpu('QPU', lab)

# Add qubits and coupler to the QPU
lab.HAL('QPU').add_qubit(lab.HAL('Q0'))
lab.HAL('QPU').add_qubit(lab.HAL('Q1'))
lab.HAL('QPU').add_qubit_coupling('Q0', 'Q1', lab.HAL('C01'))

# Initialise ZI acquisition object
stz.ZI.ZIACQ('ZIacq', lab, 'zi_boxes')

# Setup a variable for ReadoutAmplitude of Q0
stz.VariableProperty(f'resAmp_Q0', lab, lab.HAL('Q0'), 'ReadoutAmplitude')
lab.VAR('resAmp_Q0').Value = 0.1
```

In the above code snippet, we initialised our `Laboratory` object, added two `ZIQubit` objects `Q0` and `Q1` to our `SOFTqpu`, as well as a `ZIQuantumElement` defining a coupler between them, and initialised our ZI acquisition. We also setup a `VariableProperty` (which can be used for experiment sweeps) for the `ReadoutAmplitude` of `Q0` (which is an attribute of the `ZIQubit` object), and set it to 0.1.

Given a QPU with couplers already added, `lab.HAL('QPU').get_coupler_obj_from_qubits('Q0', 'Q1', TunableTransmonCouplerFixed)` returns the coupler HAL object of the given type connecting two qubits (asserting if none is found) — useful in scripts that need to look up a coupler without already knowing its HAL name.

### Signals

Both `ZIQubit` and `ZIQuantumElement` (coupler) objects are wired up in terms of **signals** — named logical lines (`drive`, `measure`, `acquire`, `flux`, etc.) that LabOne Q workflows play pulses onto or acquire from — but the two HAL types specify them differently.

**Qubits:** A `ZIQubit`'s signals are wired directly to physical instrument channels, via the four positional tuple arguments in its constructor — `zi_instr_phys_drive`, `zi_instr_phys_measure`, `zi_instr_phys_acquire`, and the optional `zi_phys_flux` (defaults to `("", "")`, i.e. no flux line). Each is a 2-tuple `(instrument_uid, port_string)`, e.g. `('shfqc0', 'SGCHANNELS/0/OUTPUT')`, where `instrument_uid` is the name given to that physical instrument in the loaded instrument config, and `port_string` is the ZI channel path on that instrument. From these, `ZIQubit` builds five logical signals internally: `drive` and `drive_ef` (both mapped to the same physical drive port — one qubit drive line is shared between the GE and EF transitions), `measure`, `acquire`, and (if a flux tuple with a non-empty instrument name is supplied) `flux`. These four physical-port tuples are stored as the `ZI_phys_drive`/`ZI_phys_measure`/`ZI_phys_acquire`/`ZI_phys_flux` attributes seen in the attribute dump below, and are used to (re)build the underlying LabOne Q device-setup connections whenever the qubit is instantiated or its saved config is reloaded.

**Couplers:** A `ZIQuantumElement`'s signals are logical signal *paths* of the form `'<QubitName>/<signal_type>'`, pointing at a signal already defined on one of the qubit HAL objects on the QPU (e.g. `'Q1/flux'`, `'Q1/drive'`) — there's no direct physical wiring at the coupler level. Which signal names are required or optional depends on the specific coupler class passed as the third constructor argument, via that class's `REQUIRED_SIGNALS`/`OPTIONAL_SIGNALS` attributes; every name in `REQUIRED_SIGNALS` must be supplied as a keyword argument, or the constructor asserts (`assert len(kwargs) == 0, "Do not supply arguments other than relevant signals..."` is really enforcing the reverse — that everything passed in is consumed as either a required or an optional signal). For `TunableTransmonCouplerFixed` specifically:
- `REQUIRED_SIGNALS = ("flux", "drive_comp", "drive_comp_stationary")` — `flux` is the flux line that actually gets pulsed for the two-qubit gate (physically the flux line of one of the two coupled qubits); `drive_comp` is that same (flux-pulsed) qubit's drive line, used to apply a compensating Z-rotation after the gate; `drive_comp_stationary` is the *other* (non-flux-pulsed) qubit's drive line, used for the equivalent compensation on that qubit.
- `OPTIONAL_SIGNALS = ("flux_aux", "drive_comp_aux")` — an auxiliary flux line (and its own compensation drive line), for cases where a secondary flux pulse is needed (e.g. to cancel crosstalk onto a neighbouring qubit/coupler).

The example at the top of this page reflects this: `C01` couples `Q0` and `Q1`, with `Q1`'s flux line doing the pulsing, so `flux='Q1/flux'` and `drive_comp='Q1/drive'` go together, while `drive_comp_stationary='Q0/drive'` covers the untouched qubit.

### Saving a QPU config
The current configuration of a QPU object (e.g. `stz.SOFTqpu('QPU', lab)`) can be saved by running `lab.HAL('QPU').save_config(lab)`. By default (`store_local=True`) this writes a file `QPU_config.json` to the current working directory — *not* the `lab`'s save directory. Pass `store_local=False` to instead write it into `lab`'s save directory (`lab._save_dir`), or `file_name=...` to use a different filename than `QPU_config.json`. An optional `additional_specs` list of `ExperimentSpecification` names can also be supplied to bundle their current configs into the same file.

A previously-saved config can be reloaded with the static method `SOFTqpu.load_config(lab, file_path=...)` (defaults to `'QPU_config.json'` in the current working directory if `file_path` is omitted), which instantiates/updates all qubits and couplers described in the file — or just one, via `SOFTqpu.load_config(lab, id='Q0', file_path=...)`.

Two other utility methods worth knowing about:
- `lab.HAL('QPU').print_summary_ZIQubits()`: prints a Markdown table summarising key parameters (frequencies, $T_1$/$T_2$, $Q$-factors, fidelities, etc.) across all qubits on the QPU.
- `SOFTqpu.create_summary_config_from_json(json_file_path, summary_output_json_file_path)` (static): reads a previously-saved `save_config` JSON file and writes out a smaller, flattened summary JSON (a curated subset of qubit/coupler parameters) — intended for consumption by an external dashboard rather than for reloading into SQDToolz.

### Viewing and setting qubit attributes
All attributes of the qubit (or coupler) objects can be viewed by `print(lab.HAL('Q0'))`, and set by `lab.HAL('Q0').FluxDC = 1`. These qubit attributes are updated as experiments are run on the qubit object. All attributes are:

```
Name: Q4
instrument: zi_boxes
Type: ZIQubit
ManualActivation: False
ZI_phys_drive: ['shfqc0', 'SGCHANNELS/0/OUTPUT']
ZI_phys_measure: ['shfqc0', 'QACHANNELS/0/OUTPUT']
ZI_phys_acquire: ['shfqc0', 'QACHANNELS/0/INPUT']
ZI_phys_flux: ['hdawg0', 'SIGOUTS/4']
ZI_qubit_type: TunableTransmonQubit
ChiGE: -46317.50540924072
DriveLO: 4000000000.0
DrivePower: -15
DriveGE: 4366659857.316082
DriveEF: 5100000000.0
DriveGEAmplitudeX: 0.311359981106039
DriveGEAmplitudeXon2: 0.1556799905530316
DriveGETime: 6e-08
DriveGEPulse: {'function': 'drag', 'beta': 0, 'sigma': 0.25}
DriveEFAmplitudeX: 0.2
DriveEFAmplitudeXon2: 0.1
DriveEFTime: 5e-08
DriveEFPulse: {'function': 'drag', 'beta': 0, 'sigma': 0.25}
ReadoutLO: 6000000000.0
ReadoutPower: 0
ReadoutInputRange: -20
ReadoutFrequency: 6296208015.848035
ReadoutAmplitude: 0.8
ReadoutKernelType: default
ReadoutKernelThresholds: None
ReadoutKernelWeights: None
ReadoutTime: 2e-06
ReadoutPad: 2e-08
ResetTime: 1e-05
IntegrationTime: 2e-06
T1GE: 7.015164194948346e-07
T2GE: 6.576253699184071e-07
T2GE_star: 0
T1EF: 0
T2EF: 0
T2EF_star: 0
FluxDC: -0.24
FluxRange: 1
QubitSpecAmplitude: 1
QubitSpecTime: 2e-05
ReadoutQi: 1825.1589041073546
ReadoutQc: 31059.628026145056
ReadoutQl: 1723.8596306071872
ReadoutKappa: 0
CorrectionMatrix: {}
ThermalPhotonNum: 0
ReadoutLineAttenuation_dB: -70
FluxConversionParams: None
QubitQiGE: 0
QubitQiEF: 0
Fidelity1QRB: 0.0
FidelityReadout: 0.0
```

`CorrectionMatrix` holds a readout-correction matrix (see [`ZI_DensityMatrix.md`](ZI_DensityMatrix.md)) once one has been measured/set; `FluxConversionParams` holds flux-to-frequency conversion parameters once calibrated (e.g. via a cryoscope or flux-sweep fit) and is `None` until then; `QubitQiGE`/`QubitQiEF` are the qubit's own internal quality factors (as distinct from `ReadoutQi`, which is the readout resonator's); and `Fidelity1QRB`/`FidelityReadout` are populated by randomised-benchmarking and readout-fidelity (blobs) experiments respectively.

### Coupler attributes

Coupler (`ZIQuantumElement`) attributes work the same way as qubit attributes — viewable with `print(lab.HAL('C01'))` and settable directly, e.g. `lab.HAL('C01').Amplitude = 0.4`. Every `ZIQuantumElement` has a `FidelityBell` attribute (default `None`), populated by `ExpZIBellStateFidelity` once a Bell-state fidelity measurement has been run on that coupler. The rest of the attributes come from the specific coupler class's own parameters (`PARAMETERS_TYPE`), so they vary by coupler type. For `TunableTransmonCouplerFixed`, these are:

```
Name: C01
Type: ZIQuantumElement
ManualActivation: False
FidelityBell: None
ZI_QuantumElement: TunableTransmonCouplerFixed
ZI_QuantumElementEx: {'flux': 'Q1/flux', 'drive_comp': 'Q1/drive', 'drive_comp_stationary': 'Q0/drive'}
Amplitude: 0.5
AmplitudeAux: 0.0
Length: 2.5e-07
Pulse: {'function': 'gaussian_square', 'sigma': 0.5, 'samples': None, 'precomp_kernel': None}
CompZAngle: None
CompZAngleAux: None
CompZAngleStationary: None
```

- `Amplitude`: Flux-pulse amplitude used for the two-qubit gate (`CZ` or `fixed_coupler_flux_pulse`). Defaults to `0.5`.
- `AmplitudeAux`: Amplitude of the auxiliary flux pulse played on the optional `flux_aux` signal (only has any effect if that signal was supplied at construction). Defaults to `0.0`.
- `Length`: Duration of the flux pulse. This is also what `get_gate_duration(('ctrl', 'Z'), qubits)` reports for scheduling purposes. Defaults to `250e-9`.
- `Pulse`: A dict describing the flux-pulse shape, in the same style as a qubit's `DriveGEPulse`/`DriveEFPulse`. Defaults to `{'function': 'gaussian_square', 'sigma': 0.5, 'samples': None, 'precomp_kernel': None}`. If `precomp_kernel` is set to a list of FIR filter taps, the pulse is convolved with them (to pre-compensate for flux-line distortion) and the played amplitude is automatically doubled to offset the roughly 50% attenuation the convolution introduces. If `samples` is set (instead of relying on `function`), that explicit sample array is played directly rather than a function-generated pulse.
- `CompZAngle`: Z-rotation phase (radians), applied as an oscillator-phase increment on the `drive_comp` signal immediately after the flux pulse, to compensate the conditional/AC-Stark phase picked up by the flux-pulsed qubit during the gate. Only applied if both `drive_comp` was supplied as a signal and this is not `None`. Defaults to `None` (no compensation).
- `CompZAngleAux`: The equivalent compensation angle applied to `drive_comp_aux`, if that optional signal was supplied. Defaults to `None`.
- `CompZAngleStationary`: The equivalent compensation angle applied to `drive_comp_stationary` — for the phase the *other* (non-flux-pulsed) qubit in the pair picks up during the gate. Defaults to `None`.

These are the same keys copied into the coupler section of a `save_config`/`create_summary_config_from_json` summary (aside from the `CompZAngle*` calibration values, which are excluded from the summary JSON).