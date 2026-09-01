OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

duration a = 300ns;
a = 400ns;

x q[0];
cz q[1], q[0];
y q[1];

delay[a*2+1e-9s] q;
x q[0];

delay[0] q;
c[0] = measure q[0];
c[1] = measure q[1];
