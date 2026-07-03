OPENQASM 3;
include 'zi_test_qasm_qelib1.inc';

bit[4] c;
qubit[4] q;

x q[1];
// h q[0];
y q[0];
y q[2];
x q[0];
x q[3];
t q[3];
y q[3];
x q[3];
ctrl @ z q[2], q[3];
delay[100ns] q[2], q[3];
y q[1];
// h q[2];
y q[2];
delay[10ns]  q[0];
delay[0]  q[2], q[3];
y q[1];

// c[0] = measure q[0];
// c[1] = measure q[1];
c[2] = measure q[2];
c[3] = measure q[3];
