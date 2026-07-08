from sqdtoolz.Utilities.ParserOpenQASM import ParserOpenQASM
import matplotlib.pyplot as plt

poqasm = ParserOpenQASM('tests/ZI_test_QASM.qasm',['tests/'])
poqasm.plot()
plt.show()
a=0