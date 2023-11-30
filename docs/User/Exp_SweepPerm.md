# Sample ordering in experiment sweeps

The classes of concern here are to permute the sampling order when running [sweeps](Exp_Sweep.md#changing-the-sampled-order-in-sweeps). Note that the objects are provided directly to the `run_single` command as a list for the keyword argument `sweep_orders`:

- [Snake an axis (ExSwpSnake)](#snake-an-axis-exswpsnake)
- [Randomise an axis (ExSwpRandom)](#randomise-an-axis-exswprandom)

## Snake an axis (ExSwpSnake)

`ExSwpSnake` does the following:

- Given a multidimensional sweep, `ExSwpSnake(m)` will alternate between forward and reverse ordering when setting the values for axis index $m>0$.
- Useful when large jumps are undesirable on a given parameter.

Consider the example:

```python
from sqdtoolz.ExperimentSweeps import*
...
#Assuming that exp is an Experiment object and lab is a Laboratory object
lab.run_single(exp, [(lab.VAR('power'), np.arange(-30, 10, 10)), (lab.VAR('flux'), np.arange(0,20,0.1))], sweep_orders=[ExSwpSnake(1)])
```

The `sweep_orders=[ExSwpSnake(1)]` command ensures that the index 1 variable (i.e. `'flux'`) is now swept as a snake to get:

```python
lab.VAR("power").Value = -30
## Sweep Flux forwards
lab.VAR("flux").Value = 0.0
# --- Get Data --- #
lab.VAR("flux").Value = 0.1
# --- Get Data --- #
...
lab.VAR("flux").Value = 19.8
# --- Get Data --- #
lab.VAR("flux").Value = 19.9
# --- Get Data --- #

lab.VAR("power").Value = -20
## Sweep Flux backwards
lab.VAR("flux").Value = 19.9
# --- Get Data --- #
lab.VAR("flux").Value = 19.8
# --- Get Data --- #
...
lab.VAR("flux").Value = 0.1
# --- Get Data --- #
lab.VAR("flux").Value = 0.0
# --- Get Data --- #

lab.VAR("power").Value = -10
## Sweep Flux forwards
lab.VAR("flux").Value = 0.0
# --- Get Data --- #
lab.VAR("flux").Value = 0.1
# --- Get Data --- #
...
lab.VAR("flux").Value = 19.8
# --- Get Data --- #
lab.VAR("flux").Value = 19.9
# --- Get Data --- #
...
```

## Randomise an axis (ExSwpRandom)

`ExSwpRandom` does the following:

- Given a multidimensional sweep, `ExSwpRandom(m)` will randomise the order each time when sweeping dimension `m`.
- Useful in experiments where the sampling is ideally random along a given axis to exclude drift etc.

Consider the example:

```python
from sqdtoolz.ExperimentSweeps import*
...
#Assuming that exp is an Experiment object and lab is a Laboratory object
lab.run_single(exp, [(lab.VAR('power'), np.arange(-30, 10, 10)), (lab.VAR('flux'), np.arange(0,20,0.1))], sweep_orders=[ExSwpRandom(1)])
```

The `sweep_orders=[ExSwpRandom(1)]` command ensures that the index 1 variable (i.e. `'flux'`) is now swept in a random order each time:

```python
lab.VAR("power").Value = -30
## Sweep all Flux values, but in a RANDOM order
lab.VAR("flux").Value = 15.7
# --- Get Data --- #
lab.VAR("flux").Value = 14.3
# --- Get Data --- #
...
lab.VAR("flux").Value = 9.8
# --- Get Data --- #
lab.VAR("flux").Value = 17.9
# --- Get Data --- #

lab.VAR("power").Value = -20
## Sweep Flux backwards
lab.VAR("flux").Value = 5.3
# --- Get Data --- #
lab.VAR("flux").Value = 13.9
# --- Get Data --- #
...
lab.VAR("flux").Value = 5.7
# --- Get Data --- #
lab.VAR("flux").Value = 3.2
# --- Get Data --- #

...
```

Note that the ordering is preserved in all other axis other than the specified index.


