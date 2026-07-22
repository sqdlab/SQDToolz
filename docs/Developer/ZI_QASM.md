# Compatibility with QASM Parsing

The OpenQASM3 parser has a scheduling layer that adds delays so that the sections nicely align when required (e.g. two-qubit gates, multi-qubit delays etc.). This requires querying of the gate-times enabled via functions embedded within:

- `ZIQubit` - to query the single-qubit gate times
- `QuantumOperations` class (can be accessed via the associated `QuantumElement` class) - to query the two-qubit gate times

To enforce this, the classes must inherit the `QASMCompatible` abstract class. Ideally the low-level drivers should inherit this (i.e. custom `QuantumElement` classes); the individual qubit classes shall be absorbed into the `ZIQubit` HAL. Same is done for the `ZIQuantumElement` but it will just pass onto the `QuantumElement` classes. Internally it has a few constructs:

- There is a `ScheduleParametersBase` that is passed onto `ParserOpenQASM` when creating schedules. This is used to query the required parameters such as gate durations etc.
- There is a `ScheduleParametersSoftQPUZI` class that is used to gobble up `softQPU` objects and extract said qubit gate parameters as required for scheduling. Internally this is set to call the `QASMCompatible` methods within the individual qubits/couplers...

In summary:

- `ParserOpenQASM` parses the `.qasm` file and schedules the timing. It can plot or tabulate the gate sequences. It can also check for ZI compatibility.
- The `oqasm_scheduled_qubits` ZI workflow is a lightweight wrapper that translates the scheduled sequence into QDSL
- `ExpZIQASM` is the main user interface that uses `oqasm_scheduled_qubits` to execute a `.qasm` file...

The qubits in `ExpZIQASM` are mapped onto hardware either by default in the ordering supplied by `qubit_ids` or via a custom mapping set via the `set_qubit_reg_to_ZI_mappings(...)` function.

## Alignment/Timing

The scheduler in `ParserOpenQASM` adds bubbles (i.e. delays to pad the section) when sections must align (e.g. a two-qubit gate). To manually align multiple qubits so that future gates all start from that point, use the multi-qubit delay instruction as specified by the standard (e.g. `delay[0] q1, q2;`). The delay value can be zero to enforce just the alignment.

## For Loops

So *OpenQASM3* specifies that `for` loops are to be executed as a sequential instruction. That is, there cannot be two parallel `for` loops; this aligns with the hardware restriction on *LabOneQ* as well. Thus, a `for` loop will be considered as a single section that slots in sequentially with the other instructions. However, there cannot be two such `for` loops being a child of the outer `for` loop. That is, in summary:

- For loops in *OpenQASM3* are done sequentially and cannot have two loops in parallel - just like in `LabOneQ`
- For loops can have two child loops within its inner level of nesting - this won't be supported as it isn't supported in `LabOneQ` (each loop can have only one child)
- To dynamically add bubbles/delays within a loop, an arithmetic offset/scaling variable is created alongside the main one and they are both swept together.

## Pulse-level control

The idea is to use *OpenPulse* but with heavy abuse of its `extern` commaand to get the frame objects for the respective qubits etc. This means that the boilerplate code on defining ports and frames can be omitted. There are 3 `extern` commands that are added implicitly:

```cpp
extern drive(qubit) -> frame;
extern flux(qubit) -> frame;
extern measure(qubit) -> frame;
```

That is, for any qubit, one may query the drive, flux or measure lines by using these three functions. After that, the `play` functions can be used in a straightforward manner.


