import numpy as np
from sqdtoolz.Utilities.TimingPlots import*

class WaveformGeneric:
    def __init__(self, waveform_names, digital_pulses):
        self.waveforms = {x:[] for x in waveform_names}
        self.digitals = {x:{} for x in digital_pulses}

    def set_waveform(self, waveform_name, waveform_data):
        self.waveforms[waveform_name] = waveform_data

    def set_digital_segments(self, signal_name, ref_waveform_name, segments, active_on_state=1):
        assert signal_name in self.digitals, f'Signal name {signal_name} not declared in digital pulses.'

        #Note that 1 implies ON (can be inverted during translation)
        self.digitals[signal_name] = {
            'refWaveform' : ref_waveform_name,
            'segments' : segments,
            'active_on_state' : active_on_state
        }

    def set_digital_trigger(self, signal_name, trig_length, trig_delay=0.0, trig_polarity=1):
        assert signal_name in self.digitals, f'Signal name {signal_name} not declared in digital pulses.'

        #Note that 1 implies ON (can be inverted during translation)
        self.digitals[signal_name] = {
            'trig_length' : trig_length,
            'trig_delay' : trig_delay,
            'trig_polarity' : trig_polarity
        }


