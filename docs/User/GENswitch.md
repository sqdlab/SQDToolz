# HAL `GENswitch` for Switches

The `GENswitch` HAL manages switches typically used as follows:

```python
import sqdtoolz as stz
#Initialise Laboratory object as lab
...

lab.load_instrument('sw_rpi')
stz.GENswitch('sw_rpi', lab, 'sw_rpi')

lab.HAL('sw_rpi').Position = "P1"
```

The `GENswitch` HAL simply sets the position of a given switch (whether it is over Ethernet or a serial COM port). The switch positions are typically given as `'P1'`, `'P2'` etc. for the given switch positions. Some special switches (like the [custom qubit control and readout box](CustomDevices/BoxIQmod.md)) may use other labels like `'Pmeas'` and `'Pmix'`. If unsure just use the `get_possible_contacts` function to query the possible switch states:

```python
lab.HAL('sw_rpi').get_possible_contacts()
```
