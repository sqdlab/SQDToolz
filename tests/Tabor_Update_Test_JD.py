"""
This script is to test new functionality of the Tabor
"""

"""
NOTES 

FFT FUNCTIONALITY:
- it appears as though the results of an FFT are stored somewhere and may need to be manually erased

"""

PW = 200e-9 # Pulse Width
PHASE = 0 
DUC_NCO = 200e6 # Frequency of digital upconverter LO
ADCFS = 1000 # ADC full scale in mV

import os
import sys
import tempfile
import webbrowser
srcpath = os.path.realpath(r'Z:\Manuals\Proteus\UPDATE on 2022-01-18 (v2 DSP)\Scripts\SourceFiles')
sys.path.append(srcpath)
from teproteus import TEProteusAdmin as TepAdmin
from teproteus import TEProteusInst as TepInst
from teproteus_functions import get_cpatured_header
from teproteus_functions import gauss_env
from teproteus_functions import iq_kernel
from teproteus_functions import pack_kernel_data
from teproteus_functions import convert_sample_to_signed
from teproteus_functions import convertFftRawDataTodBm
from teproteus_functions import convertTimeRawDataTomV
from teproteus_functions import smooth
from teproteus_functions import pack_fir_data

import numpy as np
import time
import ipywidgets as widgets
from IPython.core.debugger import set_trace
from scipy.signal import chirp, sweep_poly
import matplotlib.pyplot as plt
plt.style.use('ggplot')
from scipy import signal
import math

# CLOCK CONFIGURATION OPTIONS =================================================
# internal parameters

DIG_SCLK = 2250e6
SCLK = DIG_SCLK * 4
WAVE_TIME = PW
GAUS_PW = PW
GAUS_PHASE = PHASE

if DUC_NCO<= DIG_SCLK:
    DDC_NCO = np.abs(np.round(DUC_NCO / DIG_SCLK) * DIG_SCLK - DUC_NCO)
else:
    DDC_NCO = DIG_SCLK - \
        np.abs(np.round(DUC_NCO / DIG_SCLK) * DIG_SCLK - DUC_NCO)

DUC_INTERP = 8

FRAME_NMB = 1
Frame_len = 2400 # must be 2400 for FFT processing

Debug = False

FRAME_NUM = FRAME_NMB
RDOUT_CH = 1

if ADCFS == 500:
    full_scale = "LOW"
elif ADCFS == 800:
    full_scale = "MED"
else:
    full_scale = "HIGH"

print('Digitizer NCO is {0} Mhz'.format(DDC_NCO / 1e6))

# CONNECT TO INSTRUMENT =======================================================
pid = os.getpid()
print('process id {0}'.format(pid))

LOCAL_DLL = False

if LOCAL_DLL == True:
    lib_dir_path= r'D:\Projects\ProtuesAwg.Ben.DSP_V2\x64\Debug'
else:
    lib_dir_path = None
    
# Connect to instrument
admin = TepAdmin(lib_dir_path)


    
# Get list of available PXI slots
slot_ids = admin.get_slot_ids()

# Assume that at least one slot was found
sid = 3#slot_ids[0]
print("Slot ID's : ", slot_ids)

 # Open a single-slot instrument:
time.sleep(2)
inst = admin.open_instrument(slot_id=sid)
#time.sleep(2)
# Get the instrument's *IDN
resp = inst.send_scpi_query('*IDN?')
print('Connected to: ' + resp)

# Get the model name
resp = inst.send_scpi_query(":SYST:iNF:MODel?")
print("Model: " + resp)

# Infer the natural DAC waveform format
if 'P9082' in resp:
    dac_mode = 8
else:
    dac_mode = 16
print("DAC waveform format: {0} bits-per-point".format(dac_mode))


if dac_mode == 16:
    max_dac = 65535
    data_type = np.uint16 
else:
    max_dac = 255
    data_type = np.uint8 
    
half_dac = round(max_dac / 2.0)

# at complex we use always 16bit
task_half_dac = 32768

    
print('task_half_dac = {0}'.format(task_half_dac))


# INITIALISATIONS =============================================================
inst.default_paranoia_level = 2

inst.send_scpi_cmd('*CLS; *RST')

