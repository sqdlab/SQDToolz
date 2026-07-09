# Setting up ZI QPU objects

In the ZI workflow, we begin by defining a QPU object, to which we add qubits (`ZI.ZIQubit`) and couplers (`ZI.ZIQuantumElement`).

```python
import sqdtoolz as stz

lab = stz.Laboratory(instr_config_file = "NQCT-02.yaml", save_dir = "/home/")
lab.load_instrument('zi_boxes')

# Define qubits and signal channels
stz.ZI.ZIQubit('Q0', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', "SIGOUTS/0"))
stz.ZI.ZIQubit('Q1', lab, 'zi_boxes', ('shfqc0', 'SGCHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/OUTPUT'), ('shfqc0', 'QACHANNELS/0/INPUT'), ('hdawg0', "SIGOUTS/1"))

# Define coupler between Q0 and Q1
ZIQuantumElement('C01', lab, TunableTransmonCouplerFixed, flux='Q1/flux')

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

### Saving a QPU config
The current configuration of a QPU object (e.g. `stz.SOFTqpu('QPU', lab)`) can be saved by running `lab.HAL('QPU').save_QPU_config()`, which will place a file `QPU_config.json` in the `lab`'s save directory.

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
ThermalPhotonNum: 0
ReadoutLineAttenuation_dB: -70
```