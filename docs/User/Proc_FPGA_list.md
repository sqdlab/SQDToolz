# Available FPGA Procesing Nodes

This document lists all the FPGA processing nodes that can be used with the `ProcessorFPGA` class discussed in the [overview](Proc_FPGA_Overview):

  * [FPGA_DDCFIR](#fpga-ddc+fir) (digital down conversion and filtering)
  * [FPGA_DDC](#fpga-ddc) (digital down conversion)
  * [FPGA_FIR](#fpga-fir) (FIR filtering)
  * [FPGA_Decimation](#fpga-decimation)
  * [FPGA_Integrate](#fpga-integrate)
  * [FPGA_Mean](#fpga-mean)

## FPGA DDC+FIR

`FPGA_DDCFIR` performs both the digital downconversion and FIR filtering required for IQ-demodulation with the expectation that:

- The FPGA supports a **multiplication block** where the signal $x[n]$ is multiplied by some 'kernel' $k[n]$ to get: $y[n]=x[n]k[n]$.
- The **signal must be integrated after this operation**.

To see why this works, consider an input signal:

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

To use the `FPGA_DDCFIR` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorFPGA('test', lab)
...
lab.PROC('test').add_stage( FPGA_DDCFIR([
  [{'fLO':25e6, 'fc':10e6, 'Taps':40, 'Win' : 'hamming'}]
  [{'fLO':25e6, 'fc':10e6, 'Taps':40}, {'fLO':10e6, 'fc':5e6, 'Taps':40}]
  ]) )
```

The syntax has facets of [`FPGA_DDC`](#fpga-ddc) and [`FPGA_FIR`](#fpga-fir). That is, the argument is a is a **list of lists** corresponding to **demodulation frequencies for every input channel**. Each entry for a demodulation channel is a dictionary containing the demodulation frequency via the argument `'fLO'`. The rest of the arguments (noting that `'Win` is optional) correspond to the same arguments given for [`FPGA_FIR`](#fpga-fir). Note that in the above example, there are 2 channels of signals where the first channel is demodulated by 25MHz filtered at 10MHz, while the second channel is demodulated on two tones 25MHz and 10MHz filtered at 10MHz and 5MHz respectively.


## FPGA DDC

`FPGA_DDC` performs the digital downconversion stage required for IQ-demodulation. That is, consider the following input signal:

$$M(t)=A\cos(2\pi ft + \phi) + k$$

where the amplitude *A* and phase *ɸ* of the sinusoidal signal of frequency *f* is desired. The `FPGA_DDC` node will take every channel and demodulate each channel to produce two new outputs (thereby replacing the each input with two new output channels):

$$\begin{align*}I(t) & =2\cos(2\pi ft)\cdot M(t)\equiv A\cos(\phi) \color{darkgray}+ 2k\cos(2\pi ft) + A\cos(2(2\pi f)t + \phi)\\
Q(t) & =-2\sin(2\pi ft)\cdot M(t) \equiv A\sin(\phi) \color{darkgray}- 2k\sin(2\pi ft) - A\sin(2(2\pi f)t + \phi)\end{align*}$$

The *I* and *Q* outputs have constant terms that are of interest. The time-varying sinusoidal terms (marked in grey) are culled via a low-pass filter (such as a `FPGA_FIR` stage that follows the `FPGA_DDC` stage). The cut-off frequency of the low-pass filter (must be evidently smaller than *f*) sets the bandwidth of the resulting signal given in *A*. The actual amplitude and phase can be extracted via:

$$\begin{align*}A&=\sqrt{I^2 + Q^2}\\
\phi&=\arg(I + jQ)\end{align*}$$

To use the `FPGA_DDC` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorFPGA('test', lab)
...
lab.PROC('test').add_stage( stz.FPGA_DDC([[25e6], [25e6, 10e6]]) )
```

The argument for `FPGA_DDC` is a **list of lists** corresponding to **demodulation frequencies** (that is, *f* in the equations above) **for every input channel**. That is, some FPGA modules support multi-tone demodulation on signals from a single channel. In the above example, the input signal has two channels and therefore, two list entries. The first channel has one tone demodulated at 25MHz, while the second channel demodulates 2 tones at 25MHz and 10MHz respectively.

Note that the output is still flattened. That is, the labelling of the output data streams are given with the channel name and suffix `_m_I` and `m_Q` where `m` is the zero-based demodulation index. In the example above, this yields: `CH1_0_I`, `CH1_0_Q`, `CH2_0_I`, `CH2_0_Q`, `CH2_1_I` and `CH2_1_Q`.

## FPGA FIR

`FPGA_FIR` performs a low or high pass filter on all input channels of the signal via premade filter coefficients specified by [`scipy.signal.firwin`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.firwin.html). To use the `FPGA_FIR` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorFPGA('test', lab)
...
lab.PROC('test').add_stage( stz.FPGA_FIR([{'Type' : 'low', 'Taps' : 128, 'fc' : 1e6, 'Win' : 'hamming'}]*6) )
```

Note that the argument is a list of dictionaries; one for every channel in the data stream (in the above example, there are 6 dictionaries in the list as appropriate when requiring 6 FIR filters for I and Q signals given in a previous [example with the DDCs](#fpga-ddc)). Each dictionary specifies the filter parameters in with their keys:

- `Type` - either `low` or `high` for a low or high pass filter respectively
- `Taps` - the size/depth of the FIR filter with more taps increasing the filter roll-off. Note that the number of taps should ideally be lower than the total signal length to get sensible data.
- `fc` - cut-off frequency in Hertz
- `Win` - the [scipy.signal window](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.get_window.html#scipy.signal.get_window) type. For example, a usual one is `'hamming'`.

Note that the **output is the same size as the input**. This is achieved via the default half-sample symmetric behavior in which a signal `(a b c d)` is augmented as `(d c b a | a b c d | d c b a)` before performing the convolution.

## FPGA Decimation

`FPGA_Decimation` reduces the number of points in the signal along a given axis via decimation (that is, only sampling every $n$ number of points). To use the `FPGA_Decimation` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorFPGA('test', lab)
...
lab.PROC('test').add_stage(FPGA_Decimation('sample', 10))
```

The argument for `FPGA_Decimation` is the name of the dimension along which the decimation is to be performed. For example, in a typical [ACQ HAL](ACQ.md), this would be `'sample'`, `'segment'` or `'repetition'`. In the above example, the `'sample'` axis is decimated by a factor 10; that is, only every tenth point is taken in the final output.

## FPGA Integrate

`FPGA_Integrate` takes the sum across a prescribed dimension and **will thereby contract said dimension**. To use the `FPGA_Integrate` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorFPGA('test', lab)
...
lab.PROC('test').add_stage( stz.FPGA_Integrate('sample') )
```

The argument for `FPGA_Integrate` is the name of the dimension along which to integrate. For example, in a typical [ACQ HAL](ACQ.md), this would be `'sample'`, `'segment'` or `'repetition'`.

## FPGA Mean

`FPGA_Mean` takes the mean across a prescribed dimension and **will thereby contract said dimension**. To use the `FPGA_Mean` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorFPGA('test', lab)
...
lab.PROC('test').add_stage( stz.FPGA_Mean('sample') )
```

The argument for `FPGA_Mean` is the name of the dimension to which the mean is taken. For example, in a typical [ACQ HAL](ACQ.md), this would be `'sample'`, `'segment'` or `'repetition'`.