inst.send_scpi_cmd(':FREQ:RAST {0}'.format(2500e6))
inst.send_scpi_cmd(':INT X{0}'.format(DUC_INTERP))
inst.send_scpi_cmd(':MODE DUC')
inst.send_scpi_cmd(':IQM ONE')
inst.send_scpi_cmd(':NCO:CFR1 {0}'.format(DUC_NCO))
inst.send_scpi_cmd(':NCO:SIXD1 ON') # ON|OFF
inst.send_scpi_cmd(':ROSC:SOUR INT')
inst.send_scpi_cmd(':FREQ:RAST {0}'.format(SCLK))

inst.send_scpi_cmd(':INST:CHAN {0}'.format(RDOUT_CH))
inst.send_scpi_cmd(':OUTP:VOLT {0}'.format(1))
inst.send_scpi_cmd(':INIT:CONT ON')
inst.send_scpi_cmd(':TRAC:DEL:ALL')

resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)


# CREATE COMPLEX GAUSSIAN PULSE ===============================================
fs = SCLK
ts = 1 / fs
fc = 0

e, i, q = gauss_env(GAUS_PW, WAVE_TIME, fs, fc, \
    interp=DUC_INTERP,phase=GAUS_PHASE,\
    direct=False,direct_lo=0, mode=16, SQP=False)

N = e.size
t = np.linspace(-N*ts/2, N*ts/2, N, endpoint=False)


tns = t * 1e9 * DUC_INTERP

# CREATE WAVE =================================================================
wave = np.zeros(2*N)
tp = np.linspace(-1, 1, 2*N, endpoint=False)

wave[::2]= i
wave[1::2]= q

wave = [x*half_dac for x in wave]
wave = [x + half_dac for x in wave]
wave = np.round(wave)
wave = np.clip(wave, 0, max_dac)


if dac_mode == 16:
    wave = wave.astype(np.uint16)
else:
    wave = wave.astype(np.uint8)

# DOWNLOAD WAVEFORMS =========================================================
# download it to segment
inst.send_scpi_cmd(':INST:CHAN {0}'.format(1))
inst.send_scpi_cmd(':TRAC:DEF {0},'.format(1) + str(wave.size))
inst.send_scpi_cmd(':TRAC:SEL {0}'.format(1))

inst.write_binary_data(':TRAC:DATA', wave)

# play the first segment ( for debug )
inst.send_scpi_cmd(':SOUR:FUNC:MODE:SEGM 1')
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

# DC WAVE =====================================================================
dc_wave = np.zeros(2*N)
dc_wave = [x + half_dac for x in dc_wave]

if dac_mode == 16:
    dc_wave = np.array(dc_wave, dtype=np.uint16)
else:
    dc_wave = np.array(dc_wave, dtype=np.uint8)
    

    
# download it to segment 2 of channel 1
inst.send_scpi_cmd(':INST:CHAN {0}'.format(1))
inst.send_scpi_cmd(':TRAC:DEF {0},'.format(2) + str(dc_wave.size))
inst.send_scpi_cmd(':TRAC:SEL {0}'.format(2))
print('downloaded DC segment {0} in size of {1} to channel {2}'.format(2,dc_wave.size,RDOUT_CH))

inst.write_binary_data(':TRAC:DATA', dc_wave)

resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

# CREATE AND DOWNLOAD TASK TABLE TO CHANNEL 1 =================================
# QUESTION: WHAT IS A TASK TABLE
tasklen = 2

#Select channel
inst.send_scpi_cmd(':INST:CHAN {0}'.format(1))
inst.send_scpi_cmd(':TASK:COMP:LENG {0}'.format(tasklen))

inst.send_scpi_cmd(':TASK:COMP:SEL 1')
inst.send_scpi_cmd(':TASK:COMP:ENAB CPU')                            # CPU trigger is the task enable
inst.send_scpi_cmd(':TASK:COMP:SEGM {0}'.format(2))                  # play segment 2
inst.send_scpi_cmd(':TASK:COMP:IDLE:LEV {0}'.format(task_half_dac))  # DC level while waiting to a trigger
inst.send_scpi_cmd(':TASK:COMP:NEXT1 {0}'.format(2))                 # the next task is 2

inst.send_scpi_cmd(':TASK:COMP:SEL 2')
inst.send_scpi_cmd(':TASK:COMP:SEGM {0}'.format(1))                  # play segment 1
inst.send_scpi_cmd(':TASK:COMP:IDLE:LEV {0}'.format(task_half_dac))  # DC level while waiting to a trigger
inst.send_scpi_cmd(':TASK:COMP:DTRigger ON')                         # issue a trigger to the ADC at start of segment
inst.send_scpi_cmd(':TASK:COMP:NEXT1 {0}'.format(1))                 # the next task is 1
     
    
inst.send_scpi_cmd(':TASK:COMP:WRIT')
print('Downloading Task table to channel {0}'.format(RDOUT_CH))

