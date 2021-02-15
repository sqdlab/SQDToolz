# SQDTOOLz

This is a toolbox to control and run a experiments by synchronising AWGs and Digitizers via a Pulser device. This was designed to supersede UQTools, keeping simplicity, scalability and efficiency in check. It is a wrapper over QCoDeS and has other key functionality such as timing control, pulse generation and shaping, data + configuration storage and retrieval, which are not present in QCoDeS.

## Install instruction:

```
pip install -e sqdtoolz
```

## Basic design overview:

The structure is as follows:

1. Laboratory - highest level object that holds experiment parameters, runs experiments and handles saving of data and experiment+instrument configurations

2. Experiment - an object when run will generate a set of input gates (e.g. to a qubit) while receiving output signals (e.g. qubit readout). The language here is generic and agnostic to the underlying implementation.

3. Experiment-Configuration - sets up the trigger relations between the HAL instruments and handles the translations of generic pulse sequences into the actual AWG channels (e.g. mapping a qubit gate-sequence onto two AWG channels when using IQ modulation).

4. HAL - the Hardware-Abstraction-Layer is used to package raw instruments (e.g. DDG, AWG and ACQ instruments) for use in describing trigger relationships and to send commands (e.g. programming waveforms) in an instrument-agnostic manner (i.e. the interface to command different AWGs is done so via the same object properties and interface functions)

5. QCoDeS-Drivers: This has all the vendor level drivers for the instruments. Most instruments have pyVISA implementation, however DLL implementations are also supported.

## Philosophy :

* Each measurement is required to be created and executed in a new experiment object.