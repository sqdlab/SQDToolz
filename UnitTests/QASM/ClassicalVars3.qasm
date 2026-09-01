OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

int fac = 8;

fac %= 5;

float fac2;
fac2 = 15.0;
fac2 -= 3;

duration a = 300ns;
a = 400ns - 1dt;

x q[0];
cz q[1], q[0];
y q[1];

delay[a/fac2+fac*-1dt] q;
x q[0];

delay[0] q;
c[0] = measure q[0];
c[1] = measure q[1];
