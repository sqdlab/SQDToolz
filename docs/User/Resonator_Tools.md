# Resonator Tools for power-sweeps of CPW resonators

The class contains functions useful for data retrieval, analysis, sorting and plotting of CPW transmission data. In general, the class does the following actions:

1. Saves important experimental data in an initialised `ResonatorPowerSweep` object.
2. Retrieves data from a specified directory (across multiple files) using `ResonatorPowerSweep.import_data` (using `Utilities.FileIO.FileIOReader`).
3. Fits S21 transmission data for a notch port using [resonator_tools](https://github.com/sebastianprobst/resonator_tools), extracting $Q_i$, $Q_c$, photon number $\langle n \rangle$, associated uncertainties, and other important measured values (more fitting routines will be added). This whole routine is contained within `ResonatorPowerSweep.do_circlefit`. Sub-routines within `ResonatorPowerSweep.do_circlefit`include:
   1. `ResonatorPowerSweep.n_ph_calculator` for calculating photon number from power
   2. `ResonatorPowerSweep.fit_data_to_sorted_dataframe` for sorting and filtering of data
   3. `ResonatorPowerSweep.get_frequency_bins` to sort measurements into frequency bins (i.e. per resonator)
4. Plots data, and fits a TLS-loss-model to allow extraction of the TLS loss tangent (`ResonatorPowerSweep.plotBokeh_n_ph` for Bokeh plotting, `ResonatorPowerSweep.plotMpl_n_ph` for Matplotlib plotting). The fitting routine is contained in the function `ResonatorPowerSweep.TLS_fit`, where the [model from Earnest et. al](https://iopscience.iop.org/article/10.1088/1361-6668/aae548) is fitted, 
   
   $$\tan\delta=\frac{1}{Q_i}=F\tan\delta_{TLS,0}\frac{\tanh\left(\frac{\hbar\omega}{2 k_B T}\right)}{\left(1+\left(\frac{\langle n \rangle}{n_c}\right)\right)^\beta} + \frac{1}{Q_{HP}},$$ 
   
   where the fit parameters are the filling-factor-scaled TLS-loss-tangent $F\tan\delta_{TLS,0}$, the critical photon number $n_c$ (above which TLS-resonator interaction saturates), the power-independent (high-power) loss $Q_{HP}$, and a fitting parameter $\beta$.
5. Saves all fitted and calculated data to a text file.

### Example usage

This script will import all valid `data.h5` files contained within our directory `data_path = "/path/to/data/folder/"`. Set the sample name and measurement temperature upon initialisation, as well as a `power_dict` (optional), which is used to assign attenuations to measurements based on their file naming. For example, files found in `data_path` containing `lowPower` (not case sensitive) in their path will be assigned -120dB attenuation. The `"default"` argument is used for all files containing no match to other keywords. 

Data is then imported, with an additional -12 dB of attenuation added across the board. A single file from the `data_path`, `"bad-file-name-here"` is ignored upon import.

The imported data 


```python
from sqdtoolz.Utilities.ResonatorTools import ResonatorPowerSweep

chunk = ResonatorPowerSweep(data_path = "/path/to/data/folder/",
                            sample_name = "My_Sample",
                            temperature = 24.7e-3,
                            power_dict= {"lowPower" : -120, 
                                         "default" : -70
                                         },
                            )
chunk.import_data(additional_attenuation=-12, 
                  files_to_ignore=["bad-file-name-here"]
                  )
chunk.do_circlefit()
chunk.plotMpl_n_ph()
```


### Example data structure

The intended data structure for this class is shown below, where the data path would be set as `data_path = "my_data_folder"`. The VNA power used during the measurement is extracted from the `"experiment_configurations.txt"` file in each valid folder. Data extracted from the folder `Sample1_lowPower` will have extra attenuation added to the measurements according to the `power_dict`.

```
my_data_folder
├── Sample1
│   ├── 144753-Measurement
│   │   ├── data.h5
│   │   ├── experiment_configurations.txt
│   │   ├── experiment_parameters.txt
│   │   ├── instrument_configuration.txt
│   │   ├── laboratory_configuration.txt
│   │   └── laboratory_parameters.txt
│   └── 144812-Measurement
│       ├── data.h5
│       ├── experiment_configurations.txt
│       ├── experiment_parameters.txt
│       ├── instrument_configuration.txt
│       ├── laboratory_configuration.txt
│       └── laboratory_parameters.txt
└── Sample1_lowPower
    ├── 003045-Measurement
    │   ├── data.h5
    │   ├── experiment_configurations.txt
    │   ├── experiment_parameters.txt
    │   ├── instrument_configuration.txt
    │   ├── laboratory_configuration.txt
    │   └── laboratory_parameters.txt
    └── 014232-Measurement
        ├── data.h5
        ├── experiment_configurations.txt
        ├── experiment_parameters.txt
        ├── instrument_configuration.txt
        ├── laboratory_configuration.txt
        └── laboratory_parameters.txt
```
