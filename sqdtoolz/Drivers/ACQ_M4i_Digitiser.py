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
from copy import deepcopy

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

    def __init__(self, name, cardid='spcm0', input_couplings='DC', **kwargs):
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
        if input_couplings == 'DC':
            input_couplings = 0
        elif input_couplings == 'AC':
            input_couplings = 1
        else:
            assert False, "Parameter input_couplings must be DC or AC."
        self.set_channel_settings(1, mV_range=1000., input_path=1, 
                                termination=0, coupling=input_couplings)#0)
        self.set_channel_settings(0, mV_range=1000., input_path=1, 
                                termination=0, coupling=input_couplings)#0)
        ###########################################################

        self.override_card_lock = False
        
        self.add_parameter(
            'samples', ManualParameter, 
            label='Number of samples per trigger.', 
            vals=vals.Multiples(divisor=16, min_value=32))
        self.samples(2048)

        # self.add_parameter(
        #     'channels',
        #     label='Number of channels',
        #     set_cmd=self._set_channels,
        #     vals=vals.Ints(1,2), initial_value=1)

        self.add_parameter(
            'segments',
            set_cmd=self._set_segments,
            label='Number of Segments',
            vals=vals.Ints(0,2**28), initial_value=1,
            docstring="Number of segments.\
                       Set to zero for autosegmentation.\
                       Connect the sequence start trigger to X0 (X1) for channels 0 (1) of the digitizer.")
        
        self._repetitions = 1
        self.ch_states = (True, False)
    
    @property
    def ChannelStates(self):
        return self.ch_states
    @ChannelStates.setter
    def ChannelStates(self, ch_states):
        assert len(ch_states) == 2, "There are 2 channel states that must be specified."
        
        final_flags = 0
        self.num_channels = 0
        if ch_states[0]:
            final_flags |= spcm.CHANNEL0
            self.num_channels += 1
        if ch_states[1]:
            final_flags |= spcm.CHANNEL1
            self.num_channels += 1
        self.enable_channels(final_flags)
        self.ch_states = ch_states

    @property
    def AvailableChannels(self):
        return 2

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
    def NumRepetitions(self):
        return self._repetitions
    @NumRepetitions.setter
    def NumRepetitions(self, num_reps):
        self._repetitions = num_reps

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
            self.enable_TS_SEQ_trig(False)
        else:
            self.multipurpose_mode_0.set('disabled')
            self.enable_TS_SEQ_trig(True)
            # self.initialise_time_stamp_mode()
            # setting number of segments to specific value.
            # Assuming X0 is the sequence start trigger.
            # self.multipurpose_mode_0.set('digital_in')

    def _set_sample_rate(self, rate):
        self.sample_rate.set(rate)
        new_rate = self.sample_rate.get()
        logging.warning(f"Cannot set sampling rate to {rate}, it is set to {new_rate} instead")

    def get_data(self, **kwargs):
        '''
        Gets processed data from the GPU. Processing involves gathering data and passing it through TvMode
        '''
        assert self.NumSamples > 32, "M4i requires the number of samples per segment to be at least 32."
        assert self.NumSamples % 16 == 0, "M4i requires the number of samples per segment to be divisible by 16."

        cur_processor = kwargs.get('data_processor', None)

        #Capture extra frame when running SEQ triggering as the SEQ trigger signal on X0 may not align exactly before the first captured segment trigger...
        if self.enable_TS_SEQ_trig():
            total_frames = (self.NumRepetitions+1)*self.NumSegments
        else:
            total_frames = (self.NumRepetitions)*self.NumSegments

        if cur_processor == None:
            if self.num_channels == 1:
                final_arrs = [np.zeros(total_frames * self.NumSamples)]
                final_arrs[0][:] = np.nan
            else:
                final_arrs = [np.zeros(total_frames * self.NumSamples), np.zeros(total_frames * self.NumSamples)]
                final_arrs[0][:] = np.nan
                final_arrs[1][:] = np.nan
            #
            cur_ind = 0
            for cur_block in self.multiple_trigger_fifo_acquisition(total_frames, self.NumSamples, 1, self.NumSegments, notify_page_size_bytes=4096):
                if self.num_channels == 1:
                    blk_size = cur_block.size
                    end_pt = min( blk_size, final_arrs[0].size - cur_ind)
                    final_arrs[0][cur_ind:cur_ind+end_pt] = deepcopy(cur_block[:end_pt])
                else:
                    blk_size = int(cur_block.size/2)
                    end_pt = min( blk_size, final_arrs[0].size - cur_ind)
                    final_arrs[0][cur_ind:cur_ind+end_pt] = deepcopy(cur_block[:2*end_pt:2])
                    final_arrs[1][cur_ind:cur_ind+end_pt] = deepcopy(cur_block[1:2*end_pt:2])
                cur_ind += end_pt
            #
            total_num_data = self.NumRepetitions * self.NumSegments * self.NumSamples   #The trimmed indexing is required when using SEQ trigger mode in which the data will be taken in excess...
            #TODO: Investigate the impact of multiplying by mVrange/1000/ADC_to_voltage() to get the voltage - may have a slight performance impact?
            return {
                'parameters' : ['repetition', 'segment', 'sample'],
                'data' : { f'ch{m}' : final_arrs[m][:total_num_data].reshape(self.NumRepetitions, self.NumSegments, self.NumSamples) for m in range(len(final_arrs)) },
                'misc' : {'SampleRates' : [self.sample_rate.get()]*self.num_channels}
            }
        else:
            #Gather data and either pass it to the data-processor or just collate it under final_arr - note that it is sent to the processor as properly grouped under the ACQ
            #data format specification.
            cache_array = []
            total_reps = 0
            done = False
            for cur_block in self.multiple_trigger_fifo_acquisition(total_frames, self.NumSamples, 1, self.NumSegments, notify_page_size_bytes=4096):
                if len(cache_array) > 0:
                    arr_blk = np.concatenate((cache_array, np.array(cur_block)))
                else:
                    arr_blk = np.array(cur_block)

                if self.num_channels == 1:
                    num_reps = int( arr_blk.size / (self.NumSegments*self.NumSamples) ) 
                    if num_reps + total_reps <= self.NumRepetitions:
                        total_reps += num_reps                
                        cache_array = arr_blk[(num_reps*self.NumSegments*self.NumSamples):]
                        if num_reps == 0:
                            continue
                        arr_blk = [arr_blk[0:(num_reps*self.NumSegments*self.NumSamples)].reshape(num_reps, self.NumSegments, self.NumSamples)]
                    else:
                        num_reps = self.NumRepetitions - total_reps
                        if num_reps == 0:
                            done = True
                        arr_blk = [arr_blk[0:(num_reps*self.NumSegments*self.NumSamples)].reshape(num_reps, self.NumSegments, self.NumSamples)]
                        done = True
                else:
                    num_reps = int( arr_blk.size / (self.NumSegments*self.NumSamples*2) )
                    if num_reps + total_reps <= self.NumRepetitions:
                        total_reps += num_reps
                        cache_array = arr_blk[(num_reps*self.NumSegments*self.NumSamples*2):]
                        if num_reps == 0:
                            continue
                        arr_blk = [
                            arr_blk[0:(num_reps*self.NumSegments*self.NumSamples*2):2].reshape(num_reps, self.NumSegments, self.NumSamples),
                            arr_blk[1:(num_reps*self.NumSegments*self.NumSamples*2):2].reshape(num_reps, self.NumSegments, self.NumSamples)
                        ]
                    else:
                        num_reps = self.NumRepetitions - total_reps
                        if num_reps == 0:
                            done = True
                        arr_blk = [
                            arr_blk[0:(num_reps*self.NumSegments*self.NumSamples*2):2].reshape(num_reps, self.NumSegments, self.NumSamples),
                            arr_blk[1:(num_reps*self.NumSegments*self.NumSamples*2):2].reshape(num_reps, self.NumSegments, self.NumSamples)
                        ]
                        done = True
                
                cur_processor.push_data({
                    'parameters' : ['repetition', 'segment', 'sample'],
                    'data' : { f'CH{m}' : arr_blk[m].astype(dtype=np.float64) for m in range(self.num_channels) },
                    'misc' : {'SampleRates' : [self.sample_rate.get()]*self.num_channels}
                })
                if done:
                    break
        
            return cur_processor.get_all_data()

