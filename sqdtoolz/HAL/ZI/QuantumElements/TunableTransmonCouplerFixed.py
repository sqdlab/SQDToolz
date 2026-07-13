import attrs
from laboneq.dsl.quantum import (
    QPU,
    QuantumElement,
    QuantumOperations,
    QuantumParameters,
    Transmon,
)
from laboneq.simple import *
from laboneq_applications.qpu_types.tunable_transmon import TunableTransmonQubit
from sqdtoolz.Utilities.OpenQASM import QASMCompatibleQubitMultiple
from sqdtoolz.HAL.ZI.ZIQubit import ZIQubit

@attrs.define(kw_only=True)
class TunableTransmonCouplerFixedParameters(QuantumParameters):
    # QubitFlux: str = ''
    Amplitude: float = 0.5
    AmplitudeAux: float = 0.0
    Length: float = 100e-9
    Pulse: dict = attrs.field(factory=lambda: {"function": "gaussian_square", "sigma": 0.5})

class TunableTransmonCouplerFixed(QuantumElement, QASMCompatibleQubitMultiple):
    PARAMETERS_TYPE = TunableTransmonCouplerFixedParameters
    REQUIRED_SIGNALS = ("flux",)
    OPTIONAL_SIGNALS = ("flux_aux")

    def get_gate_duration(self, gate:list|tuple, qubits:list[ZIQubit]):
        if isinstance(gate[1], (tuple,list)):
            gate = (gate[0], gate[1][0])    #The gate time is irrespective of angle; if that's even allowed here... Could check if it's allowed etc...
        if gate[0] == 'ctrl' and gate[1] == 'Z':
            return self.parameters.Length
        elif gate[0] == 'ctrl' and gate[1] == 'X':
            return self.parameters.Length + qubits[1].get_gate_duration('H')
        assert False, f"Cannot implement {gate} on this coupler."

class TunableTransmonCouplerFixedOperations(QuantumOperations):
    QUBIT_TYPES = TunableTransmonCouplerFixed

    @dsl.quantum_operation
    def fixed_coupler_flux_pulse(
        self,
        q: TunableTransmonCouplerFixed,
        length: float | SweepParameter,
        amplitude: float | SweepParameter = None,
        amplitude_aux: float | SweepParameter = None
    ) -> None:
        # pulse_parameters = {"function": "gaussian_square", "sigma": 0.5}
        # flux_pulse = dsl.create_pulse(pulse_parameters, name="flux_pulse")
        flux_pulse = dsl.create_pulse(q.parameters.Pulse, name="flux_pulse")

        # assert q.parameters.QubitFlux != '', "Must set QubitFlux in the coupler."

        dsl.play(
            # self.qpu[q.parameters.QubitFlux].signals['flux'],
            q.signals['flux'],
            amplitude=amplitude if amplitude != None else q.parameters.Amplitude,
            length=length,
            pulse=flux_pulse,
        )

        aux_signal = q.signals.get("flux_aux")
        if aux_signal is not None:
            aux_amp = amplitude_aux if amplitude_aux is not None else q.parameters.AmplitudeAux
            dsl.play(
                aux_signal,
                pulse=flux_pulse,
                amplitude=aux_amp,
                length=length,
            )

    @dsl.quantum_operation
    def CZ(
        self,
        q: TunableTransmonCouplerFixed,
        phase: float = 0.0,
    ) -> None:
        # pulse_parameters = {"function": "gaussian_square", "sigma": 0.5}
        # flux_pulse = dsl.create_pulse(pulse_parameters, name="flux_pulse")
        flux_pulse = dsl.create_pulse(q.parameters.Pulse, name="flux_pulse")

        amplitude = q.parameters.Amplitude
        length = q.parameters.Length

        dsl.play(
            q.signals["flux"],
            amplitude=amplitude,
            length=length,
            # phase=phase,
            pulse=flux_pulse,
        )

        aux_signal = q.signals.get("flux_aux")
        if aux_signal is not None:
            amplitude_aux = q.parameters.AmplitudeAux
            if amplitude_aux is not None:
                dsl.play(
                    aux_signal,
                    pulse=flux_pulse,
                    amplitude=amplitude_aux,
                    length=length,
                )

# - How to infer qubits given the coupler in the QPU
# - The qubits need to be inferred to choose the correct signal path
# - In the dsl stuff:
#   - We pass the coupler to the QOP, it should automatically infer the qubits for say the flux-pulse
#   - For complicated gates like CX, we pass the coupler and the qubit name for control?
#   - Easy way to grab a given fixed-coupler given a QPU and the 2 qubits involved for the gate
#   - Ideally, it's just CX(qubit1, qubit2) - but how does it know of the coupler? Maybe it needs to be CX(qpu, qubit1, qubit2)? Here it could infer the correct coupling by using the class type QubitCoupling?
#OR alternatively, just stick with the native gate-set:
# - The CZ gate is symmetric w.r.t. the control/target designations
# - The Hadamards for a CX can be added in the QASM gate set! That is, they can slot in and overlap nicely around other gates while the CZ gate acts as the impassable barrier
# - This yields greater flexibility in scheduling etc...
