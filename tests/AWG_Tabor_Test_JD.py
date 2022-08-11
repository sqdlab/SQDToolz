"""
This is a test bench written for the purpose of understanding 
the sqdToolz stack and developing new code for updated tabor firmwares
"""
"""
NOTES on version 1.212
computer freezes if you run multiple times without restarting vs code
Had a computer freeze incident even when restarting vs code

NOTES on version 1.218 
computer ran this code successfully on the first run
able to switch between signal forms as long as vs code was restarted

NOTES on 08/04/2022
Tabor currently working reliably on latest firmware (saying so tentatively)
Problems attributed to cooling factors and the fan not be turned up to high,
affecting memory loading
"""

"""
SETUP FOR THESE TESTS
CH1 to INPUT1
CH2 to INPUT2
CH1MKR1 to TRIG IN
"""
### =====================================IMPORTS=============================== ###
from sqdtoolz.Experiment import Experiment
from sqdtoolz.HAL.DDG import*
from sqdtoolz.HAL.AWG import*
from sqdtoolz.HAL.ACQ import*
from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.HAL.WaveformSegments import*
from sqdtoolz.HAL.WaveformTransformations import*
import numpy as np
import scipy
from sqdtoolz.Variable import*
from sqdtoolz.Laboratory import*
import sqdtoolz as stz

from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
import time
import unittest
import matplotlib.pyplot as plt


### ==========================INSTRUMENT SETUP================================== ###
# Create New Laboratory Class
lab = Laboratory(instr_config_file = "tests\\TaborTest_JD.yaml", save_dir = "mySaves\\")

# Load the Tabor into the lab class to use
lab.load_instrument('TaborAWG')

# Define the modulation waveform transformation
#WFMT_ModulationIQ("myTestMod", lab, 100e6)
# Setup an AWG waveform
#awg_wfm_q = WaveformAWG("Waveform 2 CH", lab,  [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH2')], 1e9)
awg_wfm_q = WaveformAWG("Waveform 2 CH", lab,  [(['TaborAWG', 'AWG'], 'CH1'), (['TaborAWG', 'AWG'], 'CH2')], 1e9)
#awg_wfm_q = WaveformAWG("Waveform 2 CH", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)

