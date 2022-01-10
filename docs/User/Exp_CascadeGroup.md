# Cascading and grouping multiple experiments

As noted [earlier](Exp_Overview.md), experiments can be declared and run with the results dumped into the single folder with the timestamp:

```python
exp = Experiment("Rabi", lab.CONFIG('AutoExp'))
#Run experiment without sweeping parameters:
result = lab.run_single(exp)
#Run experiment with sweeping parameters:
result = lab.run_single(exp, [(lab.VAR("wait_time"), np.arange(0,100e-9,10e-9))])
```

As shown above, one may sweep the experiment over a range of `Variable` objects. However, in the case of an automated experiment (for example, `Exp_Rabi`), such operations may not be permitted for it may interfere with the post-processing. In such a case, one may run a conventional loop:


```python
exp = ExpRabi('Rabi', lab.CONFIG('AutoExp'), lab.WFMT('Qubit_GE'), np.linspace(0,0.5,80), lab.SPEC('Qubit1'))

for m in range(10):
    result = lab.run_single(exp)
```

Although this works, it will create a separate folder for each experiment. This is not necessarily an issue, but consider a more complex case such as that when taking T1 statistics:

```python
expRabi = ExpRabi('Rabi', lab.CONFIG('AutoExp'), lab.WFMT('Qubit_GE'), np.linspace(0,0.5,80), lab.SPEC('Qubit1'))
expT1 = ExpT1GE('T1', lab.CONFIG('AutoExp'), lab.WFMT('Qubit_GE'), np.linspace(0,50e-6,50), lab.SPEC('Qubit1'))

for m in range(10):
    #Recalibrate Rabi frequency
    result = lab.run_single(expRabi)
    #Perform T1 experiment
    result = lab.run_single(expT1)
```

In this case, there would be a cascade of Rabi and T1 experiment folders. It would be ideal if all the folders were somehow grouped with a method to automatically combine all the individual experimental datasets for the convenience of further analysis. In summary, this page covers:

- Method to group a set of experiments into a single folder
- Method to sweep a bunch of experiments (e.g. Exp_Rabi) over a range of values on some `Variable` object
- Method to amalgamate individual datasets via `FileIODirectory`

## Placing multiple experiments into a single folder

Multiple experiments can be placed into a single folder via the grouping functions in the `Laboratory` class:

```python
expRabi = ExpRabi('Rabi', lab.CONFIG('AutoExp'), lab.WFMT('Qubit_GE'), np.linspace(0,0.5,80), lab.SPEC('Qubit1'))
expT1 = ExpT1GE('T1', lab.CONFIG('AutoExp'), lab.WFMT('Qubit_GE'), np.linspace(0,50e-6,50), lab.SPEC('Qubit1'))

lab.group_open("T1-statistics")
for m in range(10):
    #Recalibrate Rabi frequency
    result = lab.run_single(expRabi)
    #Perform T1 experiment
    resultT1 = lab.run_single(expT1)
lab.group_close()
```

The Rabi and T1 experiments will now be grouped in a single time-stamped folder with the name 'T1-statistics' as follows:

```
Experiment_Folder
---2022-01-10
      - 123201-T1-statistics
            - 123202-Rabi
            - 123330-T1
            - 123405-Rabi
            - 123427-T1
            ...
```

Note that calling `group_open` again will close the current group and start a new one; that is, it will not nest within the group. In addition, one should remember to call `group_close` (especially when killing experiments) to ensure that subequent experiments do not get created within the current grouping directory. All experiments of the same type within a grouped directory can be collated into a single dataset via the `FileIODirectory` class:

```python
#From path
leData = FileIODirectory(r'...\2022-01-10\123202-Rabi\123330-T1\data.h5')
#Or equivalently from the last result FileIOReader object returned from the experiment...
leData = FileIODirectory.fromReader(resultT1)

#The data and parameters are retrieved similar to FileIOReader - e.g. to get the array data:
arr = leData.get_numpy_array()
```

Note that in this case, the `FileIODirectory` collates all the T1 experiments into a single object in which the first array index of `arr` slices through the individual experiments. The `FileIODirectory` can be initialised by taking one of the experiments in the grouped directory; upon which, it finds all others with the same name. In the above example, this is done by either pointing it to an individual data file (e.g. like `123330-T1\data.h5` in the example) or any `FileIOReader` object returned by the `run_single` function (in the above example, this is the last one in the string of experiments).

## Sweeping experiments over a variable object

In the example shown in the previous section, grouped experiments were retrieved and indexed by the order in which they were performed in the directory. Now this section extends this concept for the case where the experiments are swept over some `Variable` objects. In doing so, the `FileIODirectory` class retrieves the experiments of the given type and slices the resulting array over the swept parameters instead of just the experiment number. Note that additionally, this sweeping functionality is useful when having to sweep automated experiments over some parameter.

Unlike normal for loops sweeping over a range of values, one sweeps over the generator functions embedded inside all `Variable` objects to let the engine know that the experiment is being swept:

```python
expRabi = ExpRabi('Rabi', lab.CONFIG('AutoExp'), lab.WFMT('Qubit_GE'), np.linspace(0,0.5,80), lab.SPEC('Qubit1'))
expT1 = ExpT1GE('T1', lab.CONFIG('AutoExp'), lab.WFMT('Qubit_GE'), np.linspace(0,50e-6,50), lab.SPEC('Qubit1'))

lab.group_open("T1-statistics")
#Sweep over a dummy variable
for cur_ind in lab.VAR('dummy').arange(10):
    #Recalibrate Rabi frequency
    result = lab.run_single(expRabi)
    #Perform T1 experiment
    resultT1 = lab.run_single(expT1)
lab.group_close()

#Sweep over the gate potentials V1 and V2
for cur_ind in lab.VAR('Pot_V1').linspace(0,1.0,20):
    for cur_ind in lab.VAR('Pot_V2').array([0.1,0.25,0.5,0.75]):
        #Recalibrate Rabi frequency
        result = lab.run_single(expRabi)
        #Perform T1 experiment
        resultT1 = lab.run_single(expT1)
lab.group_close()
```

When using `FileIODirectory`, it will slice the experiments over the values of `'Pot_V1'` and  `'Pot_V2'` before sweeping over the parameters within the individual experiment.

