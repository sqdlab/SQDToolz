# SQDTOOlz

This is a toolbox to control AWGS, Pulser, Digitizer, etc device used in measurement. This was designed to superseed UQTools, keeping simplicity, scalability and efficiency in check. It is a wrapper over Qcodes and has other key functionality such as timing control, pulse generation and shaping, data + configuration storage and reterival, which are not present in Qcodes.

## Baisc design overview:

The Main module has 2 part :

    1. Qcodes: This has all the vendor level drivers for the instruments. Most intruments have pyVISA implementation, however DLL implementation is supported as well.

    2. Timing + HIL : Timing is used accept different instrument objects and perform check on the order of operations. HIL or Hardware Interface Layer, is a wrapper class around each of the different intruments being used. Each intrument has it own wapper class, which has additional information relevant to that specific instrument. The instrument class wrapper, are supposed to provide a unified template, which can be used to add new devices.

## Philosophy :

* Each measurment is required to be created and executed in a new experiment object.