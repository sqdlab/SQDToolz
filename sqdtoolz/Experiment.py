import qcodes as qc

class Experiment:
    def __init__(self, instr_config_file, save_dir, name=""):
        '''
        '''

        self.station = qc.Station(config_file=instr_config_file)

        #List of digital delay generators
        self._DDGs = []
        #List of arbitrary waveform generators
        self._AWGs = []
        #List of acquisition devices
        self._ACQs = []
        


    def run (self, sweep_vars=[]):
        pass


