# Available GPU Procesing Nodes

This document lists all the GPU processing nodes that can be used with the `ProcessorGPU` class discussed in the [overview](Proc_GPU_Overview):

  * [GPU_DDC](#gpu-ddc) (digital down conversion)
  * [GPU_FIR](#gpu-fir) (FIR filter)
  * [GPU_Mean](#gpu-mean)
  * [GPU_MeanBlock](#gpu-meanblock)
  * [GPU_Max](#gpu-max)
  * [GPU_Integrate](#gpu-integrate)
  * [GPU_ChannelArithmetic](#gpu-channelarithmetic)
  * [GPU_ConstantArithmetic](#gpu-constantarithmetic)
  * [GPU_FFT](#gpu-fft)
  * [GPU_ESD](#gpu-esd)
  * [GPU_Duplicate](#gpu-duplicate)
  * [GPU_Rename](#gpu-rename)

## GPU DDC

`GPU_DDC` performs the digital downconversion stage required for IQ-demodulation. That is, consider the following ipnut signal:

$$M(t)=A\cos(2\pi ft + \phi) + k$$

where the amplitude *A* and phase *ɸ* of the sinusoidal signal of frequency *f* is desired. The `GPU_DDC` node will take every channel and demodulate each channel to produce two new outputs (thereby replacing the each input with two new output channels):

$$\begin{align*}I(t) & =2\cos(2\pi ft)\cdot M(t)\equiv A\cos(\phi) \color{darkgray}+ 2k\cos(2\pi ft) + A\cos(2(2\pi f)t + \phi)\\
Q(t) & =-2\sin(2\pi ft)\cdot M(t) \equiv A\sin(\phi) \color{darkgray}- 2k\sin(2\pi ft) - A\sin(2(2\pi f)t + \phi)\end{align*}$$

The *I* and *Q* outputs have constant terms that are of interest. The time-varying sinusoidal terms (marked in grey) are culled via a low-pass filter (such as a `GPU_FIR` stage that follows the `GPU_DDC` stage). The cut-off frequency of the low-pass filter (must be evidently smaller than *f*) sets the bandwidth of the resulting signal given in *A*. The actual amplitude and phase can be extracted via:

$$\begin{align*}A&=\sqrt{I^2 + Q^2}\\
\phi&=\arg(I + jQ)\end{align*}$$

To use the `GPU_DDC` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_DDC([25e6, 25e6]) )
```

The argument for `GPU_DDC` is a list of the demodulation frequencies (that is, *f* in the equations above) on every input channel. In the above example, the input signal has two channels and therefore, two demodulation frequencies (incidentally 25MHz on both channels) are specified.

Note that the two output channels for any channel input are given the same name but with the suffix `_I` and `_Q`. For example, an input channel of name `CH2` is removed to give two channels of names `CH2_I` and `CH2_Q`.

## GPU FIR

`GPU_FIR` performs a low or high pass filter on all input channels of the signal via premade filter coefficients specified by [`scipy.signal.firwin`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.firwin.html). To use the `GPU_FIR` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_FIR([{'Type' : 'low', 'Taps' : 128, 'fc' : 1e6, 'Win' : 'hamming'}]*2) )
```

Note that the argument is a list of dictionaries; one for every channel (in the above example, there are 2 dictionaries in the list as appropriate when requiring 2 FIR filters for I and Q signals). Each dictionary specifies the filter parameters in with their keys:

- `Type` - either `low` or `high` for a low or high pass filter respectively
- `Taps` - the size/depth of the FIR filter with more taps increasing the filter roll-off. Note that the number of taps should ideally be lower than the total signal length to get sensible data.
- `fc` - cut-off frequency in Hertz
- `Win` - the [scipy.signal window](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.get_window.html#scipy.signal.get_window) type. For example, a usual one is `'hamming'`.

Note that the **output is the same size as the input**. This is achieved via the default half-sample symmetric behavior in which a signal `(a b c d)` is augmented as `(d c b a | a b c d | d c b a)` before performing the convolution.

## GPU Mean

`GPU_Mean` takes the mean across a prescribed dimension and **will thereby contract said dimension**. To use the `GPU_Mean` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_Mean('sample') )
```

The argument for `GPU_Mean` is the name of the dimension to which the mean is taken. For example, in a typical [ACQ HAL](ACQ.md), this would be `'sample'`, `'segment'` or `'repetition'`. Note that if one were to take the mean across the left-most/outer-most dimension (e.g. `'repetition'`), it should be done so using `add_stage_end` for the entire dataset must fully acquired to take a valid overall mean.

## GPU MeanBlock

`GPU_MeanBlock` takes a block-mean, across a given dimension, on every channel of an input signal to thereby downsample the signal. The input signal is divided into blocks upon which the mean across each block is taken. To use the `GPU_MeanBlock` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_MeanBlock('sample', 5) )
```

Note the following:

- The first argument in `GPU_MeanBlock` is the dimension across which the block-mean is taken (similar to `GPU_Mean`), while The second argument is the size (in the number of raw samples) of the block.
- For example, if the signal has 91 samples, the above example code would produce 18 blocks of size 5 (that is, **residual samples are discarded**). Upon taking the mean within each individual block,  which a 18 block means are taken to produce an 18 point signal.
- The dimension across which the mean is taken is not contracted if the block size equals the sample signal size (unlike `GPU_Mean`).

The functionality of `GPU_MeanBlock` is effectively the result of oversampling and averaging to increase signal resolution while downsampling like a decimation algorithm.

## GPU Max

`GPU_Max` takes the maximum across a prescribed dimension and **will thereby contract said dimension**. To use the `GPU_Max` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_Max('sample') )
```

The argument for `GPU_Max` is the name of the dimension to which the mean is taken. For example, in a typical [ACQ HAL](ACQ.md), this would be `'sample'`, `'segment'` or `'repetition'`. Note that if one were to take the maximum across the left-most/outer-most dimension (e.g. `'repetition'`), it should be done so using `add_stage_end` for the entire dataset must fully acquired to take a valid overall maximum.

## GPU Integrate

`GPU_Integrate` takes the sum across a prescribed dimension and **will thereby contract said dimension**. To use the `GPU_Integrate` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_Integrate('sample') )
```

The argument for `GPU_Integrate` is the name of the dimension to which the mean is taken. For example, in a typical [ACQ HAL](ACQ.md), this would be `'sample'`, `'segment'` or `'repetition'`. Note that if one were to take the summation across the left-most/outer-most dimension (e.g. `'repetition'`), it should be done so using `add_stage_end` for the entire dataset must fully acquired to take a valid overall summation.

## GPU ChannelArithmetic

`GPU_ChannelArithmetic` performs a simple binary operation across two input channels while keeping/discarding the two input channels if desired. To use the `GPU_ChannelArithmetic` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_ChannelArithmetic([0, 2], '+', True) )
```

Note that:
- The first argument in `GPU_ChannelArithmetic` is a list of channel indices (in the above example, the binary operation is performed between the first and third input channels). Note that both indices can of the same channel.
- The second argument is the binary operation. One may select: `'+'`, `'-'`, `'*'`, `'/'`, `'%'` for addition, subtraction, multiplication, division and modulo respectively.
- The third argument will discard the two input channels if set to `True`.

Note that the design choice to choose channel indices is for portability of code for the channel names stem from the physical channel names down in the ACQ driver; for example, a two channel signal from the first and fifth inputs of an ACQ HAL will perhaps yield the names `'CH1'` and `'CH5'` etc.

## GPU ConstantArithmetic

`GPU_ConstantArithmetic` performs a binary operation on a given list of channels with some prescribed constant. 
To use the `GPU_ConstantArithmetic` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_ConstantArithmetic(4, '/', [0, 2]) )
lab.PROC('test').add_stage( stz.GPU_ConstantArithmetic(5, '+', None) )
```

In this example, the first node will divide the first and third channels by 4, while the second node will add 5 to all channels. Note that:

- The first argument in `GPU_ConstantArithmetic` is a **constant to act as the second argument in the binary operation**.
- The second argument is the binary operation. One may select: `'+'`, `'-'`, `'*'`, `'/'`, `'%'` for addition, subtraction, multiplication, division and modulo respectively.
- The third argument is a list of channel indices (in the above example, the first node performs the division by 4 on the first and third input channels). If `None` is specified instead of a list (like in the second node of the example above), then the constant operation is performed (in this case adding 5) on all input channels.

Note that the design choice to choose channel indices is for portability of code for the channel names stem from the physical channel names down in the ACQ driver; for example, a two channel signal from the first and fifth inputs of an ACQ HAL will perhaps yield the names `'CH1'` and `'CH5'` etc.

## GPU FFT

`GPU_FFT` performs an FFT (default [numpy convention](https://numpy.org/doc/stable/reference/generated/numpy.fft.fft.html)) on a single or double input signal (taken as *I*+*jQ* in this case). It will **throw an error if the input signal has more than two channels**.To use the `GPU_FFT` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_FFT() )
```

Note that:
- One may optionally add an argument to `GPU_FFT` to highlight which indices (in the case of a two-channel waveform) are I and Q via a tuple (e.g. `(1,0)` would indicate that the second channel is I and the first channel is Q).
- The FFT is done over the inner/right-most index of the array with the input channels replaced by the new channels: `'fft_real'` and `'fft_imag'`.
- The accompanying frequencies are given over the inner/right-most index and placed in `'fft_frequency'` under the key `'parameter_values'`.
- Once again, if there is 1 input channel, the FFT is over just the single real channel, while 2 channels yields the FFT over the complex amalgamation: *I*+*jQ*.

## GPU ESD

`GPU_ESD` gives the energy-spectral-density of an incoming signal (that is, the the squared norm of the FFT). Its operation, preconditions and syntax are identical to that of [GPU_FFT](#gpu-fft) except for the following:

- It's called `GPU_ESD` instead of `GPU_FFT`
- Instead of outputting the two channels `'fft_real'` and `'fft_imag'`, it instead outputs only one channel: `esd`.

## GPU Duplicate

`GPU_Duplicate` duplicates data on every input channel by a prescribed number. This may be useful in some data processing chains where one may wish to apply different layers of processing across the same input channel. To use the `GPU_Duplicate` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_Duplicate([3,4,1]) )
```

The argument for `GPU_Duplicate` is a list with the number of duplications required per input channel (in the example above, the first channel is duplicated 3 times, the second channel is duplicated 4 times and the third channel is left alone). Note that the duplicated channels are enumerated from `_0` up to the number of times it is to be duplicated. In the above example, if the input channels are named `CH2`, `CH5` and `CH7`, then the duplication yields:

- `CH2` is removed to give three channels of names `CH2_0`, `CH2_1` and `CH2_2`; each with a copy of the dataset held initially in `CH2`.
- `CH5` is removed to give three channels of names `CH5_0`, `CH5_1`, `CH5_2` and `CH5_3`; each with a copy of the dataset held initially in `CH5`.
- `CH7` is left alone as `CH7` as it is not to be duplicated.

## GPU Rename

`GPU_Rename` renames all input channels. To use the `GPU_Rename` stage, consider the following code (assuming that `lab` is a valid `Laboratory` object):

```python
import sqdtoolz as stz
...
stz.ProcessorGPU('test', lab)
...
lab.PROC('test').add_stage( stz.GPU_Rename(['mark', 'pace', 'calib']) )
```

Note that the argument for `GPU_Rename` is simply a list of signal names that must match the number of input channels right before the `GPU_Rename` stage. If the correct number of names is not provided, an error will be thrown. Note that the ordering of input channels is well-defined for Python `dict` objects are ordered from Python 3.6 and 3.7 onwards in which the order is guaranteed to be the order of insertion (which in this case starts from the `ACQ` driver).


