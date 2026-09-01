OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

x q[0];
y q[1];

c[0] = measure q[0];
c[1] = measure q[1];
