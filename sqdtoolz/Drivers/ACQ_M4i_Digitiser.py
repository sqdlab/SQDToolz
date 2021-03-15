import scipy
import logging
import numpy as np
from qcodes import validators as vals, ManualParameter, ArrayParameter
# from qcodes.instrument_drivers.sqdlab.ADCProcessorGPU import TvModeGPU
from sqdtoolz.Drivers.Dependencies.Spectrum.M4i import M4i
import sqdtoolz.Drivers.Dependencies.Spectrum.pyspcm as spcm
from qcodes.instrument.base import Instrument
import qcodes
import gc

class ACQ_M4i_Digitiser(M4i):
    class DataArray(ArrayParameter):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, snapshot_value=False, **kwargs)
            self.get = self.get_raw       
            
        def get_raw(self):
            if 'singleshot' in self.name:
                self.instrument.processor.singleshot(True)
                if 'time_integrat' in self.name:
                    self.instrument.processor.enable_time_integration(True)
                else:
                    self.instrument.processor.enable_time_integration(False)
                data = self.instrument.get_data()
                self.shape = data.shape
            else:
                self.instrument.processor.singleshot(False)
                data = self.instrument.get_data()
                self.shape = data.shape
            gc.collect()
            return data            

    def __init__(self, name, cardid='spcm0', **kwargs):
        super().__init__(name, cardid, **kwargs)

        ###########################################################
        #Default digitizer setup (one analog, one digital channel)#
        self.clock_mode.set(spcm.SPC_CM_EXTREFCLOCK)
        self.reference_clock.set(10000000)#10 MHz ref clk
        self.sample_rate.set(500000000) #500 Msamples per second
        assert self.sample_rate.get() == 500000000, "The digitizer could not be acquired. \
                                                It might be acquired by a different kernel."
        self.set_ext0_OR_trigger_settings(spcm.SPC_TM_POS, termination=0, coupling=0, level0=500)
        self._trigger_edge = 1
        self.multipurpose_mode_0.set('disabled')
        self.multipurpose_mode_1.set('disabled')
        self.multipurpose_mode_2.set('disabled')
        self.enable_channels(spcm.CHANNEL0 | spcm.CHANNEL1) # spcm.CHANNEL0 | spcm.CHANNEL1
        self.num_channels = 2   #!!!!!CHANGE THIS IF CHANGING ABOVE
        self.set_channel_settings(1, mV_range=1000., input_path=1, 
                                termination=0, coupling=1)
        self.set_channel_settings(0, mV_range=1000., input_path=1, 
                                termination=0, coupling=1)
        ###########################################################

        self.override_card_lock = False
        
        self.add_parameter(
            'samples', ManualParameter, 
            label='Number of samples per trigger.', 
            vals=vals.Multiples(divisor=16, min_value=32))
        self.samples(2048)

        self.add_parameter(
            'channels',
            label='Number of channels',
            set_cmd=self._set_channels,
            vals=vals.Ints(1,2), initial_value=1)

        self.add_parameter(
            'segments',
            set_cmd=self._set_segments,
            label='Number of Segments',
            vals=vals.Ints(0,2**28), initial_value=1,
            docstring="Number of segments.\
                       Set to zero for autosegmentation.\
                       Connect the sequence start trigger to X0 (X1) for channels 0 (1) of the digitizer.")
    
    @property
    def NumSamples(self):
        return self.samples()
    @NumSamples.setter
    def NumSamples(self, num_samples):
        self.samples(num_samples)

    @property
    def SampleRate(self):
        return self.sample_rate.get()
    @SampleRate.setter
    def SampleRate(self, frequency_hertz):
        self.sample_rate.set(frequency_hertz)

    @property
    def NumSegments(self):
        return self.segments()
    @NumSegments.setter
    def NumSegments(self, num_segs):
        self.segments(num_segs)

    @property
    def TriggerInputEdge(self):
        return self._trigger_edge
    @TriggerInputEdge.setter
    def TriggerInputEdge(self, pol):
        self._trigger_edge = pol
        if self._trigger_edge == 1:
            self.set_ext0_OR_trigger_settings(spcm.SPC_TM_POS, termination=0, coupling=0, level0=500)
        else:
            self.set_ext0_OR_trigger_settings(spcm.SPC_TM_NEG, termination=0, coupling=0, level0=500)

    def _set_segments(self, segments):
        if segments == 0:
            # use autosegmentation. Assuming X0 is the sequence start trigger.
            # ADC input has one marker, which indicates sequence start
            self.multipurpose_mode_0.set('digital_in')
            self.processor.unpacker.markers.set(1)
            self.processor.sync.method.set('all')
            self.processor.sync.mask.set(0x01)
            logging.warning("Autosegmentation enabled. The number of acquisitions is \
                            set to number of averages in total. Number of acquisitions \
                            per segment will be averages//segments")
        elif segments == 1:
            # only one segment. Not checking for sequence start trigger
            self.multipurpose_mode_0.set('disabled')
        else:
            # setting number of segments to specific value.
            # Assuming X0 is the sequence start trigger.
            self.multipurpose_mode_0.set('digital_in')

    def _set_channels(self, num_of_channels):
        if num_of_channels == 1:
            self.enable_channels(spcm.CHANNEL0) # spcm.CHANNEL0 | spcm.CHANNEL1
        if num_of_channels == 2:
            self.enable_channels(spcm.CHANNEL0 | spcm.CHANNEL1) # spcm.CHANNEL0 | spcm.CHANNEL1
        self.num_channels = num_of_channels

    def _set_sample_rate(self, rate):
        self.sample_rate.set(rate)
        new_rate = self.sample_rate.get()
        logging.warning(f"Cannot set sampling rate to {rate}, it is set to {new_rate} instead")

    def get_data(self):
        '''
        Gets processed data from the GPU. Processing involves gathering data and passing it through TvMode
        '''
        # segments = self.segments()
        # blocksize = min(segments*2**11, segments*1)#2**28//2**int(np.ceil(np.log2(m4idigi.samples.get())))
        # if segments*1%blocksize == 0:
        #     blocks = segments*1//blocksize
        # else:
        #     blocks = 1
        #     logging.warn('Only acquiring {} acquisitions. \
        #     Make sure averages is divisible by {} to acquire the correct number.'.format(blocksize//segments, blocksize//segments))

        final_arr = [np.array(x) for x in self.multiple_trigger_fifo_acquisition(self.NumSegments, self.NumSamples, 1)]
        #Concatenate the blocks
        final_arr = np.concatenate(final_arr)
        return np.array([final_arr[:,:,m] for m in range(self.num_channels)])

def runme():
    new_digi = ACQ_M4i_Digitiser("test")
    new_digi.segments(2)#3 * (2**26))
    new_digi.samples(256)#2**8+2**7)
    
    # term = new_digi._param32bit(30130)
    # term = new_digi.termination_1()
    # new_digi.snapshot()

    a = new_digi.get_data()

    #a = [print(np.array(x)) for x in new_digi.multiple_trigger_fifo_acquisition(3*2**26,384,2**11)]

    # assert (num_of_acquisitions*self.samples.get()%4096 == 0) or (num_of_acquisitions*self.samples.get() in [2**4, 2**5, 2**6, 2**7, 2**8, 2**9, 2**10, 2**11]), "The number of total samples requested to the card is not valid.\nThis must be 16, 32, 64, 128, 256, 512, 1k ,2k or any multiple of 4k.\nThe easiest way to ensure this is to use powers of 2 for averages, samples and segments, probably in that order of priority."
    s=0
    print("done")

if __name__ == '__main__':
    runme()
