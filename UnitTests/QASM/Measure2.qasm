OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

x q[0];
y q[0];

reset q;
x q[0];
y q[1];

delay[0] q;
c = measure q;
