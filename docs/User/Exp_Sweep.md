# Sweeping parameters in experiments

Experiments can be run while sweeping the value of `Variable` objects over a list of values:

- The engine first sets the variable value to the first value in the list after which, data is then gathered. This sequence repeats for all values in the list.
- Each sweeping parameter is given as a tuple of: (`Variable` object, numpy array of values) - except for the case where one wishes to sweep a one-many parametric set as discussed later below.

This article covers:
- [Basic Sweeps](#basic-sweeps)
- [One-Many Sweeps](#one-many-sweeps)
- [Changing the sampled order in sweeps](#changing-the-sampled-order-in-sweeps)


## Basic sweeps

Example syntax of a sweeping experiment is shown below (assuming `lab` is the `Laboratory` object):


``` python
#Create experiment object (it's temporary and not stored in lab) using configuration 'AutoExp'
exp = Experiment("Rabi", lab.CONFIG('AutoExp'))
#Run experiment with one sweeping parameter:
result = lab.run_single(exp, [(lab.VAR("wait_time"), np.arange(0,100e-9,10e-9))])
#Run experiment with two sweeping parameters:
result = lab.run_single(exp, [ (lab.VAR("wait_amps"), np.arange(0,0.5,0.01)), (lab.VAR("wait_time"), np.arange(0,100e-9,10e-9)) ])
```

Note that when doing multidimensional sweeps, the right-most parameters are swept first. For example consider the sweep:
```python
lab.run_single(exp, [ (lab.VAR("wait_amps"), np.array([10,20])), (lab.VAR("wait_time"), np.array([1,2,3])) ])
```

The experiment sequence (on interleaving the data acquisition) will be:

```python
lab.VAR("wait_amps").Value, lab.VAR("wait_time").Value = (10, 1)
# --- Get Data --- #
lab.VAR("wait_amps").Value, lab.VAR("wait_time").Value = (10, 2)
# --- Get Data --- #
lab.VAR("wait_amps").Value, lab.VAR("wait_time").Value = (10, 3)
# --- Get Data --- #
lab.VAR("wait_amps").Value, lab.VAR("wait_time").Value = (20, 1)
# --- Get Data --- #
lab.VAR("wait_amps").Value, lab.VAR("wait_time").Value = (20, 2)
# --- Get Data --- #
lab.VAR("wait_amps").Value, lab.VAR("wait_time").Value = (20, 3)
# --- Get Data --- #
```

This is important when sweeping parameters that may be susceptible to drift; in which case, one may wish to sweep over that parameter first. Finally note that the behaviour of the default experiment is to store the data on every acquisition call in between sweeping iterations (thus, enabling live-plotting functionality).


## One-Many sweeps

Consider the case where along one of the sweeping axes, one wishes to set many variables over every sweeping step. For example:

- Take parameters A1, P1, A2, P2
- The parameters are to be swept such that (A1=1,P1=0,A2=3,P2=-4) in the first step, (A1=4,P1=-3,A2=2,P2=-2) in the second step etc.

This is technically a one-dimensional indexing in which each index is setting 4 parameters as per some prescribed set of tuples. In this case, the parameter is given as a different tuple to that from the previous case:

- Tuple is: (Name of this sweeping variable, list of `Variable` objects, numpy array of values)
- The name must be unique across all other variables in this sweep
- The numpy array is a 2D N x V array in which V is the number variables to set and N is the number of steps in this parametric sweep

For example, consider:

``` python
#Create experiment object (it's temporary and not stored in lab) using configuration 'AutoExp'
exp = Experiment("Rabi", lab.CONFIG('AutoExp'))
#Run experiment with one sweeping parameter:
result = lab.run_single(exp, [('gateSet', [lab.VAR("A1"), lab.VAR("P1"), lab.VAR("A2"), lab.VAR("P2")], np.array([[1,0,3,-4], [4,-3,2,-2]]))])
```

This is equivalent to the execution:

```python
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (1,0,3,-4)
# --- Get Data --- #
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (4,-3,2,-2)
# --- Get Data --- #
```

Consider another example:

``` python
#Create experiment object (it's temporary and not stored in lab) using configuration 'AutoExp'
exp = Experiment("Rabi", lab.CONFIG('AutoExp'))
#Run experiment with two sweeping parameters:
result = lab.run_single(exp, [ (lab.VAR("wait_amps"), np.arange(0,0.3,0.1)), 
                                ('gateSet', [lab.VAR("A1"), lab.VAR("P1"), lab.VAR("A2"), lab.VAR("P2")], np.array([[1,0,3,-4], [4,-3,2,-2]])) ])
```

This is equivalent to the execution:

```python
lab.VAR("wait_amps").Value = 0
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (1,0,3,-4)
# --- Get Data --- #
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (4,-3,2,-2)
# --- Get Data --- #

lab.VAR("wait_amps").Value = 0.1
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (1,0,3,-4)
# --- Get Data --- #
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (4,-3,2,-2)
# --- Get Data --- #

lab.VAR("wait_amps").Value = 0.2
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (1,0,3,-4)
# --- Get Data --- #
lab.VAR("A1").Value, lab.VAR("P1").Value, lab.VAR("A2").Value, lab.VAR("P2").Value = (4,-3,2,-2)
# --- Get Data --- #
```

## Changing the sampled order in sweeps

TBW
