OPENQASM 3.0;
include "ZI_test_QASM_qelib1.inc";

qubit q;
qubit q2;
bit[2] c;

cal {
    float ampl = 0.358;
    waveform wfm_envelope = load_numpy_encoded(0x789C9BEC17EA1B10C9C850C650AD9E925A9C5CA46EA5A06E936C68A6AEA3A09E965F54529498179F5F94920A92704BCC294E058A17672416A402F91AA63A9A3A0AB50AE4032E0630F8600FA1191C50F91FF63360051C5075020E68120E00F09C2091);
    // waveform custom_wfm = [
    //     1.0 + 0.0im,
    //     0.8 + 0.2im,
    //     0.3 + 0.5im,
    //     0.0 + 0.0im
    // ];
}

cal
{
    ampl = 0.40;
}

defcal rx(angle leAngle) $1 {
    float offset = 0.5;
    play(
        drive($1),
        gaussian(20ns, 0.5*leAngle+offset)
    );
    shift_phase(drive($1), pi/2);
    play(
        flux($1),
        gaussian(35ns, 0.5*leAngle+offset)
    );
    play(
        drive($1),
        wfm_envelope
    );
}
defcal x $0 {
    play(
        drive($0),
        gaussian(20ns, 0.358)
    );
}


float[64] a = 5;
a = 0;
angle vtheta = pi / 4;

rx(vtheta) q;
complex[float] f = 1+2im;

reset q;

for int i in [0:2] {
    angle vtheta = pi / (i + 2); // Shadows the outer vtheta
    for int m in [0:i]
    {
        rx(vtheta) q;
    }
    ry(vtheta) q;
    rx(vtheta/2) q2;
    delay[i*20ns] q;
}

rx(vtheta) q; // Refers to the outer vtheta again

delay[0]  q, q2;
c[0] = measure q;
c[1] = measure q2;
