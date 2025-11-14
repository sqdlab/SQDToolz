# Zurich Instruments

The products SHFQC, HDAWG and PQSC from Zurich Instruments integrate into *SQDToolz* via a light wrapper over LabOneQ objects. The objectives are:

- Let LabOneQ handle all interfacing with ZI products without software intervention from *SQDToolz*
- Have light wrappers that handle the objects and reinitialisation contracts to enable cold reloading

The following constructs exist to handle interfacing with the ZI products:

- [ZIQubit](#ziqubit)
- [SOFTqpu](#softqpu)
- [ZIACQ](#ziacq)

## ZIQubit

This wraps over the qubit objects (e.g. `TunableTransmonQubit`) provided by ZI (either in the `laboneq`, `laboneq-applications` or custom packages/classes). *SQDToolz* adopts these objects as they not only hold a useful set of qubit parameters (i.e. don't have to use `ExperimentSpecification` objects) but to also utilise ZI *workflows* to automate experiments. Note the following design decisions regarding its expected behaviour:

- The qubit's name in the ZI object is the same as this HAL's reference name
- The HAL can be reinitialised with different logical signal lines; this can be useful when rerouting to a different channel/port midway through the experiment without having to reinitialise and/or lose the calibrated qubit parameters
- If the HAL is reinitialised into a different qubit object type, then all calibrated qubit parameters are lost/reset
- Using `__getattr__`, `__setattr__` and `__dict__`, an engine is created to map local HAL attributes (compatible with cold reloading) onto the ZI qubit object (which ultimately holds the dictionary data of the qubit parameters)

## SOFTqpu

Although this is a general object used to house a network of qubits and couplings (can be multiple between any two qubits), it implements `ZIbase` to ensure that it can integrate with the ZI objects. Specifically, it has the ability to export a *QPU topology* object for use with the ZI *workflows*.

## ZIACQ

This is a light wrapper that must be supplied as the acquisition HAL in the `ExperimentConfiguration` object. It is there to:

- Handles parameters related to acquisition (such as `NumRepetitions` and `RepetitionTime`) and postprocessing (such as `AcquisitionMode`). A few of these parameters can be set to `'DEFAULT'` so that the experiment's default options (i.e. appropriately choosing the correct ones) can be chosen
- Handles the data acquisition and translation into the *SQDToolz* HDF5 format

It has an attribute `_cur_workflow` that is set to `None` when `init_instruments()` calls its `_set_current_config()`. It must be set by the `Experiment` object (after this function call) to some workflow module (e.g. `qubit_spectroscopy` from the *LabOneQ* applications library). The `get_data()` call then runs this workflow to extract the returned data.

## ExpZIqubit

This is written as a light wrapper to ZI experiment workflows that utilise ZI qubit and QPU objects.
