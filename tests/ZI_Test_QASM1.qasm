OPENQASM 3.0;
include "ZI_test_QASM_qelib1.inc";

qubit q;
qubit q2;

float[64] a = 5;
a = 0;
angle vtheta = pi / 4;

rx(vtheta) q;
complex[float] f = 1+2im;

for int i in [0:2] {
    angle vtheta = pi / (i + 2); // Shadows the outer vtheta
    for int m in [0:i]
    {
        rx(vtheta) q;
    }
    ry(vtheta) q;
    rx(vtheta/2) q2;
    delay[i*20ns] q;
}

rx(vtheta) q; // Refers to the outer vtheta again
