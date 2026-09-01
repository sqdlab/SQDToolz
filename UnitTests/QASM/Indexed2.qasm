OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit q1;
qubit q2;
bit c1;
bit c2;

x q1;
y q1;

reset q1;
x q1;
y q2;

delay[0] q1, q2;
c1 = measure q1;
c2 = measure q2;
