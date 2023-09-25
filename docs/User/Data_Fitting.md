# Basic Data Fitting

The following fitting functions exist:

- [Lorentzian peak/trough](#lorentzian)
- [Fano Resonance](#fano-resonance)
- [Exponential rise/decay](#exponential)
- [Sinusoid with exponential envelope](#sinusoid-with-exponential-envelope)

Each fitting function lives in a class. The fitting classes all have the function `get_fitted_plot`:

```python
dpkt = dFit.get_fitted_plot(...)
```
that returns a dictionary `dpkt` of the fitted parameters along with a plot stored in the key `'fig'`. If no no plots were requested, `'fig'` is `None`, while it is set to the associated Matplotlib figure object otherwise.

The classes also have a function `get_plot_data_from_dpkt` to query the fitted values over a given range of x-values:

```python
data_x_fits = np.arange(0,1000,0.1)
data_y_fits = dFit.get_plot_data_from_dpkt(data_x_fits, dpkt)
```


## Lorentzian

The `DFitPeakLorentzian` class fits a Lorentzian peak/trough via the equation:

$$
f(x) = A\cdot\frac{(\tfrac{w}{2})^2}{(x-x_0)^2+(\tfrac{w}{2})^2}+c
$$

The syntax is as follows:

```python
from sqdtoolz.Utilities.DataFitting import*
import numpy as np

data_x = np.arange(100,300,1)
data_y = np.exp(-(data_x-220)**2/20**2) + 0.5*np.random.rand(data_x.size)

dfit = DFitPeakLorentzian()
dpkt = dfit.get_fitted_plot(data_x, data_y)
dpkt['fig'].show()
```

The returned data packet `dpkt` contains the fitted parameters mapped as:

- `'amplitude'`: $A$ (height of Lorentzian peak)
- `'width'`: $w$ (full width half maximum of peak)
- `'centre'`: $x_0$ (centre of peak)
- `'offset'`: $c$

The `get_fitted_plot` function has optional arguments:

- `xLabel` - x-axis label
- `yLabel` - y-axis label
- `dip` - Defaults to `False`. If `True`, the fitted Lorentzian is forced to fit a dip/trough instead of a peak.
- `dontplot` - Defaults to `False`. If `True`, no plots are generated and the returned data packet will not contain the plot figure object.
- `axs` - Defaults to `None`. A Matplotlib axis object can be provided to embed the fitted plot onto the axis instead of creating a new figure.

## Fano Resonance

The `DFitFanoResonance` class fits a [Fano Resonance](https://en.wikipedia.org/wiki/Fano_resonance) trough via the equation:

$$
f(x) = A\cdot\frac{(b\tfrac{w}{2}+x-x_0)^2}{(x-x_0)^2+(\tfrac{w}{2})^2}+c
$$

The syntax is as follows:

```python
from sqdtoolz.Utilities.DataFitting import*
import numpy as np

data_x = np.arange(-10,10,0.1)
data_y = 5 * (0.75*0.5*2+data_x - 1)**2/((data_x - 1)**2 + (0.5*2)**2) + 3 + 0.5*np.random.rand(data_x.size)

dfit = DFitFanoResonance()
dpkt = dfit.get_fitted_plot(data_x, data_y)
dpkt['fig'].show()
```

The returned data packet `dpkt` contains the fitted parameters mapped as:

- `'amplitude'`: $A$ (height of resonance trough)
- `FanoFac`: $b$ (Fano factor)
- `'width'`: $w$ (full width half maximum of resonance trough)
- `'centre'`: $x_0$ (centre of resonance trough)
- `'offset'`: $c$
- `'xMinimum'` and `'xMaximum'`: minimum and maximum $x$ values of the fitted Fano resonance function.
- `'yMinimum'` and `'yMaximum'`: minimum and maximum $y$ values of the fitted Fano resonance function.

The `get_fitted_plot` function has optional arguments:

- `xLabel` - x-axis label
- `yLabel` - y-axis label
- `dontplot` - Defaults to `False`. If `True`, no plots are generated and the returned data packet will not contain the plot figure object.
- `axs` - Defaults to `None`. A Matplotlib axis object can be provided to embed the fitted plot onto the axis instead of creating a new figure.

## Exponential

The `DFitExponential` class fits an exponential rise/decay via the equation:

$$
f(x) = Ae^(-\tfrac{x}{\tau})+c
$$

The syntax is as follows:

```python
data_x = np.arange(0,10,0.05)
data_y = 1.2*(1-np.exp(-data_x/5.7)) + 0.5*np.random.rand(data_x.size)

dfit = DFitExponential()
dpkt = dfit.get_fitted_plot(data_x, data_y, rise=True)
dpkt['fig'].show()
```

The returned data packet `dpkt` contains the fitted parameters mapped as:

- `'amplitude'`: $|A|$
- `'offset'`: $c$
- `decay_rate`: $\tau$

The `get_fitted_plot` function has optional arguments:

- `xLabel` - x-axis label
- `yLabel` - y-axis label
- `rise` - Defaults to `False`. If `True`, the function is forced to be an exponential rise by forcing the fitted `A` to be negative. Otherwise, it is forced to be an exponential decay by forcing the fitted `A` to be positive.
- `dontplot` - Defaults to `False`. If `True`, no plots are generated and the returned data packet will not contain the plot figure object.
- `axs` - Defaults to `None`. A Matplotlib axis object can be provided to embed the fitted plot onto the axis instead of creating a new figure.


## Sinusoid with exponential envelope

The `DFitSinusoid` class fits a sine wave with an exponential envelope via the equation:

$$
s(x) = Ae^{-\gamma x}\cos(2\pi fx+\phi)+c
$$

The syntax is as follows:

```python
data_x = np.linspace(0.0,0.5,50)
data_y = np.array([0.23851978, 0.26857639, 0.23126279, 0.27585205, 0.26447248,
    0.27526831, 0.17744127, 0.22679398, 0.21559565, 0.24723698,
    0.35787993, 0.31643191, 0.31584339, 0.22591795, 0.22043368,
    0.18779161, 0.1751315 , 0.11268123, 0.1717033 , 0.22510175,
    0.21942741, 0.28069079, 0.3084679 , 0.30082049, 0.236087  ,
    0.29243284, 0.16359482, 0.21956686, 0.10740641, 0.08908458,
    0.13835961, 0.20114916, 0.23415966, 0.36481327, 0.3908816 ,
    0.29160973, 0.31766139, 0.23254812, 0.16462614, 0.16513641,
    0.0647385 , 0.13140232, 0.06296652, 0.11841913, 0.19849058,
    0.18849815, 0.30028236, 0.34362802, 0.31551777, 0.32641923])

dfit = DFitSinusoid()
dpkt = dfit.get_fitted_plot(data_x, data_y)
dpkt['fig'].show()
```

The returned data packet `dpkt` contains the fitted parameters mapped as:

- `'amplitude'`: $A$ (amplitude of oscillations)
- `decay_rate`: $\gamma$ (decay rate of exponential envelope)
- `'frequency'`: $f$
- `'phase'`: $\phi$
- `'offset'`: $c$

The `get_fitted_plot` function has optional arguments:

- `xLabel` - x-axis label
- `yLabel` - y-axis label
- `dontplot` - Defaults to `False`. If `True`, no plots are generated and the returned data packet will not contain the plot figure object.
- `axs` - Defaults to `None`. A Matplotlib axis object can be provided to embed the fitted plot onto the axis instead of creating a new figure.