inst.send_scpi_cmd(':INST:CHAN {0}'.format(RDOUT_CH))
inst.send_scpi_cmd(':OUTP ON')
inst.send_scpi_cmd('FUNC:MODE TASK')
inst.send_scpi_cmd('*TRG')

resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

# SETUP DIGITIZER =============================================================
# Setup the digitizer in two-channels mode
inst.send_scpi_cmd(':DIG:MODE DUAL')

# Set DDC mode to complex
inst.send_scpi_cmd(':DIG:DDC:MODE COMPlex')

# Set center frequency of channel 1
inst.send_scpi_cmd(':DIG:DDC:CFR1 {0}'.format(DDC_NCO))

# Set SCLK digitizer 
inst.send_scpi_cmd(':DIG:FREQ {0}'.format(DIG_SCLK))

# Set SYNC to SYSREF for phase coherance 
#inst.send_scpi_cmd(':DIG:DDC:CLKS AWG')

# Allocate capture memory according to number of frame and frame length in samples
cmd = ':DIG:ACQuire:FRAM:DEF {0},{1}'.format(FRAME_NUM, Frame_len)
inst.send_scpi_cmd(cmd)

# Select the frames for the capturing 
capture_first, capture_count = 1, FRAME_NUM
cmd = ":DIG:ACQuire:FRAM:CAPT {0},{1}".format(capture_first, capture_count)
inst.send_scpi_cmd(cmd)

# Enable capturing data from channel 1
inst.send_scpi_cmd(':DIG:CHAN:SEL 1')
inst.send_scpi_cmd(':DIG:CHAN:STATE ENAB')

# Full scale select
inst.send_scpi_cmd(':DIG:CHAN:RANGe {0}'.format(full_scale)) # { LOW | MEDium | HIGH}

# Select the internal-trigger as start-capturing trigger:
inst.send_scpi_cmd(':DIG:TRIG:SOURCE TASK{0}'.format(1))

# Enable capturing data from channel 2
inst.send_scpi_cmd(':DIG:CHAN:SEL 2')
inst.send_scpi_cmd(':DIG:CHAN:STATE ENAB')

# Full scale select
inst.send_scpi_cmd(':DIG:CHAN:RANGe {0}'.format(full_scale)) # { LOW | MEDium | HIGH}

# Select the internal-trigger as start-capturing trigger:
inst.send_scpi_cmd(':DIG:TRIG:SOURCE TASK{0}'.format(1))

# Set Trigger AWG delay to 0
inst.send_scpi_cmd(':DIG:TRIG:AWG:TDEL {0}'.format(4e-9))

# Clean memory 
inst.send_scpi_cmd(':DIG:ACQ:ZERO:ALL')

resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
print("Set Digitizer: DUAL mode; ADC Trigger")

resp = inst.send_scpi_query(':DIG:DDC:DEC?')
print(resp)

# SETUP DSP ===================================================================
# Select to store the FFT out data on memory 1
inst.send_scpi_cmd(':DSP:STOR1 FFTOut') # DIRect1 | DIRect2 | DSP1 | DSP2 | DSP3 | DSP4| FFTIn | FFTOut
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

# Select to store the FFT in data on memory 2
inst.send_scpi_cmd(':DSP:STOR2 FFTIn') # DIRect1 | DIRect2 | DSP1 | DSP2 | DSP3 | DSP4| FFTIn | FFTOut
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

# select which input is routed to the FFT
inst.send_scpi_cmd(':DSP:FFT:INPut DSP1') # DSP1 | DSP3 |DBUG
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

# FIR data
COE_FILE = r'Z:\Manuals\Proteus\UPDATE on 2022-01-18 (v2 DSP)\Scripts\sfir_51_tap.csv'
# Had to update this file location to that provided, old location was:
#r'D:\SVN\branches\Nitzan\FPGA\Proteus\implement\ip_repo\adc_ctrl\src\sfir_51_tap.csv'
mem = pack_fir_data(COE_FILE)



