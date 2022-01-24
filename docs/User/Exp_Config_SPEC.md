# Using ExperimentSpecification objects
TO BE FINISHED

The `ExperimentSpecification` object performs the following tasks:

- Records a list of key-value pairs - that is, each pair having a name and value
- The key-value pairs may have an attached target like some instrument HAL parameter
- When running an `ExperimentConfiguration` with attached `ExperimentSpecification` objects, all key-value pairs with a target are set to thereby override the values set by the `ExperimentConfiguration` object.

It specifically solves two issues:

- It stores a list of parameters in a logical grouping
- It acts as a store for an experimental parameter that is to override that stored in an `ExperimentConfiguration` snapshot

The issues it solves are further explained below along with the method the usage in code.

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

## Defining an Experiment Specification (Manually)

In the manual definition, the names of all parameters must be initialised manually. The object is initialised by given it a name and a `Laboratory` object:

```python
#Create an ExperimentSpecification object
ExperimentSpecification('Cavity', lab)

#Add a parameter to the SPEC 'Cavity'
lab.SPEC('Cavity').add('Line width', 1e6)
#Add a parameter to the SPEC 'Cavity' that links to the Frequency property of lab.HAL('MWcav')
lab.SPEC('Cavity').add('Line width', 1e6, lab.HAL('MWcav'), 'Frequency')
#Add a parameter to the SPEC 'Cavity' that links to the Variable of lab.VAR('MW')
lab.SPEC('Cavity').add('Line width', 1e6, lab.HAL('MWcav'), 'Frequency')
```

TO BE FINISHED

## Defining an Experiment Specification (via Template)


TO BE FINISHED
