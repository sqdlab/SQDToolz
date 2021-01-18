# SQDTOOlz

This is a toolbox to control and run a experiments by synchronising AWGs and Digitizers via a Pulser device. This was designed to supersede UQTools, keeping simplicity, scalability and efficiency in check. It is a wrapper over Qcodes and has other key functionality such as timing control, pulse generation and shaping, data + configuration storage and retrieval, which are not present in Qcodes.

## Basic design overview:

The Main module has 2 part :

1. Qcodes: This has all the vendor level drivers for the instruments. Most instruments have pyVISA implementation, however DLL implementation is supported as well.

2. Timing + HIL : Timing is used accept different instrument objects and perform check on the order of operations. HIL or Hardware Interface Layer, is a wrapper class around each of the different instruments being used. Each instrument has it own wrapper class, which has additional information relevant to that specific instrument. The instrument class wrapper, are supposed to provide a unified template, which can be used to add new devices.

## Philosophy :

* Each measurement is required to be created and executed in a new experiment object.