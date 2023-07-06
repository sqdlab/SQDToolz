# Available FPGA Procesing Nodes

This document lists all the GPU processing nodes that can be used with the `ProcessorFPGA` class discussed in the [overview](Proc_FPGA_Overview):

  * [FPGA_DDCFIR](#fpga-ddc) (digital down conversion)

## FPGA DDC+FIR

`FPGA_DDCFIR` performs both the digital downconversion and FIR filtering required for IQ-demodulation with the expectation that the signal will be integrated. To see why this works, consider an input signal:

$$M(t)=A\cos(2\pi ft + \phi) + c$$

where the amplitude $A$ and phase $\phi$ of the sinusoidal signal of frequency $f$ is desired. To demodulate, multiply the signal with cosine and sine:

$$\begin{align*}I(t) & =2\cos(2\pi ft)\cdot M(t)\equiv A\cos(\phi) \color{darkgray}+ 2c\cos(2\pi ft) + A\cos(2(2\pi f)t + \phi)\\
Q(t) & =-2\sin(2\pi ft)\cdot M(t) \equiv A\sin(\phi) \color{darkgray}- 2c\sin(2\pi ft) - A\sin(2(2\pi f)t + \phi)\end{align*}$$

To isolate the required DC components, an appropriate low-pass filter $h[k]$ with a cut-off below $f$ is applied over the discretised signals (with sample rate $f_s$):

$$\begin{align*}I_F[n]&=(h * I)[n]=\sum_{k=0}^\infty h[k]\cdot I[n-k]=\sum_{k=0}^\infty h[k]\cdot 2\cos\left(\tfrac{2\pi f}{f_s}(n-k)\right)\cdot M[n-k]\\
Q_F[n]&=(h * Q)[n]=\sum_{k=0}^\infty h[k]\cdot Q[n-k]=-\sum_{k=0}^\infty h[k]\cdot 2\sin\left(\tfrac{2\pi f}{f_s}(n-k)\right)\cdot M[n-k]\end{align*}$$

where the filter $h[k]$ is taken to be causal. Upon integrating the signal (for a signal $M[n]$ of length $N$ being zero outside $[0,N]$):

$$\begin{align*}I_o[n]&=\sum_{n=0}^NI_F[n]=\sum_{k=0}^N\sum_{n=0}^N h[k]\cdot2\cos\left(\tfrac{2\pi f}{f_s}(n-k)\right)\cdot M[n-k]\\
Q_o[n]&=\sum_{n=0}^NQ_F[n]=-\sum_{k=0}^N\sum_{n=0}^N h[k]\cdot2\sin\left(\tfrac{2\pi f}{f_s}(n-k)\right)\cdot M[n-k]\end{align*}$$

Recast the sums (noting once again that $M[n]$ is zero for $n<0$):

$$\begin{align*}I_o[n]&=\sum_{k=0}^N\sum_{m=0}^{N-k} h[k]\cdot2\cos\left(\tfrac{2\pi f}{f_s}m\right)\cdot M[m]=\sum_{m=0}^N\sum_{k=0}^{N-m} h[k]\cdot2\cos\left(\tfrac{2\pi f}{f_s}m\right)\cdot M[m]\\
Q_o[n]&=-\sum_{k=0}^N\sum_{m=0}^{N-k} h[k]\cdot2\sin\left(\tfrac{2\pi f}{f_s}m\right)\cdot M[m]=-\sum_{m=0}^N\sum_{k=0}^{N-m} h[k]\cdot2\sin\left(\tfrac{2\pi f}{f_s}m\right)\cdot M[m]\end{align*}$$

Thus, the multiplicative kernels that are used before integration are:

$$\boxed{\begin{align*}K_I[n]&=2\cos\left(\tfrac{2\pi f}{f_s}n\right)\cdot\sum_{k=0}^{N-n} h[k]\\
K_Q[n]&=-2\sin\left(\tfrac{2\pi f}{f_s}n\right)\cdot\sum_{k=0}^{N-n} h[k]
\end{align*}}$$

The advantage of this approach is that the latency can be reduced as there is no convolution operation. That is, the there is only a multiplication operation on the input signal before integration.