### =============================ACQ TESTS ====================================== ###
"""
Parameters to Vary:
- Sample Rate
- Record Length: number of samples to be captured per trigger event
- Digitizer: Current active digitizer channel
- Digitizer Range: Range of values that the digitizer reads :- always set to max range on initialization
NOTES:
Need to figure out whether it is generation or acquisition thats causing the funky reads due to varying repititions 
"""
def setup_acq_const_tests(amp = 0.4, trigger = "EXT") :
    """
    Function to setup CH1 and CH2 to output simple signals to acquires
    """
    print("Setting up Constant Waveforms for Acquisition")
    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH1", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)
    awg_wfm2 = WaveformAWG("Waveform CH2", lab,  [(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", None, 512e-9-384e-9, 0.4))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
    if (trigger == "EXT") :
        awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    awg_wfm2.add_waveform_segment(WFS_Constant(f"init", None, 512e-9-384e-9, 0.4))
    awg_wfm2.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfm2.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm1.prepare_final()
    awg_wfm2.prepare_initial()
    awg_wfm2.prepare_final()

    awg_wfm1.get_output_channel(0).Output = True
    awg_wfm2.get_output_channel(0).Output = True

def setup_acq_osc_tests(amp = 0.4, trigger = "EXT") :
    """
    Function to setup CH1 and CH2 to output simple signals to acquires
    """
    print("Setting up IQ Waveforms for Acquisition")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH1", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)
    awg_wfm2 = WaveformAWG("Waveform CH2", lab,  [(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 512e-9-384e-9, amp))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
    if (trigger == "EXT") :
        awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    awg_wfm2.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 512e-9-384e-9, amp))
    awg_wfm2.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfm2.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm1.prepare_final()
    awg_wfm2.prepare_initial()
    awg_wfm2.prepare_final()

    awg_wfm1.get_output_channel(0).Output = True
    awg_wfm2.get_output_channel(0).Output = True

def setup_acq_full_osc_tests(amp = 0.2, trigger = "EXT") :
    """
    Function to setup CH1 and CH2 to output simple signals to acquires
    """
    print("Setting up IQ Waveforms")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH1", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)
    awg_wfm2 = WaveformAWG("Waveform CH2", lab,  [(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 1024e-9, amp))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init0", lab.WFMT('OscMod').apply(), 1024e-9, amp))
    if (trigger == "EXT") :
        awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    awg_wfm2.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 2*1024e-9, amp))

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm1.prepare_final()
    awg_wfm2.prepare_initial()
    awg_wfm2.prepare_final()

    awg_wfm1.get_output_channel(0).Output = True
    awg_wfm2.get_output_channel(0).Output = True

def setup_acq_multi_osc_tests(amps = [0.2,0.15,0.1,0.05], freqs = [100e6,120e6,140e6,160e6], trigger = "EXT") :

    print("Setting up Multiplexed Waveforms for Acquisition")
    phases = np.zeros(len(freqs))

    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH1", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)
    awg_wfm2 = WaveformAWG("Waveform CH2", lab,  [(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", None, 2*1024e-9))
    awg_wfm1.add_waveform_segment(WFS_Multiplex(f"init1", None, 2*1024e-9, amplitudes = amps, frequencies = freqs, phases = phases))
    #awg_wfm1.add_waveform_segment(WFS_Multiplex(f"init2", None, 1024e-9, amplitudes = amps, frequencies = freqs, phases = phases))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init3", None, 4*1024e-9))
    if (trigger == "EXT") :
        awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    awg_wfm2.add_waveform_segment(WFS_Multiplex(f"init", None, 2*1024e-9, amplitudes = amps, frequencies = freqs, phases = phases))

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm2.prepare_initial()
    awg_wfm1.prepare_final()
    awg_wfm2.prepare_final()

    awg_wfm1.get_output_channel(0).Output = True
    awg_wfm2.get_output_channel(0).Output = True

def setup_acq_multi_time_osc_tests(amps = [0.1, 0.1, 0.1, 0.1], freqs = [100e6,120e6,140e6,160e6], trigger = "EXT") :
    print("Setting up Varying Frequency Waveforms for Acquisition")
    phases = np.zeros(len(freqs))

    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH1", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)
    awg_wfm2 = WaveformAWG("Waveform CH2", lab,  [(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", None, 2*1024e-9))
    awg_wfm1.add_waveform_segment(WFS_Cosine(f"init0", None, 1024e-9, amplitude=amps[0], frequency=freqs[0], phase=0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init1", None, 1024e-9))
    awg_wfm1.add_waveform_segment(WFS_Cosine(f"init2", None, 1024e-9, amplitude=amps[1], frequency=freqs[1], phase=0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init3", None, 1024e-9))
    awg_wfm1.add_waveform_segment(WFS_Cosine(f"init4", None, 1024e-9, amplitude=amps[2], frequency=freqs[2], phase=0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init5", None, 1024e-9))
    awg_wfm1.add_waveform_segment(WFS_Cosine(f"init6", None, 1024e-9, amplitude=amps[3], frequency=freqs[3], phase=0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init5", None, 4*1024e-9))
    if (trigger == "EXT") :
        awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    awg_wfm2.add_waveform_segment(WFS_Multiplex(f"init", None, 2*1024e-9, amplitudes = amps, frequencies = freqs, phases = phases))

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm2.prepare_initial()
    awg_wfm1.prepare_final()
    awg_wfm2.prepare_final()

    awg_wfm1.get_output_channel(0).Output = True
    awg_wfm2.get_output_channel(0).Output = True

def test_acq_driver_1(waveform_setup = setup_acq_const_tests) :
    """
    acquisition driver test 1 acquire a constant pulse from both channels
    """
    print("Running Acquisition Driver Test 1")
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1
    lab.HAL("TaborACQ").SampleRate = 1e9


    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = leData['data']['CH1'][r][s][1::2]    #I
            plt.plot(data)
            data = leData['data']['CH1'][r][s][0::2]    #Q
            plt.plot(data)
            data = leData['data']['CH2'][r][s][1::2]
            plt.plot(data)
            data = leData['data']['CH2'][r][s][0::2]
            plt.plot(data)
    plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
    input('Press ENTER to finish test.')

def test_acq_driver_2(lab, waveform_setup = setup_acq_const_tests) :
    """
    acquisition driver test 1 acquire a constant pulse from both channels
    with a processor being used in acquisition
    """
    print("Running Acquisition Driver Test 2")
    proc = ProcessorCPU("DDC", lab)
    proc.add_stage(CPU_DDC([100e6]*2))
    proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 10e6, 'Win' : 'hamming'}]*4))

    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSegments = 2
    acq_module.NumRepetitions = 2
    acq_module.set_data_processor(proc)


    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = leData['data']['CH1_I'][r][s][1::2]    #I
            plt.plot(data)
            data = leData['data']['CH1_Q'][r][s][0::2]    #Q
            plt.plot(data)
            data = leData['data']['CH2_I'][r][s][1::2]
            plt.plot(data)
            data = leData['data']['CH2_Q'][r][s][0::2]
            plt.plot(data)
    plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
    # Clean up data processor for later tests
    lab.HAL("TaborACQ").set_data_processor(None)
    input('Press ENTER to finish test.')

def test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests) :
    """
    Varying repitition, numframes, and numSamples test
    """
    print("Running Acquisition Driver Test 3")
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = numSamples
    acq_module.NumSegments = numFrames
    acq_module.NumRepetitions = numReps


    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = leData['data']['CH1'][r][s][1::2]    #I
            plt.plot(data, label = f'CH1-I-S:{s}-R:{r}')
            data = leData['data']['CH1'][r][s][0::2]    #Q
            plt.plot(data, label = f'CH1-Q-S:{s}-R:{r}')
            data = leData['data']['CH2'][r][s][1::2]
            plt.plot(data, label = f'CH2-I-S:{s}-R:{r}')
            data = leData['data']['CH2'][r][s][0::2]
            plt.plot(data, label = f'CH2-Q-S:{s}-R:{r}')
    plt.legend(loc="upper right")
    plt.show()
    input('Press ENTER to finish test.')

def test_acq_driver_4(numSamples = 4800, numFrames = 4, numReps = 1, waveform_setup = setup_acq_multi_time_osc_tests) :
    """
    Test DSP Kernel blocks on proteus, filter coefficients taken from file provided by Tabor
    """
    print("Running Acquisition Driver Test 4")
    # filt_coeffs = np.array([-0.00084713, 0.000673766, 0.001850315, -0.000517804, -0.003273407,-0.000363655,0.004920981,0.002325397,-0.006386267,\
    #     -0.005644754,0.007043156,0.010434112,-0.006062997,-0.016572719,0.002425474,0.023678146,0.005161621,-0.031130307,-0.018682209,\
    #     0.038149254,0.042538523,-0.043914904,-0.092565044,0.047705801,0.313645744,0.450972039,0.313645744,0.047705801,-0.092565044,\
    #     -0.043914904,0.042538523,0.038149254,-0.018682209,-0.031130307,0.005161621,0.023678146,0.002425474,-0.016572719,-0.006062997,\
    #     0.010434112,0.007043156,-0.005644754,-0.006386267,0.002325397,0.004920981,-0.000363655,-0.003273407,-0.000517804,0.001850315,\
    #     0.000673766,-0.00084713])

    #filt_coeffs = np.zeros(51)
    filt_coeffs = np.ones(51)
    filt_coeffs = scipy.signal.firwin(51, 10e6, fs=lab._get_instrument('TaborAWG').ACQ.sample_rate())
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 48 * 500 
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1
    acq_module._instr_acq.setup_data_path(ddc_mode = "REAL", acq_mode = "DUAL", ddr1_store = "DIR1", ddr2_store = "DIR2")
    acq_module._instr_acq.setup_data_path(ddc_mode = "REAL", acq_mode = "DUAL", ddr1_store = "DSP1", ddr2_store = "DIR2")
    acq_module._instr_acq.setup_kernel("IQ4", filt_coeffs, flo = 100e6)

    #acq_module._instr_acq.setup_filter("I1", filt_coeffs)
    #acq_module._instr_acq.setup_filter("Q1", filt_coeffs)
    
    leData = acq_module.get_data()
    leDecisions = instr.ACQ.get_frame_data()
    print("Decisions: {0} + j {1}".format(leDecisions["I"], leDecisions["Q"]))
    print("State1: {0}".format(leDecisions["state1"]))
    print("State2: {0}".format(leDecisions["state2"]))
    import matplotlib.pyplot as plt
    # for r in range(acq_module.NumRepetitions) :
    #     for s in range(acq_module.NumSegments) :
    #         data = leData['data']['CH1'][r][s]    
    #         freqs = np.fft.fftfreq(len(data), 1.0/lab.HAL("TaborACQ").SampleRate)
    #         arr_fft = np.abs(np.fft.fft(data))
    #         plt.plot(freqs, arr_fft)
    # plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = leData['data']['CH1'][r][s][1::2]   
            plt.plot(data)
            data = leData['data']['CH1'][r][s][0::2]    #Q
            plt.plot(data)
    plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
    input('Press ENTER to finish test.')

def test_acq_driver_5(waveform_setup = setup_acq_multi_osc_tests) :
    """
    acquisition driver test 1 acquire a 4 tone pulse and plot the FFT
    """
    print("Running Acquisition Driver Test 5")
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 48 * 250 
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1
    lab.HAL("TaborACQ").SampleRate = 1e9

    # stz.ProcessorCPU('demodulator', lab)
    # lab.PROC('demodulator').reset_pipeline()
    # lab.PROC('demodulator').add_stage(stz.CPU_Duplicate([4,4]))
    # lab.PROC('demodulator').add_stage(stz.CPU_DDC([100e6, 120e6, 140e6, 160e6, 100e6, 120e6, 140e6, 160e6]))
    # lab.PROC('demodulator').add_stage(stz.CPU_FIR([{'Type' : 'low', 'Taps' : 128, 'fc' : 10e6, 'Win' : 'hamming'}]*16))
    # lab.HAL("TaborACQ").set_data_processor(lab.PROC('demodulator'))

    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = leData['data']['CH1'][r][s]
            plt.plot(data)
            # plt.show() 
            # data1 = np.sqrt(leData['data']['CH1_3_I'][r][s]**2 + leData['data']['CH1_3_Q'][r][s]**2)
            # data2 = np.sqrt(leData['data']['CH1_0_I'][r][s]**2 + leData['data']['CH1_0_Q'][r][s]**2)
            # data3 = np.sqrt(leData['data']['CH1_1_I'][r][s]**2 + leData['data']['CH1_1_Q'][r][s]**2)
            # data4 = np.sqrt(leData['data']['CH1_2_I'][r][s]**2 + leData['data']['CH1_2_Q'][r][s]**2)
            # plt.plot(data1)
            # plt.plot(data2)
            # plt.plot(data3)
            # plt.plot(data4)
            # plt.legend(["160e6","100e6","120e6","140e6"])
            plt.xlabel("Sample Number")
            plt.ylabel("Digitization Amplitude")
            plt.show()
            #data = leData['data']['CH1'][r][s]    
            #freqs = np.fft.fftfreq(len(data), 1.0/lab.HAL("TaborACQ").SampleRate)
            #arr_fft = np.abs(np.fft.fft(data))
            #plt.plot(freqs, arr_fft)
    plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
    input('Press ENTER to finish test.')

def test_acq_driver_6(waveform_setup = setup_acq_multi_time_osc_tests) :
    """
    acquisition driver test 1 acquire a 4 tone pulse and plot the FFT
    """
    print("Running Acquisition Driver Test 6")
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')


    filt_coeffs = scipy.signal.firwin(51, 1e6, fs=lab._get_instrument('TaborAWG').ACQ.sample_rate())
    #plt.plot(filt_coeffs)
    #plt.show()
    print(filt_coeffs)
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.ChannelStates = (True, True)
    acq_module.NumSamples = 48 * 250 
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1
    #acq_module._instr_acq.setup_data_path(ddc_mode = "REAL", acq_mode = "DUAL", ddr1_store = "DIR1", ddr2_store = "DIR2")
    acq_module._instr_acq.setup_data_path(ddc_mode = "REAL", acq_mode = "DUAL", ddr1_store = "DIR1", ddr2_store = "DIR2")
    #acq_module._instr_acq.setup_kernel("IQ4", filt_coeffs, flo = 120e6-70e6)
    lab.HAL("TaborACQ").SampleRate = 1e9
    stz.ProcessorCPU('demodulator', lab)
    lab.PROC('demodulator').reset_pipeline()
    lab.PROC('demodulator').add_stage(stz.CPU_Duplicate([4]))
    lab.PROC('demodulator').add_stage(stz.CPU_DDC([100e6, 120e6, 140e6, 160e6]))
    lab.PROC('demodulator').add_stage(stz.CPU_FIR([{'Type' : 'low', 'Taps' : 128, 'fc' : 10e6, 'Win' : 'hamming'}]*10))
    lab.HAL("TaborACQ").set_data_processor(lab.PROC('demodulator'))

    leData = acq_module.get_data()
    # TAP = 51
    # flo = 100e6
    # res = 10
    # L = 6000*2#res * int(np.ceil(10240 / res))
    # k = np.ones(L+TAP)
    # ts = 1 / lab.HAL("TaborACQ").SampleRate
    # t = np.linspace(0, L*ts, L, endpoint=False)
    # loi = np.cos(2 * np.pi * flo * t)
    # loq = -(np.sin(2 * np.pi * flo * t))
    #iData = leData['data']['CH1'][r][s][1::2]
    #qData = leData['data']['CH1'][r][s][0::2]
    #iData = iData * loi
    #qData = qData * loq
    #leDecisions = instr.ACQ.get_frame_data()
    
    

    
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data1 = leData['data']['CH1'][r][s]
            plt.plot(data1)
            plt.show()
            # data1 = np.sqrt(leData['data']['CH1_3_I'][r][s]**2 + leData['data']['CH1_3_Q'][r][s]**2)
            # data2 = np.sqrt(leData['data']['CH1_0_I'][r][s]**2 + leData['data']['CH1_0_Q'][r][s]**2)
            # data3 = np.sqrt(leData['data']['CH1_1_I'][r][s]**2 + leData['data']['CH1_1_Q'][r][s]**2)
            # data4 = np.sqrt(leData['data']['CH1_2_I'][r][s]**2 + leData['data']['CH1_2_Q'][r][s]**2)
            # plt.plot(data1)
            # plt.show()
            # plt.plot(data2)
            # plt.show()
            # plt.plot(data3)
            # plt.show()
            # plt.plot(data4)
            # plt.show()

            # freqs = np.fft.fftfreq(len(data), 1.0/lab.HAL("TaborACQ").SampleRate)
            # arr_fft = np.abs(np.fft.fft(data))
            # fftData = np.fft.fft(data)
            # freq = np.fft.fftfreq(len(data), 1.0/lab.HAL("TaborACQ").SampleRate)
            # fftData = np.abs(np.fft.fftshift(fftData))
            # freq = np.fft.fftshift(freq)
            #plt.plot(data)
            #iData = np.convolve(filt_coeffs, leData['data']['CH1'][r][s] * loi) #* (loi)
            #qData = np.convolve(filt_coeffs, leData['data']['CH1'][r][s] * loq) #* (loq)
            #plt.plot(leData['data']['CH1'][0][0])
            #plt.plot(iData)
            #plt.plot(qData)
            #np.convolve(iData, filt_coeffs)
            #np.convolve(qData, filt_coeffs)
            #iData = iData * loi
            #qData = qData * loq
            #plt.plot(iData)
            #plt.plot(qData)

            # data = leData['data']['CH1'][r][s][1::2]    #I
            # plt.plot(data)
            # data = leData['data']['CH1'][r][s][0::2]    #Q
            # plt.plot(data)
    plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!

def test_awg_driver_1() :
    """
    Test Single Channel (CH1) programming
    """
    print("Running AWG Driver Test 1")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH1", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", None, 1024e-9, 0.25)) # lab.WFMT('OscMod').apply()
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init1", None, 1024e-9, 0.25)) # lab.WFMT('OscMod').apply()
    #awg_wfm1.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 512e-9-384e-9, 0.25))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
    
    # Setup trigger 
    awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm1.prepare_final()

    # Set output channel to true
    awg_wfm1.get_output_channel(0).Output = True

    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.set_data_processor(None)
    acq_module.NumSamples = 4800
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


    leData = acq_module.get_data()
    leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = np.sqrt(leData['data']['CH1'][r][s][1::2] ** 2 + leData['data']['CH1'][r][s][0::2] ** 2)     #I
            plt.plot(data)
            # data = leData['data']['CH1'][r][s][1::2]    #I
            # plt.plot(data)
            # data = leData['data']['CH1'][r][s][0::2]    #Q
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][1::2]
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][0::2]
            # plt.plot(data)
    plt.show()
    # awg_wfm1.get_output_channel(0).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_2() :
    """
    Test Single Channel (CH2) programming
    """
    print("Running AWG Driver Test 2")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH2", lab,  [(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 512e-9-384e-9, 0.25))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
    
    # Setup trigger 
    awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm1.prepare_final()

    # Set output channel to true
    awg_wfm1.get_output_channel(0).Output = True

    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = np.sqrt(leData['data']['CH1'][r][s][1::2] ** 2 + leData['data']['CH1'][r][s][0::2] ** 2)     #I
            plt.plot(data)
            # data = leData['data']['CH1'][r][s][1::2]    #I
            # plt.plot(data)
            # data = leData['data']['CH1'][r][s][0::2]    #Q
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][1::2]
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][0::2]
            # plt.plot(data)
    plt.show()
    awg_wfm1.get_output_channel(0).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_3() :
    """
    Test Double Channel (CH1 and CH2) programming where
    channels share a memory bank
    """
    print("Running AWG Driver Test 3")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfmIQ = WaveformAWG("Waveform IQ", lab,  [(['TaborAWG', 'AWG'], 'CH1') ,(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 512e-9-384e-9, 0.25))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
    
    # Setup trigger 
    awg_wfmIQ.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    # Prepare waveforms and output them
    awg_wfmIQ.prepare_initial()
    awg_wfmIQ.prepare_final()

    # Set output channel to true
    awg_wfmIQ.get_output_channel(0).Output = True
    awg_wfmIQ.get_output_channel(1).Output = True

    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = np.sqrt(leData['data']['CH1'][r][s][1::2] ** 2 + leData['data']['CH1'][r][s][0::2] ** 2)     #I
            plt.plot(data)
            # data = leData['data']['CH1'][r][s][1::2]    #I
            # plt.plot(data)
            # data = leData['data']['CH1'][r][s][0::2]    #Q
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][1::2]
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][0::2]
            # plt.plot(data)
    plt.show()
    awg_wfmIQ.get_output_channel(0).Output = False
    awg_wfmIQ.get_output_channel(1).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_4() :
    """
    Test Double Channel (CH1 and CH2) programming where
    channels share a memory bank. This test varies length of pulses
    """
    print("Running AWG Driver Test 4")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfmIQ = WaveformAWG("Waveform IQ", lab,  [(['TaborAWG', 'AWG'], 'CH1') ,(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"init0", lab.WFMT('OscMod').apply(), 512e-9-384e-9, 0.3))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"init1", lab.WFMT('OscMod').apply(), 512e-9, 0.2))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero3", None, 512e-9+384e-9, 0.0))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero4", None, 576e-9, 0.0))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"init2", lab.WFMT('OscMod').apply(), 50e-9*32, 0.1))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero5", None, 512e-9+384e-9, 0.0))
    awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero6", None, 576e-9, 0.0))
    
    # Setup trigger 
    awg_wfmIQ.get_output_channel(0).marker(0).set_markers_to_segments(["init0"])

    # Prepare waveforms and output them
    awg_wfmIQ.prepare_initial()
    awg_wfmIQ.prepare_final()

    # Set output channel to true
    awg_wfmIQ.get_output_channel(0).Output = True
    awg_wfmIQ.get_output_channel(1).Output = True

    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800 * 4
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = np.sqrt(leData['data']['CH1'][r][s][1::2] ** 2 + leData['data']['CH1'][r][s][0::2] ** 2)     #I
            plt.plot(data)
            # data = leData['data']['CH1'][r][s][1::2]    #I
            # plt.plot(data)
            # data = leData['data']['CH1'][r][s][0::2]    #Q
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][1::2]
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][0::2]
            # plt.plot(data)
    plt.show()
    awg_wfmIQ.get_output_channel(0).Output = False
    awg_wfmIQ.get_output_channel(1).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_5() :
    """
    test of waveform with large number of segments
    across both channels (CH1 and CH2) which share a memory bank
    """
    print("Running AWG Driver Test 5")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfmIQ = WaveformAWG("Waveform IQ", lab,  [(['TaborAWG', 'AWG'], 'CH1') ,(['TaborAWG', 'AWG'], 'CH2')], 1e9)

    # Add Segments
    for m in range(4):
        awg_wfmIQ.add_waveform_segment(WFS_Gaussian(f"init{m}", lab.WFMT('OscMod').apply(), 512e-9, 0.5-0.1*(m)))
        #awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero1{m}", None, 512e-9, 0.01*m))
        #awg_wfmIQ.add_waveform_segment(WFS_Gaussian(f"init2{m}", lab.WFMT('OscMod').apply(), 512e-9, 0.3))# 0.5-0.1*m))
        awg_wfmIQ.add_waveform_segment(WFS_Constant(f"zero2{m}", None, 512e-9, 0.0))

    
    # Setup trigger 
    awg_wfmIQ.get_output_channel(0).marker(0).set_markers_to_segments(["init0"])

    # Prepare waveforms and output them
    awg_wfmIQ.prepare_initial()
    awg_wfmIQ.prepare_final()

    # Set output channel to true
    awg_wfmIQ.get_output_channel(0).Output = True
    awg_wfmIQ.get_output_channel(1).Output = True

    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800 * 12
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


    leData = acq_module.get_data()
    #leDecisions = instr.ACQ.get_frame_data()

    import matplotlib.pyplot as plt
    for r in range(acq_module.NumRepetitions) :
        for s in range(acq_module.NumSegments) :
            data = np.sqrt(leData['data']['CH1'][r][s][1::2] ** 2 + leData['data']['CH1'][r][s][0::2] ** 2)     #I
            plt.plot(data)
            # data = leData['data']['CH1'][r][s][1::2]    #I
            # plt.plot(data)
            # data = leData['data']['CH1'][r][s][0::2]    #Q
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][1::2]
            # plt.plot(data)
            # data = leData['data']['CH2'][r][s][0::2]
            # plt.plot(data)
    plt.show()
    awg_wfmIQ.get_output_channel(0).Output = False
    awg_wfmIQ.get_output_channel(1).Output = False
    input('Press ENTER to finish test.')
    
