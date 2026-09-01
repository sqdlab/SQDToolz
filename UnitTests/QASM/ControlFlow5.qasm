OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

int fac = 2;
fac **= 3;
float fac2;
fac2 = 15.0/3**2;

x q[0];

for int m in [0:2:5] {
    float fac = m*2;
    for int n in [0:m]
    {
        x q[1];
    }
    delay[fac*1ns] q[1];
    x q[1];
    delay[fac2*1ns] q[1];
    x q[1];
    delay[m*3*1ns] q[1];
    x q[1];
}

delay[fac*1ns] q;
cz q[0], q[1];

c[0] = measure q[0];
c[1] = measure q[1];
