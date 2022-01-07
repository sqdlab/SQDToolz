# Sweeping parameters in experiments

Experiments can be run while sweeping the value of `Variable` objects over a list of values:

- The engine first sets the variable value to the first value in the list after which, data is then gathered. This sequence repeats for all values in the list.
- Each sweeping parameter is given as a tuple of: (`Variable` object, numpy array of values)

Example syntax of a sweeping experiment is shown below (assuming `lab` is the `Laboratory` object):


``` python
#Create experiment object (it's temporary and not stored in lab)
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
