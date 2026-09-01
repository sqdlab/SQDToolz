OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

x q[0];
delay[0] q[0], q[1];
y q[1];

delay[0] q;
c[0] = measure q[0];
c[1] = measure q[1];