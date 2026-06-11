# QASM Parsing

Before commit ID `6d4dbac`, the parsing was done by hand using `lex`/`yacc`. However, in order to easily update to newer grammar specifications to the exact letter prescribed by the OpenQASM3 standard, the ANTLR approach was adopted.

## Installing ANTLR toolkit on Ubuntu

Go to the [ANTLR4 website](https://www.antlr.org/download.html) and download the complete JAR (e.g. *antlr-4.13.2-complete.jar*) and move it to `/usr/local/lib` or alternatively run:

```bash
cd /usr/local/lib
sudo wget http://www.antlr.org/download/antlr-4.13.2-complete.jar
```

Now run:

```bash
cd /usr/local/bin
sudo nano antlr4
```

Fill it with:

```bash
#! /bin/bash
export CLASSPATH=".:/usr/local/lib/antlr-4.13.2-complete.jar:$CLASSPATH"
java -jar /usr/local/lib/antlr-4.13.2-complete.jar "$@"
```

and save the file. Finally, run:

```bash
sudo chmod +x antlr4
```

Running `antlr4` should work. ~~The installation script for SQDToolz additionally has `antlr4-python3-runtime`.~~ Okay given that openqasm3 is a package already in SQDToolz, this was adopted instead...

## Some notes on OpenQASM 3.0

Synchronisation is done via delay[0] on multiple qubits if required - i.e. [noting](https://openqasm.com/language/delays.html):

    A multi-qubit delay instruction is not equivalent to multiple single-qubit delay instructions. Instead a multi-qubit delay acts as a synchronization point on the qubits, where the delay begins from the latest non-idle time across all qubits, and ends simultaneously across all qubits.

The `barrier` instruction is only there to prevent optimisation by commutation reordering and/or collapsing/simplification of gates across the barrier. Thus, the `barrier` instruction does not do anything in the current state of the compiler.