inst.send_scpi_cmd(':DSP:FIR:SEL I1') # I1|Q1|I2|Q2|DBUGI|DBUGQ
inst.send_scpi_cmd(':DSP:FIR:BYPass OFF')
inst.write_binary_data(':DSP:FIR:DATA', mem)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

inst.send_scpi_cmd(':DSP:FIR:SEL Q1') # I1|Q1|I2|Q2|DBUGI|DBUGQ
inst.send_scpi_cmd(':DSP:FIR:BYPass OFF')
inst.write_binary_data(':DSP:FIR:DATA', mem)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

# ACQUIRE SIGNALS INTO MEMORY =================================================
# Stop the digitizer's capturing machine (to be on the safe side)
inst.send_scpi_cmd(':DIG:INIT OFF')

# Start the digitizer's capturing machine
inst.send_scpi_cmd(':DIG:INIT ON')
print("Waiting to recive enter to generate trigger - press Enter to start trigger")
#input()

inst.send_scpi_cmd('*TRG')


time.sleep(2)
resp = inst.send_scpi_query(':DIG:ACQuire:FRAM:STAT?')
print('captured {0} frames'.format(resp[6:]))
numFramesRx = int(resp[6:])

# READ ALL CAPTURED FRAMES ====================================================
# Choose which frames to read (all in this example)
inst.send_scpi_cmd(':DIG:DATA:SEL ALL')

# Choose what to read 
# (only the frame-data without the header in this example)
inst.send_scpi_cmd(':DIG:DATA:TYPE FRAM')

# Get the total data size (in bytes)
resp = inst.send_scpi_query(':DIG:DATA:SIZE?')
num_bytes = np.uint32(resp)
print('Total size in bytes: ' + resp)
print()

# Read the data that was captured by channel 1:
inst.send_scpi_cmd(':DIG:CHAN:SEL 1')

wavlen = num_bytes // 2

wav1 = np.zeros(wavlen, dtype=np.uint32)
# the FFT size is 1024 for I and 1024 for Q so we take only the first 2048 samples
wav1 = wav1[:2048]

rc = inst.read_binary_data(':DIG:DATA:READ?', wav1, num_bytes)

resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
print("read data from DDR1")

# Read the data that was captured by channel 2:
inst.send_scpi_cmd(':DIG:CHAN:SEL 2')

wavlen = num_bytes // 2

wav2 = np.zeros(wavlen, dtype=np.uint32)
# the FFT size is 1024 for I and 1024 for Q so we take only the first 2048 samples
wav2 = wav2[:2048]

rc = inst.read_binary_data(':DIG:DATA:READ?', wav2, num_bytes)

resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
print("read data from DDR2")

# PLOT ========================================================================
totlen = 1024
x = range(totlen)

wave1_i = np.zeros(totlen, dtype=np.uint32)
wave1_q = np.zeros(totlen, dtype=np.uint32)

wave1_q = wav1[::2]
wave1_i = wav1[1::2]

pdbm,f = convertFftRawDataTodBm(wave1_i,wave1_q,ADCFS,DIG_SCLK,16)
pdbm = smooth(pdbm,15,'hanning')
pdbm = pdbm[14:]




wave2_i = np.zeros(totlen, dtype=np.uint32)
wave2_q = np.zeros(totlen, dtype=np.uint32)

wave2_q = wav2[::2]
wave2_i = wav2[1::2]

i2,q2 = convertTimeRawDataTomV(wave2_i,wave2_q,ADCFS)

fig, axs = plt.subplots(2,1)
fig.set_figheight(16)
fig.set_figwidth(15)
axs[0].plot(x, i2, '-',x, q2, '-')
axs[0].set_title('Time domain')
axs[0].set_xlabel('Samples')
axs[0].set_ylabel('Amp [mV]')
axs[1].plot(f, pdbm, '-')
axs[1].set_title('Frequency domain')
axs[1].set_xlabel('Frequency [MHz]')
axs[1].set_ylabel('Power [dBm]')
plt.show()

# READ DEBUG REGISTERS ========================================================
if Debug == True :
    channb = 1
    cmd = ':INST:CHAN {0}; :SYST:INF:REG?'.format(channb)
    html_str = inst.send_scpi_query(cmd, max_resp_len=2000000)
    #print(html_str)
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
        url = 'file://' + f.name
        f.write(html_str)
    webbrowser.open(url)

# CLOSE CONNECTION ============================================================
inst.close_instrument()
admin.close_inst_admin()