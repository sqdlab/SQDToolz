# Automated experiments

The results from an experiment are typically post-processed (e.g. fitting a Rabi experiment to a sinusoidal decay to extract the Rabi frequency). Although this can be done manually in the experiment scripts, a cleaner approach a repetitive experiment is to:

- Override the `Experiment` class' functions to write a custom experiment that has a well-tested post-processing sub-routine
- The post-processing should also automatically set the values of desired parameters (whether it is a VAR or a SPEC) based on the results of the given experiment (e.g. setting the cavity resonance frequency or the Rabi frequency)

Details of writing custom `Experiment` classes are given in the developer documentation. This page will give a usage summary of the currently written classes.

## Rabi experiment (ExpRabi)

TBW
