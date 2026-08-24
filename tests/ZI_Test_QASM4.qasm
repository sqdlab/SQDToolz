OPENQASM 3.0;

cal {
}


include "stdgates_transmon_fixed_coupler.inc";

qubit[5] q;
bit[5] c;

h q[0];

h q[2];
delay[0] q[0], q[2];
cz q[0],q[2];
h q[0];

h q[1];
delay[0] q[0], q[2];
cz q[1],q[2];
h q[1];

delay[0] q[0], q[1], q[2];
c = measure q;
