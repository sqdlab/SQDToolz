# Defining Variables

`Variable` objects serve the following purposes:

- A container with a value that one can get/set
- Can link the value to instrument HAL parameters
- Its values are stored along with the experimental data and metadata
- The `ExperimentViewer` shows the values of all `Variable` objects

In general any variable can be accessed via the `Laboratory` object as follows:

```python
#Access the Variable object named "testVar"
lab.VAR("testVar")
```

To get or set the variable value, use the `Value` property:

```python
#Get the value of Variable object "testVar"
val = lab.VAR("testVar").Value

#Set the value of Variable object "testVar" to 9
lab.VAR("testVar").Value = 9
```

To actually define variables, one may select from the list of different variable types, each with different use cases:

- [`VariableInternal`](#variableinternal) - a dummy placeholder that simply stores a value internally
- [`VariableProperty`](#variableproperty) - a direct link to some object property (e.g. instrument parameter) useful when sweeping
- [`VariableSpaced`](#variablespaced) - sets the value of 2 other variables ensuring that they are spaced by some value.
- [`VariableDifferential`](#variabledifferential) - sets the values of two variables differentially so that the difference between the two variables equals the set value.

Note that the examples below utilise a `Laboratory` object called `lab`.

## VariableInternal

The `VariableInternal` object is a dummy placeholder that simply stores a value internally. The basic definition is simply the name and `Laboratory` object along with an optional initial value:

```python
#Define an dummy variable called "testVar"
VariableInternal("testVar", lab)

#Define an dummy variable called "testVar" with an initial value 9
VariableInternal("testVar", lab, 9)
```

**Use Case 1:** `VariableInternal` is to create a dummy variable used in **repeating an experiment**:

```python
#Repeating an experiment 100 times using a dummy variable

VariableInternal("dummy", lab)

exp = Experiment("VNA", lab.CONFIG('base'))
result = lab.run_single(exp, [(lab.VAR("dummy"), np.arange(0,100,1))])
``` 

**Use Case 2:** `VariableInternal` is just as a parameter store for post-processed values (one can track the value via the `ExperimentViewer` module):

```python
VariableInternal("cav-line-width", lab)

exp = ExpPeakScouterIQ('CavitySpec', lab.CONFIG('contMeas'), param_width=lab.VAR("cav-line-width"))
result = lab.run_single(exp, [(lab.VAR('cav_freq'), np.arange(4e9,8e9,1e6))])
```

## VariableProperty

The `VariableProperty` object is a direct link to some object proprety of a SQDToolz object held by [Laboratory](Laboratory.md). Thus, the basic definition is simply the name, `Laboratory` object, the object to which the variable is linked and the property to link:

```python
#Define an property variable called "testVar" and link it to the 'Frequency' property of the HAL object called "MWcav" 
VariableProperty("testVar", lab, lab.HAL("MWcav"), 'Frequency')
```

This is useful when sweeping instrument parameters in an experiment. For example, 


```python
#Link "cav_freq" to the 'Frequency' property of "MWcav" (a microwave source HAL)
VariableProperty("cav_freq", lab, lab.HAL("MWcav"), 'Frequency')

exp = ExpPeakScouterIQ('CavitySpec', lab.CONFIG('contMeas'), param_width=lab.VAR("cav-line-width"))
#Sweep the 'Frequency' property of "MWcav" via the "cav_freq" variable
result = lab.run_single(exp, [(lab.VAR("cav_freq"), np.arange(4e9,8e9,1e6))])
```

Note that `VariableProperty` does not store anything internally. Its `Value` is gotten/set directly from/upon the object property. Thus, for example, if it is linked to a HAL object's property, then the actual instrument parameter value will be queried and changed directly on interfacing with `Value`.

The compatible SQDToolz object types whose properties that one may link are:

- HAL
- WFMT
- VAR

Note that the third use-case is more niche and not recommended in general.

See also: [Sweeping AWG waveform parameters using VARs](AWG_VARs.md)

## VariableSpaced

There are cases where one wishes to set a parameter to a value while automatically setting a second parameter to the same value but spaced by some amount. The definition requires the name, `Laboratory` object, two variable objects and the spacing value:

```python
#Define a spacing variable for 2 variables "QubitFreq" and "MWpulseFreq" spaced at 100e6
VariableSpaced("testVarSpaced", lab, lab.VAR("QubitFreq"), lab.VAR("MWpulseFreq"), 100e6)
```

In the example above, setting a value to the variable `"testVarSpaced"` will set `"QubitFreq"` to said value and `"MWpulseFreq"` to `100e6` above:


```python
lab.VAR("testVarSpaced").Value = 5e6

#Now:
#   lab.VAR("QubitFreq").Value   = 5e6
#   lab.VAR("MWpulseFreq").Value = 5e6 + 100e6
```

This is useful when setting frequency parameters that require a sideband offset or a demodulation offset to be set simultaneously to another source. Note that this variable also has a sixth argument `negate_first`. In this case:

```python
VariableSpaced("testVarSpaced2", lab, lab.VAR("var1"), lab.VAR("var2"), 100e6, negate_first=True)
```

In the example above, it is set to `True` (default value is `False`). When setting the variable `"testVarSpaced2"`, `"var1"` will be set to the value while `"var2"` will be set to 100e6 minus the value:

```python
lab.VAR("testVarSpaced2").Value = 5e6

#Now:
#   lab.VAR("var1").Value   = 5e6
#   lab.VAR("var2").Value = 100e6 - 5e6
```




## VariableDifferential

When using differential signalling, one may have two variables linked to two entities (for example, the voltages on two different gate electrodes) with the intent on setting them differentially. The definition requires the name, `Laboratory` object, two variable objects upon which to set differentially:

```python
#Define a differential variable over two variables "voltA" and "voltB"
VariableDifferential("testVarDiff", lab, lab.VAR("voltA"), lab.VAR("voltB")):
```

In the example above, setting a value to the variable `"testVarDiff"` sets half the value to `"voltA"` and negative of the half-value will be set to `"voltB"`:

```python
lab.VAR("testVarDiff").Value = 4
#Now:
#   lab.VAR("voltA").Value = 2
#   lab.VAR("voltB").Value = -2

lab.VAR("testVarDiff").Value = -7
#Now:
#   lab.VAR("voltA").Value = -3.5
#   lab.VAR("voltB").Value = 3.5
```
