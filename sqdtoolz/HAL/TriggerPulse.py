
class TriggerType:
    def __init__(self):
        pass

    def get_trigger_times(self, input_trig_pol=1):
        assert False, "The class implementing a TriggerType must implement the get_trigger_times function."

    def get_trigger_params(self):
        assert False, "The class implementing a TriggerType must implement the get_trigger_params function."

class Trigger(TriggerType):
    def __init__(self, parent, name, instr_trig_output_channel):
        '''
        Initialises a Trigger object that can be used to build triggering relationships between instruments (that is,
        this object can be used as a trigger source to trigger other instruments).

        Inputs:
            - name - Name of the trigger (typically that given by the instrument - e.g. 'M1', 'A' etc...)
            - instr_trig_output_channel - An instrument or module object concerning the trigger output. It can be in fact
                                          any object that implements all the required properties to be trigger-compatible. 
        '''
        self._instrTrig = instr_trig_output_channel
        self._name = name
        self._parent = parent

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
        return self._instrTrig.TrigEnable
    @TrigEnable.setter
    def TrigEnable(self, boolVal):
        self._instrTrig.TrigEnable = boolVal

    def _get_instr_trig_src(self):
        '''
        Used by TimingConfiguration to backtrack through all interdependent trigger sources (i.e. traversing up the tree)
        '''
        return self._parent.get_trigger_source()
    def _get_instr_input_trig_edge(self):
        #Sometimes the object (e.g. a DDG) may not have an input trigger...
        if (hasattr(self._parent,'InputTriggerEdge')):
            return self._parent.InputTriggerEdge    #Parent implementing this should have a preferred edge
        else:
            return 0

    def get_trigger_times(self, input_trig_pol=1):
        if input_trig_pol == 0:
            if self.TrigPolarity == 0:
                return [self.TrigPulseDelay]
            else:
                return [self.TrigPulseDelay + self.TrigPulseLength]
        elif input_trig_pol == 1:
            if self.TrigPolarity == 0:
                return [self.TrigPulseDelay + self.TrigPulseLength]
            else:
                return [self.TrigPulseDelay]
        else:
            assert False, "Trigger polarity must be 0 or 1 for negative or positive edge/polarity."

    def _get_current_config(self):
        return {self.name : {
            'TrigPulseDelay'  : self.TrigPulseDelay,
            'TrigPulseLength' : self.TrigPulseLength,
            'TrigPolarity'  : self.TrigPolarity,
            'TrigEnable'    : self.TrigEnable
        }}

    def _set_current_config(self, dict_config):
        '''
        Set the trigger parameters from a dictionary. Note that this must be the dictionary value returned by _get_current_config - that is,
        the dictionary should only have the keys of the parameters to be set (e.g. TrigPulseDelay, TrigPulseLength, TrigPolarity and TrigEnable)

        Input:
            - dict_config - Dictionary of trigger parameters.
        '''
        self.TrigPulseDelay = dict_config['TrigPulseDelay']
        self.TrigPulseLength = dict_config['TrigPulseLength']
        self.TrigPolarity = dict_config['TrigPolarity']
        self.TrigEnable = dict_config['TrigEnable']

    def get_trigger_params(self):
        return {
                'TriggerHAL' : self._parent.Name,
                'TriggerID' : self.name,
                'TriggerCH' : 0,  #Defaults to 0
            }


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
    

    
