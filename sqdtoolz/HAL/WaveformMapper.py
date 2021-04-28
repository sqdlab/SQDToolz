
class WaveformMapper:
    def __init__(self):
        self.waveforms = {}
        self.digitals = {}

    def add_waveform(self, waveform_name, awg_hal_object_name):
        self.waveforms[waveform_name] = awg_hal_object_name

    def add_digital(self, signal_name, awg_marker_object):
        self.digitals[signal_name] = awg_marker_object
