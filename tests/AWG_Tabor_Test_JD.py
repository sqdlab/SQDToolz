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
from sqdtoolz.Variable import*
from sqdtoolz.Laboratory import*

from sqdtoolz.HAL.Processors.ProcessorCPU import*
from sqdtoolz.HAL.Processors.CPU.CPU_DDC import*
from sqdtoolz.HAL.Processors.CPU.CPU_FIR import*
from sqdtoolz.HAL.Processors.CPU.CPU_Mean import*
import time
import unittest


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

FIR_FILE = r"Z:\Manuals\Proteus\UPDATE on 2022-01-18 (v2 DSP)\Scripts\sfir_51_tap.csv"

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

def test_acq_driver_1(waveform_setup = setup_acq_const_tests) :
    """
    acquisition driver test 1 acquire a constant pulse from both channels
    """
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSegments = 2
    acq_module.NumRepetitions = 2


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

def test_acq_driver_2(lab, waveform_setup = setup_acq_const_tests) :
    """
    acquisition driver test 1 acquire a constant pulse from both channels
    with a processor being used in acquisition
    """
    proc = ProcessorCPU("DDC", lab)
    proc.add_stage(CPU_DDC([100e6]*2))
    proc.add_stage(CPU_FIR([{'Type' : 'low', 'Taps' : 40, 'fc' : 10e6, 'Win' : 'hamming'}]*4))

    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
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
    input('Press ENTER to finish test.')

def test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests) :
    """
    Varying repitition, numframes, and numSamples test
    """
    waveform_setup()
    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
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
    
def test_awg_driver_1() :
    """
    Test Single Channel (CH1) programming
    """
    # Waveform transformation
    WFMT_ModulationIQ("OscMod", lab, 100e6)

    # Setup waveforms
    awg_wfm1 = WaveformAWG("Waveform CH1", lab,  [(['TaborAWG', 'AWG'], 'CH1')], 1e9)

    # Add Segments
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 1024e-9, 0.25))
    awg_wfm1.add_waveform_segment(WFS_Constant(f"init1", lab.WFMT('OscMod').apply(), 1024e-9, 0.25))
    #awg_wfm1.add_waveform_segment(WFS_Constant(f"init", lab.WFMT('OscMod').apply(), 512e-9-384e-9, 0.25))
    #awg_wfm1.add_waveform_segment(WFS_Constant(f"zero1", None, 512e-9+384e-9, 0.0))
    #awg_wfm1.add_waveform_segment(WFS_Constant(f"zero2", None, 576e-9, 0.0))
    
    # Setup trigger 
    awg_wfm1.get_output_channel(0).marker(0).set_markers_to_segments(["init"])

    # Prepare waveforms and output them
    awg_wfm1.prepare_initial()
    awg_wfm1.prepare_final()

    # Set output channel to true
    awg_wfm1.get_output_channel(0).Output = True

    instr = lab._get_instrument('TaborAWG')

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.set_data_processor(None)
    acq_module.NumSamples = 4800
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


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
    plt.show()
    # awg_wfm1.get_output_channel(0).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_2() :
    """
    Test Single Channel (CH2) programming
    """
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

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


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
    plt.show()
    awg_wfm1.get_output_channel(0).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_3() :
    """
    Test Double Channel (CH1 and CH2) programming where
    channels share a memory bank
    """
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

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


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
    plt.show()
    awg_wfmIQ.get_output_channel(0).Output = False
    awg_wfmIQ.get_output_channel(1).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_4() :
    """
    Test Double Channel (CH1 and CH2) programming where
    channels share a memory bank. This test varies length of pulses
    """
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

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800 * 4
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


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
    plt.show()
    awg_wfmIQ.get_output_channel(0).Output = False
    awg_wfmIQ.get_output_channel(1).Output = False
    input('Press ENTER to finish test.')

def test_awg_driver_5() :
    """
    test of waveform with large number of segments
    across both channels (CH1 and CH2) which share a memory bank
    """
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

    acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
    acq_module.NumSamples = 4800 * 12
    acq_module.NumSegments = 1
    acq_module.NumRepetitions = 1


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
    plt.show()
    awg_wfmIQ.get_output_channel(0).Output = False
    awg_wfmIQ.get_output_channel(1).Output = False
    input('Press ENTER to finish test.')
    
def test_awg_driver_6(lab) :
    """
    Test using external trigger
    Note this test is not robust to different external triggers
    """
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

### ACQ TESTS ###
# test_acq_driver_1(waveform_setup = setup_acq_const_tests)
# test_acq_driver_1(waveform_setup = setup_acq_osc_tests)
# test_acq_driver_2(lab, waveform_setup = setup_acq_const_tests)

# Vary Reps
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 1, waveform_setup = setup_acq_full_osc_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 3, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 5, waveform_setup = setup_acq_const_tests)

# Vary Frames
# test_acq_driver_3(numSamples = 4800, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 6, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 4800, numFrames = 8, numReps = 1, waveform_setup = setup_acq_const_tests)

# Vary number of samples
# test_acq_driver_3(numSamples = 50*48, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 150*48, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)
# test_acq_driver_3(numSamples = 400*48, numFrames = 4, numReps = 1, waveform_setup = setup_acq_const_tests)

### AWG TESTS ###
test_awg_driver_1()
test_awg_driver_2()
test_awg_driver_3()
test_awg_driver_4()
test_awg_driver_5()
# test_awg_driver_6(lab)
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

acq_module = ACQ("TabourACQ", lab, ['TaborAWG', 'ACQ'])
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

