# Real-time Data Processing

Sometimes when acquiring a lot of data, the individual samples may not be of interest as much as the final processed value. Examples include:

- Acquiring raw sample data that needs to be digital IQ demodulated; only the demodulated data is of interest
- One would rather store the smaller filtered/downsampled/decimated data than the giant raw samples

In such cases, instead of running the analysis in post-processing, one may process the data in real-time as the data is acquired. Currently, the software supports real-time processing via:

- [Computer CPU](Proc_CPU_Overview.md)
- [Computer GPU]((Proc_GPU_Overview.md)) (for CUDA-enabled GPUs - otherwise, defaults to the CPU)

The processing is defined as a pipeline in which one may pick and choose the individual processing elements:

- [CPU processors](Proc_CPU_list.md)
- [GPU processors](Proc_GPU_list.md)
