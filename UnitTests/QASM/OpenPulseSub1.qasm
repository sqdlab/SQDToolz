OPENQASM 3;
include 'stdgates_transmon_fixed_coupler.inc';

qubit[2] q;
bit[2] c;

defcal x $2 {
    play(drive($2), gaussian(83ns, 0.5));
}

x q[0];
x q[1];

delay[0] q;
c[0] = measure q[0];
c[1] = measure q[1];
