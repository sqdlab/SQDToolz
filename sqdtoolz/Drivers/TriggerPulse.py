
class Trigger:
    def __init__(self, name, instr_trig_output_channel):
        self._instrTrig = instr_trig_output_channel
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def TrigPulseDelay(self):
        return self._instrTrig.TrigPulseDelay
    @TrigPulseDelay.setter
    def TrigPulseDelay(self, len_seconds):
        self._instrTrig.TrigPulseDelay = len_seconds

    @property
    def TrigPulseLength(self):
        return self._instrTrig.TrigPulseLength
    @TrigPulseLength.setter
    def TrigPulseLength(self, len_seconds):
        self._instrTrig.TrigPulseLength = len_seconds

    @property
    def TrigPolarity(self):
        return self._instrTrig.TrigPolarity
    @TrigPolarity.setter
    def TrigPolarity(self, pol):
        self._instrTrig.TrigPolarity = pol

    @property
    def TrigEnable(self):
        return self._instr_ddg.TrigEnable
    @TrigEnable.setter
    def TrigEnable(self, boolVal):
        self._instr_ddg.TrigEnable = boolVal


class SyncTriggerPulse:
    def __init__(self, trig_len, enableGet, enableSet, trig_pol = 1, trigOutputDelay = 0.0):
        '''
        Represents a constant synchronisation trigger pulse outputted from any bench device (e.g. DDGs, AWGs etc...)

        Inputs:
            - trig_len - Length of trigger pulse (away from idle baseline) in seconds
            - enableGet - Getter function to check if the trigger output is enabled
            - enableSet - Setter function to set the output trigger (via True/False)
            - trig_pol - If one, the idle baseline is low and trigger is high (positive polarity). If zero, the idle baseline is high and the trigger is low (negative polarity)
            - trigOutputDelay - Output delay (in seconds) before the trigger pulse is set (by default it is mostly 0.0s) 
        '''

        self._trig_len = trig_len
        self._enableGet = enableGet
        self._enableSet = enableSet
        self._trig_pol = trig_pol
        self._trigOutputDelay = trigOutputDelay


    @property
    def TrigEnable(self):
        return self._enableGet()
    @TrigEnable.setter
    def TrigEnable(self, boolVal):
        self._enableSet(boolVal)

    @property
    def TrigPulseDelay(self):
        return self._trigOutputDelay  #Readonly for an output trigger pulse

    @property
    def TrigPulseLength(self):
        return self._trig_len  #Readonly for an output trigger pulse

    @property
    def TrigPolarity(self):
        return self._trig_pol  #Readonly for an output trigger pulse
    

    
