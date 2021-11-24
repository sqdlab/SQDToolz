from sqdtoolz.HAL.Processors.ProcessorCPU import ProcNodeCPU

class CPU_ConstantArithmetic(ProcNodeCPU):
    def __init__(self, constant=0, operation='+', channels=None):
        '''
        General function that adds, subtracts, multiples or divides all data in particular channels by a constant.

        Inputs:
            - constant - the constant (float)
            - operation - '+', '-', '*', '/', '%'
            - channels - List of channels to operate on. None means all channels
        '''
        self.operations = ['+', '-', '*', '/', '%']
        self.constant = constant
        assert operation in self.operations, f"The operation {operation} is not permitted. Choose from {self.operations}"
        self.operation = operation
        self.channels = channels

    @classmethod
    def fromConfigDict(cls, config_dict):
        return cls(config_dict['Constant'], config_dict['Operation'], config_dict['Channels'])

    def perform_arithmetic(self, data, operation, constant):
        if operation == '+':
            data += constant
        elif operation == '-':
            data -= constant
        elif operation == '*':
            data *= constant
        elif operation == '/':
            data /= constant
        elif operation == '%':
            data = data % constant
        return data
    
    def process_data(self, data_pkt, **kwargs):
        assert self.operation in self.operations, f"The operation {self.operation} is not permitted. Choose from {self.operations}"

        #Process means on a per-channel basis
        for ch_ind, cur_ch in enumerate(data_pkt['data'].keys()):
            if self.channels == None:
                data_pkt['data'][cur_ch] = self.perform_arithmetic(data_pkt['data'][cur_ch], self.operation, self.constant)
            elif ch_ind in self.channels:
                data_pkt['data'][cur_ch] = self.perform_arithmetic(data_pkt['data'][cur_ch], self.operation, self.constant)

        return data_pkt

    def _get_current_config(self):
        return {
            'Type'  : self.__class__.__name__,
            'Constant' : self.constant,
            'Operation' : self.operation,
            'Channels' : self.channels
        }
