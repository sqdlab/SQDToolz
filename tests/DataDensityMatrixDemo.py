import numpy as np
import itertools
from sqdtoolz.Utilities.DataDensityMatrix import DataDensityMatrix
import functools

shots, ddm, fidelity = DataDensityMatrix.generate_simulated_shots(3, np.array([1,0,0,0,0,0,0,1]) / np.sqrt(2), 1024, [np.array([[0.98, 0.10], [0.02, 0.90]])]*3)
print(f"{fidelity*100:.4g}%")

