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
import numpy as np
from laboneq.dsl.experiment import pulse_library

@pulse_library.register_pulse_functional
def filtered_pulse(x, main_function, filter_taps, filter_delay=0, **kwargs):
    sampling_rate = kwargs["sampling_rate"]
    if kwargs.get("samples",None) is None:
        pulse = pulse_library.pulse_sampler(main_function)(x,**kwargs)
    else:
        pulse = kwargs["samples"]*1.0
    filtered = np.convolve(np.real(pulse), np.asarray(filter_taps), mode="full")[:pulse.shape[0]]
    return filtered

@attrs.define(kw_only=True)
class TunableTransmonCouplerFixedParameters(QuantumParameters):
    # QubitFlux: str = ''
    Amplitude: float = 0.5
    AmplitudeAux: float = 0.0
    Length: float = 250e-9
    Pulse: dict = attrs.field(factory=lambda: {"function": "gaussian_square", "sigma": 0.5, "samples": None, "precomp_kernel" : None})

class TunableTransmonCouplerFixed(QuantumElement, QASMCompatibleQubitMultiple):
    PARAMETERS_TYPE = TunableTransmonCouplerFixedParameters
    REQUIRED_SIGNALS = ("flux",)
    OPTIONAL_SIGNALS = ("flux_aux",)

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
        pulse_params = q.parameters.Pulse
        if pulse_params.get("precomp_kernel") is not None:
            flux_pulse = dsl.create_pulse({"function": "filtered_pulse", "main_function": pulse_params["function"], "filter_taps": pulse_params["precomp_kernel"], "filter_delay": pulse_params.get("filter_delay", 0)}, name="flux_pulse")
        else:
            if pulse_params.get("samples") is None:
                flux_pulse = dsl.create_pulse(pulse_params, name="flux_pulse")
            else:
                flux_pulse = pulse_library.sampled_pulse(uid="sampled_pulse", samples=pulse_params["samples"])

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
        amplitude: float = None,
        length:float = None,
    ) -> None:
        # pulse_parameters = {"function": "gaussian_square", "sigma": 0.5}
        # flux_pulse = dsl.create_pulse(pulse_parameters, name="flux_pulse")
        flux_pulse = dsl.create_pulse(q.parameters.Pulse, name="flux_pulse")

        if amplitude is None:
            amplitude = q.parameters.Amplitude
        if length is None:
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

