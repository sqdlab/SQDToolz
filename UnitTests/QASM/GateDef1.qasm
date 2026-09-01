OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

gate s a { rz(pi/2) a; }
gate sDag a { rz(0-pi/2) a; }
gate cy a,b { sDag b; cx a,b; s b; }

x q[0];
cy q[0], q[1];

delay[0] q;
c[0] = measure q[0];
c[1] = measure q[1];

