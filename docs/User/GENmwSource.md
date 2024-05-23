# HAL `GENmwSource` for Microwave Sources

The `GENmwSource` HAL manages microwave sources and is typically used as follows:

```python
import sqdtoolz as stz
#Initialise Laboratory object as lab
...

lab.load_instrument('src_sgs')
stz.GENmwSource("MWcavity", lab, 'src_sgs', 'RFOUT')

lab.HAL('MWcavity').Mode = 'Continuous'
lab.HAL('MWcavity').Power = 14.5
lab.HAL('MWcavity').Frequency = 8.1e9
lab.HAL('MWcavity').Output = False
```

Note that the `GENmwSource` HAL operates on a **per channel basis** and thus, the instantiation requires the instrument name (in YAML) and the RF output port name (being `'src_sgs'` and `'RFOUT'` in the above example). The relevant attributes are:

- `Mode` - output modes (if supported by the instrument) being: `'Continuous'`, `'PulseModulated'`, `'AmplitudeModulated'`, `'FrequencyModulated'`, `'PhaseModulated'`.
- `Power` - output power **given in dBm**.
- `Frequency` - output frequency **given in Hertz**.
- `Output` - if `True` the RF output is turned on.

The `'Continuous'` mode will output the microwave continuously. For the remaining modes where there are modulations on the output, the relevant attributes are:

- `Phase` - phase of the output. Only relevant when using `'PulseModulated'` mode
- `AmplitudeModDepth` - the amplitude modulation depth given as a percentage from 0 to 100. Only relevant when using `'AmplitudeModulated'` mode.
- `FrequencyModAmplitude` - the maximum frequency that can be deviated for the maximum input modulation frequency amplitude. Only relevant when using `'FrequencyModulated'` mode.
- `PhasePhaseModAmplitude` - the maximum phase that can be deviated for the maximum input modulation voltage amplitude. Only relevant when using `'PhaseModulated'` mode.

Note that the output is turned on and off automatically when running experiments. To [disable this](Exp_Overview.md), set the attribute `ManualActivation` to `True`.
