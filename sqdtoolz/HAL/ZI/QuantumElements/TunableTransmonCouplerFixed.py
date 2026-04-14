import attrs
from laboneq.dsl.quantum import (
    QPU,
    QuantumElement,
    QuantumOperations,
    QuantumParameters,
    Transmon,
)
from laboneq.simple import *

@attrs.define(kw_only=True)
class TunableTransmonCouplerFixedParameters(QuantumParameters):
    # QubitFlux: str = ''
    Amplitude: float = 0.5
    Length: float = 100e-9
    Pulse: dict = attrs.field(factory=lambda: {"function": "gaussian_square", "sigma": 0.5})

class TunableTransmonCouplerFixed(QuantumElement):
    PARAMETERS_TYPE = TunableTransmonCouplerFixedParameters
    REQUIRED_SIGNALS = ("flux",)

class TunableTransmonCouplerFixedOperations(QuantumOperations):
    QUBIT_TYPES = TunableTransmonCouplerFixed

    @dsl.quantum_operation
    def fixed_coupler_flux_pulse(
        self,
        q: TunableTransmonCouplerFixed,
        amplitude: float | SweepParameter,
        length: float | SweepParameter
    ) -> None:
        # pulse_parameters = {"function": "gaussian_square", "sigma": 0.5}
        # flux_pulse = dsl.create_pulse(pulse_parameters, name="flux_pulse")
        flux_pulse = dsl.create_pulse(q.parameters.Pulse, name="flux_pulse")

        # assert q.parameters.QubitFlux != '', "Must set QubitFlux in the coupler."

        dsl.play(
            # self.qpu[q.parameters.QubitFlux].signals['flux'],
            q.signals['flux'],
            amplitude=amplitude,
            length=length,
            pulse=flux_pulse,
        )

    @dsl.quantum_operation
    def CX(
        self,
        q: TunableTransmonCouplerFixed,
        qubit_name_control: str,
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
            phase=phase,
            pulse=flux_pulse,
        )

# - How to infer qubits given the coupler in the QPU
# - The qubits need to be inferred to choose the correct signal path
# - In the dsl stuff:
#   - We pass the coupler to the QOP, it should automatically infer the qubits for say the flux-pulse
#   - For complicated gates like CX, we pass the coupler and the qubit name for control?
#   - Easy way to grab a given fixed-coupler given a QPU and the 2 qubits involved for the gate
#   - Ideally, it's just CX(qubit1, qubit2) - but how does it know of the coupler? Maybe it needs to be CX(qpu, qubit1, qubit2)? Here it could infer the correct coupling by using the class type QubitCoupling?

