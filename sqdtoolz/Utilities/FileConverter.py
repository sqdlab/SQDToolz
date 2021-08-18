from FileIO import FileIOReader
import os.path
from pathlib import Path
import sys

class FileConverter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = Path(filepath).stem
        self.folder_path = os.path.dirname(self.filepath)
        self.reader = FileIOReader(filepath)
    
    def _to_mma_array(self, conv_list):
        return 

    def toMathematica(self, destName=''):
        if destName == '':
            destFile = self.folder_path + "/" + self.filename + '.dat'
        else:
            destFile = destName
        with open(destFile, 'w') as outfile:
            outfile.write("{")
            #Parameter names
            outfile.write("{")
            for m, cur_param in enumerate(self.reader.param_names):
                outfile.write(f'\"{cur_param}\"')
                if m < len(self.reader.param_names) - 1:
                    outfile.write(",")
            outfile.write("},\n")
            #Parameter values
            outfile.write("{")
            for m, cur_param in enumerate(self.reader.param_vals):
                outfile.write("{")
                for p, cur_val in enumerate(self.reader.param_vals[m]):
                    outfile.write(f'{cur_val}')
                    if p < self.reader.param_vals[m].size - 1:
                        outfile.write(",")
                outfile.write("}")
            outfile.write("},\n")
            #Parameter data array
            arr = self.reader.get_numpy_array()
            outfile.write( str(arr.tolist()).replace('[','{').replace(']','}').replace('\n',',') )
            
            outfile.write("}\n")

# fc = FileConverter(r'data.h5')
# fc.toMathematica()
if __name__ == '__main__':
    if len(sys.argv) >= 2:
        fc = FileConverter(sys.argv[1])
        fc.toMathematica()

