OPENQASM 3;
include 'zi_test_qasm_qelib1.inc';

bit[2] c;
qubit[2] q;

z q[0];
rx(pi/2) q[0];

z q[1];
ry(pi/2) q[1];

ctrl @ z q[0], q[1];

z q[1];
ry(pi/2) q[1];

delay[0]  q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
