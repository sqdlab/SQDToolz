
// --- Standard rotations ---
// Rotation around X-axis
gate rx(theta) a { U(theta, -pi/2,pi/2) a; }
// rotation around Y-axis
gate ry(theta) a { U(theta,0,0) a; }
// rotation around Z axis
gate rz(phi) a { U(0,0,phi) a; }

// Pauli gate: bit-flip
gate x a { U(pi,0,pi) a; }
// Pauli gate: bit and phase flip
gate y a { U(pi,pi/2,pi/2) a; }
// Pauli gate: phase flip
gate z a { U(0,0,pi) a; }

// Clifford gate: Hadamard (i.e. (Y/2).(Z))
gate h a { z a; ry(pi/2) a; }

// 2-Qubit native CZ
gate cz a, b { ctrl @ z a, b; }

// Derived 2-Qubit CX
gate cx a,b { h b; cz a,b; h b; }
