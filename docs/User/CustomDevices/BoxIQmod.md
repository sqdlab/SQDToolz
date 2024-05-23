# Qubit Control and Readout Box (IQ modulation)

This is a compact **1U rack-mount module** that enables qubit readout and control (with in-situ mixer calibration). The layout is as follows:

![My Diagram3](BoxIQmod.drawio.svg)

The front panel consists of all SMA ports except the two DC ports which are BNC. The general usage notes will be highlighted in the sections below.

## Readout

The box uses a heterodyne scheme for the readout. The idea is that:

- The readout resonator is excited (directly into the fridge input outside the box) at the resonant frequency $f_0$.
- The output from the fridge looks like $A\cos(2\pi f_0 t + \varphi)$ where the goal is to find $I=A\cos(\varphi)$ and $Q=A\sin(\varphi)$.
- The LO downconversion source is set to $f_0+f_{off}$ (can be any frequency offset, but it is convenient to typically use $f_{off}=25~\textnormal{MHz}$). Useful to utilise [`VariableSpaced`](../Var_Defns.md).
- The *Marki MLIQ0218L* is a wide-band mixer that can operate over 2-18GHz and thus, covers the usual 6.9-12GHz resonator range. It embeds the amplitude and phase of the readout output from the fridge onto the signal: $A\cos(2\pi f_{off}t+\varphi)$.
- The signal is subsequently filtered for aliases and amplified before sending into the ADC digitiser where the signal is digitally demodulated and filtered to extract the I and Q components (either in the [CPU](../Proc_CPU_list.md#cpu-ddc)/[GPU](../Proc_GPU_list.md#gpu-ddc) or onboard any [FPGA](../Proc_FPGA_list.md#fpga-ddc) processors).

The advantages of this method are:

- No filters or IQ-modulators are required (as with a homodyne upconversion setup where the second sideband requires elimination).
- Only one digitiser input is required (as opposed to two if downconverting exactly to DC when using $f_0$ for the LO).

## Qubit control and mixer calibration

The qubit is controlled via [IQ modulation](../MeasurementMethods/IQmod.md) via the two AWG ports and the MW LO port. The mixer DC offsets are controlled via the two DC BNC ports (feeding into Bias-Ts). The *Marki MLIQ0218L* was once again chosen for its wide-band operation (albeit, the splitter it to 4-12GHz qubit frequency operation). 

To perform mixer calibration, the *RADIALL R570432100* switch is set to port 1 to sniff the signal sent directly to the fridge. This signal is sent to the downconversion readout setup. That is:

- The downconversion LO is set to $f_{in}+f_{off}$ and the digital demodulation is done on $f_{off}$.
- This effectively makes the readout setup a spectrum analyser where the manitude of any peak at $f_{in}$ can be sampled.
- By sweeping the value of $f_{in}+f_{off}$ on the downconversion LO source, one may sample the magnitudes of the sideband and LO peaks.

The panel LED lights up to indicate that the switch is on mixer calibration mode. To use the switch, simply instantiate the [HAL](../GENswitch.md) over the driver YAML:

```yaml
  sw_qbox:
    type: sqdtoolz.Drivers.SW_RpiIQBox.SW_RpiIQBox
    address: 'TCPIP::192.168.1.19::4000::SOCKET'
    parameters:
      pulse_delay_time:
        initial_value: 1
```

Just change the IP address of the Raspberry Pi (with the [drivers](https://github.com/sqdlab/SQDdevRPi) installed) as appropriate. The switch states are given as `'Pmix'` and `'Pmeas'` for mixer calibration and normal readout measurements respectively.
