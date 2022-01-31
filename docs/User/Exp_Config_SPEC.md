# Using ExperimentSpecification objects

The `ExperimentSpecification` object performs the following tasks:

- Records a list of key-value pairs - that is, each pair having a name and value
- The key-value pairs may have an attached target like some instrument HAL parameter
- When running an `ExperimentConfiguration` with attached `ExperimentSpecification` objects, all key-value pairs with a target are set to thereby override the values set by the `ExperimentConfiguration` object.

It specifically solves two issues:

- It stores a list of parameters in a logical grouping
- It acts as a store for an experimental parameter that is to override that stored in an `ExperimentConfiguration` snapshot

The issues it solves are further explained below along with the method the usage in code:

- [Issues](#issues)
    - [Logical grouping](#logical-grouping)
    - [Overriding the ExperimentConfiguration](#overriding-the-experimentconfiguration)
- [Manually defining and accessing Experiment Specifications](#manually-defining-and-accessing-experiment-specifications)
- [Defining an Experiment Specification via a template](#defining-an-experiment-specification-via-a-template)

## Issues

Before diving into the `ExperimentSpecification` object, it is useful to consider the two main cases in detail.

### Logical grouping

This is straightfoward when considering more complex experiments. For the same reason structured types exist in many programming languages, the `ExperimentSpecification` object provides a more compact representation of a repeated set of parameters compared to individual [`Variable`](Var_Defns.md) objects. For example, a Qubit specification could perhaps store the Rabi frequency, the X-gate time, the X-Gate amplitude etc. Although a set of `Variable` object could store the same information across multiple `Variable` objects, it makes it unweildy when passing information on different qubits. It would also makes programming of automated experiments more elegant as the property names for a given qubit will be uniform.

The method to create a specification template is explained later below.

### Overriding the ExperimentConfiguration

Consider the following use-case:

1. The configuration `lab.CONFIG('rabi')` is initialised so that the `Frequency` parameter of `lab.HAL('MWcav')` is set to `7e9`. The 7GHz corresponds to the cavity resonance frequency.
2. A cavity spectroscopy is done and the resonance frequency is found to be `7.5e9`.
3. When running an experiment with `lab.CONFIG('rabi')`, it will set the cavity frequency (that is, `lab.HAL('MWcav').Frequency`) back to `7e9`.

One could remember to reinitialise/update `lab.CONFIG('rabi')` after finding the new cavity frequency, but that is cumbersome. The `ExperimentSpecification` object enables an elegant and logical override to the values stored in the `ExperimentConfiguration` object.

## Manually defining and accessing Experiment Specifications

In the manual definition, the names of all parameters must be initialised manually. The object is initialised by given it a name and a `Laboratory` object:

```python
#(A) - Create an ExperimentSpecification object called 'Cavity'
ExperimentSpecification('Cavity', lab)

#(B) - Add a parameter to the SPEC 'Cavity'
lab.SPEC('Cavity').add('Line width', 1e6)
#(C) - Link the parameter 'Line width' in the SPEC 'Cavity' to a voltage output lab.HAL('voltLabel').Voltage
lab.SPEC('Cavity').set_destination('Line width', lab.HAL('voltLabel'), 'Voltage')

#(D) - Add a parameter to the SPEC 'Cavity' that links to the Frequency property of lab.HAL('MWcav')
lab.SPEC('Cavity').add('Cav Frequency', 1e9, lab.HAL('MWcav'), 'Frequency')

#(E) - Add a parameter to the SPEC 'Cavity' that links to the Variable of lab.VAR('MWpwr')
lab.SPEC('Cavity').add('Cav Power', -20, lab.VAR('MWpwr'))
```

The code above shows different methods to link `ExperimentSpecification` parameters to object properties or variables in the engine:

- (A) - The `ExperimentSpecification` object is initialised by registering the SPEC name `'Cavity'` into a `Laboratory` object called `lab`.
- (B) - The SPEC object can be accessed via `lab.SPEC('Cavity')`. A parameter called `'Line Width'` is created here via the `add` function and set to `1e6`.
- (C) - The parameter `'Line Width'` is simply stores a value unless it is given a destination. Here `set_destination` is used to link to the `Voltage` property in the HAL object `lab.HAL('voltLabel')`. When running an experiment, this destination is set with the value (currently `1e6`), thereby overriding any value stored in the `ExperimentConfiguration` object.
- (D) - Instead of using the `set_destination` function, one may just pass the destination parameters onto the `add` function.
- (E) - When setting the destination to a `Variable` object, the default property (thereby the variable value) that is set is `Value` (see the [article on Variables](Var_Defns.md) for further details). Thus, one does not need to pass on the final property argument.

To edit the value of the `ExperimentSpecification` parameter (e.g. either manually or via an automated experiment that sets it on running some post-processing), the syntax is as follows:

```python
lab.SPEC('Cavity')['Line Width'].Value = 7e6
```

Note that the syntax uses square brackets to illustrate that it is like a dictionary key. Nonetheless, its value is manipulated via its `'Value'` property to keep it in line with the manipulation of `Variable` objects (see the [article on Variables](Var_Defns.md) for further details).

## Defining an Experiment Specification via a template

When using experiment specifications to represent object types (e.g. encapsulating qubit characteristics for use in a T1 experiment), a set of standardised keys become necessary. The templating mechanism enables a standard set of names as well as a method to automatically initialise the specification parameters (that is, not having to keep using the `add` function like in the previous section). The initialisation and typical usage is given by:

```python
#Create an ExperimentSpecification for QubitAnc using the Qubit template
ExperimentSpecification('QubitAnc', lab, 'Qubit')

#Link the 'Frequency GE' property in 'QubitAnc' to the 'Frequency' property on the source MWqubit1
lab.SPEC('QubitAnc').set_destination('Frequency GE', lab.HAL('MWqubit1'), 'Frequency')

#Set the 'Frequency GE' property in 'QubitAnc' to 5.9GHz for use in following experiments
lab.SPEC('QubitAnc')['Frequency GE'].Value = 5.9e9
```

Note that setting the destination of all parameters is not necessary. For example, `'GE X-Gate Time'` parameter in the `'Qubit'` template is intended to just be a stored value. The value can be read in automated experiments like `ExpRamseyGE` and used to set the appropriate lengths for the tipping and untipping pulses. However, it may be useful to link properties that relate to hard experimental parameters or variables; like `'Frequency GE'` being linked to `lab.HAL('MWqubit1').Frequency` in the example above.

To list the available templates, use the static `list_SPEC_templates` function:

```python
#List all available templates
ExperimentSpecification.list_SPEC_templates()

#List all available templates and all parameters within them along with the initial values:
ExperimentSpecification.list_SPEC_templates(True)
```
