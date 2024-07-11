# RF resonator Fitting

The following RF resonator fitting functions exist:

- [RF notch resonance](#rf-notch-resonance) - used for **transmission spectra** of resonators side-coupled to a transmission line.
- [RF reflectance](#rf-reflectance) - used for **reflection spectra** of resonators terminating a transmission line.


## RF notch resonance

This applies to a **transmission spectra for resonators side-coupled to a transmission line**. The corresponding equation can be shown to be (c.f. [fitting paper](https://pubs.aip.org/aip/rsi/article-abstract/86/2/024706/360955/Efficient-and-robust-analysis-of-complex?redirectedFrom=fulltext)):

$$
S_{21}(f)=Ae^{j(2\pi f\tau + \alpha)}\left(1-\frac{\tfrac{Q_L}{|Q_c|}e^{j\phi}}{1+2jQ_L\left(\tfrac{f}{f_0}-1\right)}\right) + I_0+jQ_0
$$

Note that:
- The loaded quality factor is defined in terms of the internal and coupling quality factors as $Q_L^{-1}=Q_{\textnormal{int}}^{-1}+\Re(Q_c^{-1})$
- The complex coupling quality factor is $|Q_c|\cdot e^{-i\phi}$
- $\omega\tau+\alpha$ represents the phase trend that occurs due to the finite cable lengths
- The offset $I_0+jQ_0$ is due to instrumentation and/or strange mismatches in the probing instrumentation.

### General usage

The syntax is as follows:

```python
from sqdtoolz.Utilities.DataFitting import DFitNotchResonance

#Assuming that the data is given as freqs, i_vals, q_vals
dFit = DFitNotchResonance()
dpkt = dFit.get_fitted_plot(freqs, i_vals, q_vals)
```

The returned data packet `dpkt` contains the fitted parameters mapped as:

- `'fres'`: $f_0$ (resonant frequency)
- `'Qi'`: $Q_\textnormal{int}$
- `'|Qc|'`: $|Q_c|$
- `'Ql'`: $Q_L$
- `'arg(Qc)'`: $\arg(Q_c)$
- `'tau'`: $\tau$
- `'alpha'`: $\alpha$
- `'ampl'`: $A$
- `'i_offset'`: $I_0$
- `'q_offset'`: $Q_0$

The `get_fitted_plot` function has optional arguments:

- `phase_deriv_smooth_fac` - The number of taps in the filter used to smooth out the phase derivative when fitting the maximum phase derivative (at the resonant frequency). Defaults to `5`. Increasing it will smoothen the phase derivative prior to fitting.
- `prop_detrend_start` - The proportion (defaults to `0.05`) of data from the beginning (lower end of the frequencies) to use in fitting the detrending line.
- `prop_detrend_end` - The proportion (defaults to `0.05`) of data in the end (higher end of the frequencies) to use in fitting the detrending line.
- `dont_plot_estimates` - Defaults to `False`. If `True`, the row of estimated plots is omitted and only the final amplitude, phase and IQ curves are drawn.

### Methodology

The fitting function requires accurate estimates of the final parameters. This section highlights the methods used to compute good initial guesses.

The first step is to remove any phase trends due to the finite length of the probing cables. The idea is to fit a line to the phase trend off-resonant from the main peak. The gradient and y-intercept of the linear fit readily gives $\tau$ and $\alpha$. Now by multiplying $e^{-j(\omega\tau+\alpha)}$ to negate the phase slope, the detrended phase slope at resonance is given by:

$$
p_0=\frac{dS_{21}(f_0)}{df}=\frac{-2Q_L^2(Q_L-Q_c\cos(\phi))}{f_0(Q_L^2+Q_c^2-2Q_LQ_c\cos(\phi))}
$$

which when ignoring $\phi$ yields a simple expression:

$$
Q_c=\frac{Q_L(f_0p_0+2Q_L)}{f_0p_0}.
$$

Note that the phase slope provides an accurate estimate for $f_0$. Now fitting $|S_{21}|^2$ to a [Fano-Resonacne](Data_Fitting.md#fano-resonance) yields the peak-width which gives the other required quality factor $Q_L$.

Finally, looking at the detrended raw data (calculated by multiplying $e^{-j(\omega\tau+\alpha)}$), one may fit the resulting circle to get the centre-point of the raw data $(I_R, Q_R)$ and the radius $R$. The radius relates to the amplitude as: $A=2R$. Compute $\phi$ by taking the polar angle of the vector starting from the IQ point corresponding to the resonant frequency and ending at $(I_R,Q_R)$.

Now computing the fitted function (on the detrended data - so taking $I_0=Q_0=\alpha=\tau=0$), one may fit a circle to get its centre point $(I_f,Q_f)$. Now compute: $(I_0,Q_0)=(I_R-I_f, Q_R-Q_f)$.

Note that the final fit is done on the detrended data (thus, setting $\alpha=\tau=0$). The fit may still readjust and find finite values for $\alpha$ and $\tau$. Simply add these fitted values to the previous values of $\alpha$ and $\tau$ found it the detrending step to get the final fitting parameters.

In addition, it is noteworthy that least-squares residual used in circle fits can be easily skewed by the resonance datasets as many points tend to bunch up in a single region. To alleviate this bias, the data is first interpolated in equal arc-lengths. Then to combat the possibility of data going back and forth (due to noise), points that are close by are culled. The resulting dataset is used in the circle fitting procedures.


## RF reflectance

This applies to a **reflection spectra for resonators terminating transmission line**. The corresponding equation can be shown to be (c.f. [appendix D in thesis](https://unsworks.unsw.edu.au/entities/publication/6d9ea387-bc52-49d2-b5c2-6979779f4d30)):

$$
S_{11}(f)=-A\cdot\frac{1-\tfrac{\text{Q}_\text{ext}}{\text{Q}_\text{int}}\left(1+j\text{Q}_\text{int}\left(\tfrac{f}{f_0}-\tfrac{f_0}{f}\right)\right)}
{1+\tfrac{\text{Q}_\text{ext}}{\text{Q}_\text{int}}\left(1+j\text{Q}_\text{int}\left(\tfrac{f}{f_0}-\tfrac{f_0}{f}\right)\right)}\cdot \exp\left({j\frac{4\pi L}{c}f+j\phi}\right)
$$

Note that:
- The loaded quality factor is defined in terms of the internal and external quality factors as $Q_L^{-1}=Q_{\textnormal{int}}^{-1}+Q_{\textnormal{ext}}^{-1}$
- The complex exponential factor represents the phase trend that occurs due to the finite cable lengths ($L$ given the speed of light $c$)


### General usage

The syntax is as follows:

```python
from sqdtoolz.Utilities.DataFitting import DFitReflectanceResonance

#Assuming that the data is given as freqs, i_vals, q_vals
dFit = DFitReflectanceResonance()
dpkt = dFit.get_fitted_plot(freqs, i_vals, q_vals)
```

The returned data packet `dpkt` contains the fitted parameters mapped as:

- `'fres'`: $f_0$ (resonant frequency)
- `'Qint'`: $Q_\textnormal{int}$
- `'Qext'`: $Q_\textnormal{ext}$
- `'Qeff'`: $Q_L$
- `'Length'`: $L$
- `'Amplitude'`: $A$
- `'Phase'`: $\phi$

The `get_fitted_plot` function has optional arguments:

- `phase_slope_smooth_num` - The number of taps in the filter used to smooth out the phase derivative when fitting the maximum phase derivative (at the resonant frequency). Defaults to `25`. Increasing it will smoothen the phase derivative prior to fitting.
- `prop_detrend_start` - The proportion (defaults to `0.05`) of data from the beginning (lower end of the frequencies) to use in fitting the detrending line.
- `prop_detrend_end` - The proportion (defaults to `0.05`) of data in the end (higher end of the frequencies) to use in fitting the detrending line.
- `dont_plot` - Defaults to `False`. If `True`, nothing is plotted (just the fitted parameters are returned)
- `dont_plot_estimates` - Defaults to `False`. If `True`, the row of estimated plots is omitted and only the final amplitude, phase and IQ curves are drawn.

### Methodology

The fitting function requires accurate estimates of the final parameters. This section highlights the methods used to compute good initial guesses.

The first step is to remove any phase trends due to the finite length of the probing cables. The idea is to fit a line to the phase trend off-resonant from the main peak. The gradient and y-intercept of the linear fit readily gives $L$ and $\phi$. Now by multiplying $\exp\left({-j\frac{4\pi L}{c}f-j\phi}\right)$ to negate the phase slope, the detrended phase slope at resonance is given by:

$$
p_0=\left.\frac{d\phi}{df}\right|_{f=f_0}=\frac{\text{Q}_\text{ext}\text{Q}_\text{int}^2}{2\pi f_0(\text{Q}_\text{ext}^2-\text{Q}_\text{int}^2)}.
$$

Now looking at the amplitude, the resulting trough will have a height (that is, the vertical size when viewing the amplitude plot - found by fitting a Lorentzian to the amplitude response $|S_{11}|$):

$$
h=\frac{2A\text{Q}_\text{int}}{\text{Q}_\text{int}+\text{Q}_\text{ext}}.
$$

Now algebraically solve the equations to get:

$$
\begin{align}
\text{Q}_\text{ext}&=\left\lbrace
\begin{array}{lc}
-\tfrac{2\pi(h-1)f_0}{h^2}\cdot\tfrac{d\phi}{df} & \tfrac{d\phi}{df}>0 \\
\tfrac{2\pi(h-1)f_0}{(h-2)^2}\cdot\tfrac{d\phi}{df} & \tfrac{d\phi}{df}<0
\end{array}
\right.\\
\text{Q}_\text{int}&=\left\lbrace
\begin{array}{lc}
\tfrac{2\pi(h-1)f_0}{h(h-2)}\cdot\tfrac{d\phi}{df} & \tfrac{d\phi}{df}>0 \\
-\tfrac{2\pi(h-1)f_0}{h(h-2)}\cdot\tfrac{d\phi}{df} & \tfrac{d\phi}{df}<0
\end{array}
\right..
\end{align}
$$

The resonance phase slope be found by smoothing a finite difference taken over $\arg(S_{11})$.