from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
from sqdtoolz.HAL.Processors.CPU.CPU_FFT import*
import matplotlib.pyplot as plt
import time

import scipy.fftpack

from sqdtoolz.Laboratory import Laboratory

#import pdb
def runme():
    lab = Laboratory('','')
    new_digi = ACQ_M4i_Digitiser("test")
    new_digi.ChannelStates = (True,False)
    new_digi.NumSegments = 1#3 * (2**26))
    new_digi.NumSamples = 2**19#(2**13)#2**8+2**7)
    new_digi.NumRepetitions = 1

    new_digi.NumRepetitions = 5
    new_digi.NumSegments = 1
    new_digi.NumSamples = 512

    # term = new_digi._param32bit(30130)
    # term = new_digi.termination_1()
    # new_digi.snapshot()

    myProc = ProcessorCPU('test', lab)
    myProc.add_stage(CPU_DDC([25e6]*2))
    myProc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 25e6, 'Win' : 'hamming'}]*4))
    # myProc.add_stage(CPU_Mean('sample'))
    # myProc.add_stage(CPU_Mean('segment'))
    # myProc.add_stage_end(CPU_Mean('repetition'))
    myProc.add_stage(CPU_FFT())

    a = new_digi.get_data(data_processor=myProc)
    b = new_digi.get_data(data_processor=myProc)
    c = new_digi.get_data(data_processor=myProc)
    d = new_digi.get_data(data_processor=myProc)
    e = new_digi.get_data(data_processor=myProc)
    f=0


    # new_digi._set_channels(2)
    # new_digi.pretrigger_memory_size(0)
    # for m in range(20):
    #     a = new_digi.get_data()#(data_processor=myProc)
    #     print(new_digi.get_error_info32bit())
    #     print(a['data']['ch0'].shape)
    cur_time = time.time()
    a = new_digi.get_data(data_processor=None)
    cur_time = time.time() - cur_time
    plt.plot(a['data']['ch0'][0][0])
    plt.plot(a['data']['ch0'][0][0] * np.cos(2*np.pi*25e6*np.arange(a['data']['ch0'][0][0].size)/500e6))
    # plt.plot(a['data']['ch0_I'][0][0])
    # plt.plot(a['data']['ch0_Q'][0][0])


    # dataVals = a['data']['ch0'][0][0]
    # yf = scipy.fftpack.fft(dataVals)
    # N = dataVals.size
    # T = 1.0 / 500e6
    # x = np.linspace(0.0, N*T, N)
    # xf = np.linspace(0.0, 1.0/(2.0*T), int(N/2))
    # plt.plot(xf, 2.0/N * np.abs(yf[:N//2]))

    plt.show()
    input('Press ENTER')
    print('we made it!')
    # np.savetxt('sample.txt', np.ndarray.flatten(a['data']['ch0'].astype(np.float32)+np.float32(4000*1)))
    # time.sleep(5)
    print('we wrote it!')
    # gc.collect()
    fig, axs = plt.subplots(2)
    for r in range(2):#acq_module.NumRepetitions):
        for s in range(1):
            axs[0].plot(a['data']['ch0_I'][r][s].astype(np.float32)+np.float32(4000*r))
            axs[0].plot(a['data']['ch1_I'][r][s].astype(np.float32)+np.float32(4000*r))
            #
            # axs[0].plot(np.ones(a['data']['ch0'][r][s].size))
            # axs[1].plot(np.ones(512))
    # plt.plot(leData[0][0])
    # plt.show()
    print('we plotted it!')
    # input('wait')
    

    new_digi.samples(496)#2**8+2**7)
    b = new_digi.get_data()#(data_processor=myProc)
    print('we made it!')
    # time.sleep(2)
    # np.savetxt('sample.txt', np.ndarray.flatten(a['data']['ch0'].astype(np.float32)+np.float32(4000*1)))
    print('we wrote it!')
    # gc.collect()
    for r in range(1):#acq_module.NumRepetitions):
        for s in range(new_digi.NumSegments):
            axs[1].plot(b['data']['ch0'][r][s].astype(np.float32)+np.float32(4000*r))
            # axs[1].plot(np.ones(512))

    # plt.plot(leData[0][0])
    plt.show()
    
    # # fig.show()
    # #a = [print(np.array(x)) for x in new_digi.multiple_trigger_fifo_acquisition(3*2**26,384,2**11)]

    # # assert (num_of_acquisitions*self.samples.get()%4096 == 0) or (num_of_acquisitions*self.samples.get() in [2**4, 2**5, 2**6, 2**7, 2**8, 2**9, 2**10, 2**11]), "The number of total samples requested to the card is not valid.\nThis must be 16, 32, 64, 128, 256, 512, 1k ,2k or any multiple of 4k.\nThe easiest way to ensure this is to use powers of 2 for averages, samples and segments, probably in that order of priority."
    # s=0
    input("done")
    

if __name__ == '__main__':
    runme()