def test_awg_driver_6(lab) :
    """
    Test using external trigger
    Note this test is not robust to different external triggers
    """
    print("Running AWG Driver Test 6")
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Load External Triggering Device
    lab.load_instrument('pulser')
    DDG("DDG", lab, 'pulser')
    lab.HAL('DDG').get_trigger_output('AB').TrigPulseLength = 50e-9
    lab.HAL('DDG').get_trigger_output('AB').TrigPolarity = 1
    lab.HAL('DDG').get_trigger_output('AB').TrigPulseDelay = 0.0e-9

    ACQ("TabACQ", lab, ['TaborAWG', 'ACQ'])
    WaveformAWG("WfmCon2", lab, [(['TaborAWG', 'AWG'], 'CH1'),(['TaborAWG', 'AWG'], 'CH2')], 1e9, total_time=10*1024000e-9)
    #lab.HAL("WfmCon2").add_waveform_segment(WFS_Constant("pulse", None, 100e-9, 0.0))
    #lab.HAL("WfmCon2").add_waveform_segment(WFS_Constant("zeros", None, -1, 0.0))

    # Construct Waveform to test
    for m in range(4):
        lab.HAL("WfmCon2").add_waveform_segment(WFS_Gaussian(f"init{m}", lab.WFMT('OscMod').apply(), 512000e-9, 0.5-0.1*(m)))
        lab.HAL("WfmCon2").add_waveform_segment(WFS_Gaussian(f"init1{m}", lab.WFMT('OscMod').apply(), 512000e-9, 0.5-0.1*(m)))
        #lab.HAL("WfmCon2").add_waveform_segment(WFS_Constant(f"zero2{m}", None, 512e-9, 0.0))

    # Pad Final Waveform
    lab.HAL("WfmCon2").add_waveform_segment(WFS_Constant(f"zero1{m}", None, -1, 0.0))

    lab.HAL("WfmCon2").get_output_channel(0).marker(0).set_markers_to_segments(['init0'])
    lab.HAL("WfmCon2").AutoCompression = 'None'

    lab.HAL("WfmCon2").set_trigger_source_all(lab.HAL("DDG").get_trigger_output('AB'))
    lab.HAL("TabACQ").set_trigger_source(lab.HAL("WfmCon2").get_output_channel(0).marker(0))

    lab.HAL("DDG").RepetitionTime = 10*10240000e-9 #4e-3

    lab.HAL("TabACQ").SampleRate = 1.4e9
    lab.HAL("TabACQ").set_acq_params(reps=1, segs=1, samples=2**20 * 3)
    lab.HAL("TabACQ").ChannelStates = (True, True)

    # lab.HAL("WfmCon2").prepare_initial()
    # lab.HAL("WfmCon2").prepare_final()
    # lab.HAL("WfmCon2").get_output_channel(0).Output = True

    ExperimentConfiguration('test_6', lab, 4e-3, ['DDG', 'WfmCon2'], 'TabACQ')
    exp = Experiment("AWG_test_6", lab.CONFIG('test_6'))
    lab.run_single(exp)
    lab.CONFIG('test_6').plot()
    plt.show()
    input('Press ENTER to finish test.')

