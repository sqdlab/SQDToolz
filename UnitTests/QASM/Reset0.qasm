OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

reset q[0];
rx(pi) q[0];

c[0] = measure q[0];
