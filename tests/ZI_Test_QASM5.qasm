OPENQASM 3.0;
include "stdgates_transmon_fixed_coupler.inc";
bit[2] c;
qubit[2] q;

rx(pi) q[0];
delay[0] q[0], q[1];
delay[0] q[0], q[1];
h q[1];
swap q[0], q[1];
// cx q[0], q[1];
// cx q[1], q[0];
// cx q[0], q[1];
ry(3*pi/2) q[1];
c[1] = measure q[1];
delay[0] q[0], q[1];
delay[0] q[0], q[1];
rx(pi/2) q[0];
delay[30ns] q[0];
c[0] = measure q[0];
gate id q {delay[25ns] q;}
