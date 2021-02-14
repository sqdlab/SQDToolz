import numpy as np

class WaveformModulation:
    def modify_waveform(self, wfm_pts, fs, t0, ch_index):
        assert False, "WaveformModulation classes must implement a modify_waveform function."

class WM_SinusoidalIQ(WaveformModulation):
    def __init__(self, name, iq_frequency, iq_amplitude = 1.0):
        self._name = name
        self._iq_frequency = iq_frequency
        self._iq_amplitude = iq_amplitude   #Given as the raw output voltage (should usually set the envelopes to unity amplitude in this case)
        self._iq_phase = 0.0                #Added onto both the cosine and sine terms
        self._iq_amplitude_factor = 1.0     #Defined as a = Q/I amplitudes and the factor 'a' is multiplied onto the Q-channel waveform 
        self._iq_phase_offset = 0.0         #Defined as the phase to add to the Q (sine) term
        self._iq_dc_offsets = (0.0, 0.0)
        self._iq_reset_phase = True         #If True, the phases of the cosine and sine waves are reset to zero after every waveform segment.

    @property
    def Name(self):
        return self._name

    @property
    def IQFrequency(self):
        return self._iq_frequency
    @IQFrequency.setter
    def IQFrequency(self, val):
        self._iq_frequency = val

    @property
    def IQPhase(self):
        return self._iq_phase
    @IQPhase.setter
    def IQPhase(self, val):
        self._iq_phase = val

    @property
    def IQAmplitude(self):
        return self._iq_amplitude
    @IQAmplitude.setter
    def IQAmplitude(self, val):
        self._iq_amplitude = val

    @property
    def IQAmplitude(self):
        return self._iq_amplitude
    @IQAmplitude.setter
    def IQAmplitude(self, val):
        self._iq_amplitude = val

    @property
    def IQAmplitudeFactor(self):
        return self._iq_amplitude_factor
    @IQAmplitudeFactor.setter
    def IQAmplitudeFactor(self, val):
        self._iq_amplitude_factor = val

    @property
    def IQPhaseOffset(self):
        return self._iq_phase_offset
    @IQPhaseOffset.setter
    def IQPhaseOffset(self, val):
        self._iq_phase_offset = val

    @property
    def IQdcOffset(self):
        return self._iq_dc_offsets
    @IQdcOffset.setter
    def IQdcOffset(self, val):
        self._iq_dc_offsets = val

    @property
    def IQResetPhase(self):
        return self._iq_reset_phase
    @IQResetPhase.setter
    def IQResetPhase(self, boolVal):
        #TODO: Add type+error checking to all the boolVal, val etc...
        self._iq_reset_phase = boolVal

    def set_IQ_parameters(self, amp = 1.0, phase = 0.0, dc_offset = (0.0, 0.0), amplitude_factor = 1.0, phase_offset = 0.0):
        self.IQAmplitude = amp
        self.IQPhase = phase
        self.IQdcOffset = dc_offset
        self.IQAmplitudeFactor = amplitude_factor
        self.IQPhaseOffset = phase_offset        

    def modify_waveform(self, wfm_pts, fs, t0, ch_index):
        if self.IQResetPhase:
            t_vals = np.arange(wfm_pts.size) / fs
        else:
            t_vals = (np.arange(wfm_pts.size) + t0) / fs
        if ch_index == 0:   #I-Channel
            return wfm_pts * self.IQAmplitude * np.cos(2 * np.pi * self.IQFrequency * t_vals + self.IQPhase) + self.IQdcOffset[0]
        elif ch_index == 1: #Q-Channel
            return wfm_pts * self.IQAmplitude * self.IQAmplitudeFactor * np.sin(2 * np.pi * self.IQFrequency * t_vals + self.IQPhase + self.IQPhaseOffset) + self.IQdcOffset[1]
        else:
            assert False, "Channel Index must be 0 or 1 for I or Q respectively."

    def _get_current_config(self):
        ret_dict = {}
        ret_dict["IQ Frequency"] = self._iq_frequency
        ret_dict["IQ Amplitude"] = self._iq_amplitude
        ret_dict["IQ Phase"] = self._iq_phase
        ret_dict["IQ Amplitude Factor"] = self._iq_amplitude_factor
        ret_dict["IQ Phase Offset"] = self._iq_phase_offset
        ret_dict["IQ DC Offset"] = self._iq_dc_offsets
        ret_dict["IQ Reset Phase"] = self._iq_reset_phase
        return ret_dict

    def _set_current_config(self, dict_config, instr_obj = None):
        for cur_key in ["IQ Frequency", "IQ Amplitude", "IQ Phase", "IQ Amplitude Factor", "IQ Phase Offset", "IQ DC Offset", "IQ Reset Phase"]:
            assert cur_key in dict_config, "Configuration dictionary does not have the key: " + cur_key
        
        self._iq_frequency = dict_config["IQ Frequency"]
        self._iq_amplitude = dict_config["IQ Amplitude"]
        self._iq_phase = dict_config["IQ Phase"]
        self._iq_amplitude_factor = dict_config["IQ Amplitude Factor"]
        self._iq_phase_offset = dict_config["IQ Phase Offset"]
        self._iq_dc_offsets = dict_config["IQ DC Offset"]
        self._iq_reset_phase  = dict_config["IQ Reset Phase"]
