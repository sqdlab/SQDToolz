# SQDToolz

This is a toolbox to control instruments to run a general lab experiments. This was designed to supersede *UQTools*, keeping simplicity, scalability and efficiency in check. It currently uses QCoDeS to communicate with the instruments, while providing higher level functionality such as timing control, pulse generation, automatic parameter updates and data/configuration storage.

There are two classes of documentation provided for this stack:

- [User documentation](docs/User/Readme.md)
- [Developer documentation](docs/Developer/Readme.md)


## Installation instructions:

The installation is done by cloning the repository and running the setup file via pip. Note that it is done in the editable mode so that one may modify the stack and push changes to GIT without upsetting the pip package manager. Two possible modes are given here depending on whether one uses Anaconda or normal Python:

### Using Anaconda Python

Run Anaconda prompt and run the following command to create an environment (in this example, the name is sqdtoolz_env):

```
conda create -n sqdtoolz_env python=3.9
```

Now activate the environment:

```
activate sqdtoolz
```

Now choose a folder to house the SQDToolz stack (idea is to create an editable folder such that the code can be modified and pushed without upsetting the pip package manager). Once navigating to this folder, run the usual GIT clone:

```
cd C:/Users/....../myFolder/
git clone https://github.com/sqdlab/sqdtoolz.git
```

Now there is a sqdtoolz folder in the current directory. Do not enter this new folder. Simply run:

```
pip install -e sqdtoolz
```

This should install all required dependencies.

### Using Normal Python

Choose a sensible folder in which to install the virtual environment. Then run the usual command:

```
python3 -m venv name_of_venv
```

Now activate the environment in the usual manner (i.e. run the script `activate` in the /Scripts folder inside the new virtual environment folder) in command line. Now choose a different folder (i.e. not in the virtual environment folder) to house the SQDToolz folder (idea is to create an editable folder such that the code can be modified and pushed without upsetting the pip package manager). Once navigating to this folder, run the usual GIT clone:

```
cd C:/Users/....../myFolder/
git clone https://github.com/sqdlab/sqdtoolz.git
```

Now (noting that the command line is still inside the active virtual environment), run:

```
pip install -e sqdtoolz
```
This should install all required dependencies.

### Updating new required packages

Just log into the virtual environment, navigate to the sqdtoolz folder (where `requirements.txt` is stored) and then run:

```
python -m pip install -r requirements.txt
```

## Basic design overview:

The stack is structured as follows:

1. Laboratory - highest level object that holds experiment parameters, runs experiments and handles saving of data and experiment+instrument configurations

2. Experiment - an object when run will generate a set of input gates (e.g. to a qubit) while receiving output signals (e.g. qubit readout). The language here is generic and agnostic to the underlying implementation.

3. Experiment-Configuration - sets up the trigger relations between the HAL instruments and handles the translations of generic pulse sequences into the actual AWG channels (e.g. mapping a qubit gate-sequence onto two AWG channels when using IQ modulation).

4. HAL - the Hardware-Abstraction-Layer is used to package raw instruments (e.g. DDG, AWG and ACQ instruments) for use in describing trigger relationships and to send commands (e.g. programming waveforms) in an instrument-agnostic manner (i.e. the interface to command different AWGs is done so via the same object properties and interface functions). The HAL abstracts the specific device into a particular type; this standardisation enables easy browsing of parameters. For example, given two microwave sources from Tektronix and Keysight, both sources will use the associated HAL object `GENmwSource` to ensure a uniform API when handling said objects (e.g. to set the output frequency, one just sets the universal `Frequency` property of the `GENmwSource` object).

5. QCoDeS-Drivers: This has all the vendor level drivers for the instruments. Most instruments have pyVISA implementation, while others use local APIs (e.g. HiSLIP or some DLL).

## Overview

Basic workflow involves:

- A `Laboratory` object is created for a given experimental run. This specifies the output directory.
- Devices that may be used are specified in the YAML (as per QCoDeS).
- Devices desired for a given experimental run are loaded from the YAML and then housed inside HAL objects
- Devices desired for a particular experiment are loaded into an `ExperimentConfiguration` object to store all HAL parameters and device settings (e.g. waveforms, frequencies, powers etc.) and trigger relationships for the timing diagram.
- When running an experiment (whether it is a default one or a custom one), the given `ExperimentConfiguration` object is used to instantiate the `Experiment` object.

When the experiment finishes, it creates a folder with the date and time-stamp. Said folder includes:

- At least, one HDF5 file with the output data (usually updated in real-time to enable live-plotting)
- `timing_diagram.png` - the timing diagram of instruments used in the current experiment highlighting the trigger relationships and the time-frames win which instruments output or acquire signals.
- `laboratory_parameters.txt` - names and values of currently defined `Variable` objects in the current experimental run
- `laboratory_configuration.txt` - a full dump of all HAL-level instrument parameters. This is used to easily browse the instrument parameters (e.g. frequency, power, sample-rates etc.). In fact, the `ExperimentViewer` UI uses this file to easily compare instrument parameters between two different experiments.
- `instrument_configuration.txt` - a QCoDeS instrument parameter dump. Used as a last resort for it is heavily obfuscated with the device-specific parameters.

Note that the folder may also include other files such as fitted plots if the derived `Experiment` object outputs said files. Other noteworthy features include:

- Flexible waveform generation engine that includes auto-compression that utilises the sequencing functionality (in supported AWGs) to lower the waveform memory usage.
- Live `ExperimentViewer` module that shows the current state of all HAL-level parameters in the experiment. It is useful to help ensure that the desired instruments are in the correct states during the experiment. It can be run via `lab.open_browser()`.
- Live plotting engine when using SQDViz.
- Structural types supported via `ExperimentSpecification`. For example, a qubit type can hold parameters such as its drive frequency, optimal drive amplitude/time for Pauli-X Gates, T1 time etc.

It should be noted that experiments can automatically interface with parameters (either inside `ExperimentSpecification` or normal `Variable` objects). For example, a Rabi experiment will automatically fit the resulting oscillations to update the currently optimal drive amplitude and time for Pauli-X gates on a given qubit. Thus, one may run cascades of experiments in an automated sequence. A usual sequence might be to run a Rabi experiment (update the currently optimal tipping $\pi/2$ amplitude), run a more optimal Ramsey experiment (update the detuning frequency) and finally run a T1 experiment with the optimal qubit drive parameters. This three-experiment combination could be run in a loop with all **parameters being updated and saved automatically in real-time**. Using the experiment grouping functionality, one may group all said experiments into a single time-stamped folder with the data IO retrieval functionality present to automatically amalgamate all results across multiple experiments (e.g. this is useful when trying to collate all T1 values when generating T1-statistics).

