from qcodes import Instrument, InstrumentChannel
from ctypes import *
import os

class ATTENVaunixChannel(InstrumentChannel):
    def __init__(self, parent:Instrument, name:str, index:int) -> None:
        super().__init__(parent, name)
        self._index = index
        self._parent = parent

        self.add_parameter('attenuation', label='Attenuation', unit='dB',
                           get_cmd=self._get_atten,
                           set_cmd=self._set_atten)

    def _set_atten(self, val):
        #Select the channel
        channel = self._parent._vnx.fnLDA_SetChannel(self._parent.Devices[self._parent.dev_ind], self._index)
        assert channel == 0, f'Vaunix attenuator SetChannel returned an error {channel}'

        attenuation = val / .05
        atten = round(attenuation)
        
        #Set the attenuation
        result = self._parent._vnx.fnLDA_SetAttenuationHR(self._parent.Devices[self._parent.dev_ind], int(atten))
        assert result == 0, f'SetAttenuationHR returned error {result}'
    def _get_atten(self):
        #Select channel
        channel = self._parent._vnx.fnLDA_SetChannel(self._parent.Devices[self._parent.dev_ind], self._index)
        #Get channel attenuation
        result = self._parent._vnx.fnLDA_GetAttenuationHR(self._parent.Devices[self._parent.dev_ind])

        assert result >= 0, f'GetAttenuationHR returned error {result}'
        return result / 20
        
    @property
    def Attenuation(self):
        return self.attenuation()
    @Attenuation.setter
    def Attenuation(self, val):
        self.attenuation(val)


class ATTEN_Vaunix(Instrument):
    '''
    Dummy driver to emulate a Generic Microwave Source instrument.
    '''
    def __init__(self, name, dev_ind=0, **kwargs):
        super().__init__(name, **kwargs) #No address...

        #Change if it is not Windows!
        dll_loc = os.path.abspath(os.path.dirname(__file__)).replace('\\','/') + '/Dependencies/VNX_attenWIN64.dll'
        self._vnx = cdll.LoadLibrary(dll_loc)
        self._vnx.fnLDA_SetTestMode(False)
        DeviceIDArray = c_int * 20
        self.Devices = DeviceIDArray()
        self.dev_ind = dev_ind

        #TODO: Use serial numbers to enumerate this?!
        self.Devices[self.dev_ind]

        # GetNumDevices will determine how many LDA devices are availible
        numDevices = self._vnx.fnLDA_GetNumDevices()
        #print(str(numDevices), ' device(s) found')

        # GetDevInfo generates a list, stored in the devices array, of
        # every availible LDA device attached to the system
        # GetDevInfo will return the number of device handles in the array
        dev_info = self._vnx.fnLDA_GetDevInfo(self.Devices)
        #print('GetDevInfo returned', str(dev_info))

        # GetSerialNumber will return the devices serial number
        ser_num = self._vnx.fnLDA_GetSerialNumber(self.Devices[self.dev_ind])
        #print('Serial number:', str(ser_num))

        #InitDevice wil prepare the device for operation
        init_dev = self._vnx.fnLDA_InitDevice(self.Devices[self.dev_ind])
        #print('InitDevice returned', str(init_dev))

        #GetNumChannels will return the number of channels on the device
        self.num_channels = self._vnx.fnLDA_GetNumChannels(self.Devices[self.dev_ind])
        if self.num_channels < 1:
            self.num_channels = 1

        # Output channels added to both the module for snapshots and internal output sources for use in queries
        self._source_outputs = {}
        for ch_index in range(1,self.num_channels+1):
            ch_name = f'CH{ch_index}'
            cur_channel = ATTENVaunixChannel(self, ch_name, ch_index)
            self.add_submodule(ch_name, cur_channel)
            self._source_outputs[ch_name] = cur_channel

    def get_output(self, identifier):
        return self._source_outputs[identifier]

    def get_all_outputs(self):
        return [(x,self._source_outputs[x]) for x in self._source_outputs]

def runme():
    myVaunix = ATTEN_Vaunix("bob")
    myVaunix.CH1.Attenuation = 0
    a = 0


if __name__ == '__main__':
    runme()