### ACQ TESTS ###
# test_acq_driver_1(waveform_setup = setup_acq_multi_osc_tests)
# test_acq_driver_1(waveform_setup = setup_acq_osc_tests)
# test_acq_driver_2(lab, waveform_setup = setup_acq_const_tests)

# Vary Reps
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 1, waveform_setup = setup_acq_full_osc_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 3, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 5, waveform_setup = setup_acq_const_tests)

# Vary Frames
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 6, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 8, numReps = 1, waveform_setup = set
# up_acq_const_tests)

# Vary number of samples
# test_acq_driver_3(numSamples = 50*48, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 150*48, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 400*48, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)

# Test DSP processes
#test_acq_driver_6()
test_acq_driver_5()
# test_acq_driver_4()

### AWG TESTS ###
# test_awg_driver_1()
# test_awg_driver_2()
# test_awg_driver_3()
# test_awg_driver_4()
# test_awg_driver_5()
#test_awg_driver_6(lab)
input('Press ENTER to exit.')

### ========================== MANUAL TEST SCRIPT =============================== ###
###
# Script for manually testing the Tabor,
# Generates a signal on channel 1 output and reads it on channel 2 input
###
"""
awg_wfm_q.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('myTestMod').apply(), 512e-9-384e-9, 0.4))
#awg_wfm_q.add_waveform_segment(WFS_Constant(f"init{m}", lab.WFMT('myTestMod').apply(), 512e-9-384e-9, 0.5-0.1*m))
awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
#awg_wfm_q.add_waveform_segment(WFS_Constant(f"init2{m}", lab.WFMT('myTestMod').apply(), 512e-9, 0.0*(0.5-0.1*m)))
awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
#awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(read_segs)
awg_wfm_q.prepare_initial()
awg_wfm_q.prepare_final()

awg_wfm_q.get_output_channel(0).Output = True
awg_wfm_q.get_output_channel(1).Output = True
instr = lab._get_instrument('TaborAWG')

acq_module = ACQ("TaborACQ", lab, ['TaborAWG', 'ACQ'])
acq_module.NumSamples = 48 * 100
acq_module.NumSegments = 2
acq_module.NumRepetitions = 2


leData = acq_module.get_data()
leDecisions = instr.ACQ.get_frame_data()

import matplotlib.pyplot as plt
for r in range(2):
    for s in range(2):
        data = leData['data']['CH1'][r][s][1::2]    #I
        plt.plot(data)
        data = leData['data']['CH1'][r][s][0::2]    #Q
        plt.plot(data)
        data = leData['data']['CH2'][r][s][1::2]
        plt.plot(data)
        data = leData['data']['CH2'][r][s][0::2]
        plt.plot(data)
plt.show()  #!!!REMEMBER TO CLOSE THE PLOT WINDOW BEFORE CLOSING PYTHON KERNEL OR TABOR LOCKS UP (PC restart won't cut it - needs to be a chassis restart)!!!
"""
""" LOOPING TEST
for m in np.linspace(0.5, 0.0, 10):
    awg_wfm_q = WaveformAWG("Waveform 2 CH", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)
    awg_wfm_q.add_waveform_segment(WFS_Constant(f"init{m}", lab.WFMT('myTestMod').apply(), 512e-9-384e-9, m))
    #awg_wfm_q.add_waveform_segment(WFS_Constant(f"init{m}", lab.WFMT('myTestMod').apply(), 512e-9-384e-9, 0.5-0.1*m))
    awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero1{m}", None, 512e-9+384e-9, 0.0))
    #awg_wfm_q.add_waveform_segment(WFS_Constant(f"init2{m}", lab.WFMT('myTestMod').apply(), 512e-9, 0.0*(0.5-0.1*m)))
    awg_wfm_q.add_waveform_segment(WFS_Constant(f"zero2{m}", None, 576e-9, 0.0))
    #awg_wfm_q.get_output_channel(0).marker(0).set_markers_to_segments(read_segs)
    awg_wfm_q.prepare_initial()
    awg_wfm_q.prepare_final()

    awg_wfm_q.get_output_channel(0).Output = True
    awg_wfm_q.get_output_channel(1).Output = True
    time.sleep(2)
    print(f'running device at {m}')
"""

