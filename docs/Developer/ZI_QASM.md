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

That is, for any qubit, one may query the drive, flux or measure lines by using these three functions. After that, the `play` functions can be used in a straightforward manner. Note that `play` functions in `cal` blocks are ignored (it will technically require ports/frames to even call `play`; there are not supported in this parser).

Note that `gatedef` must only use logical qubits while `defcal` only uses physical qubits. Thus, the execution is as follows in this example:
1. Parse the statement: `x q[1];`
2. Have a mapping external to the script: `q[1] → $1`
3. Check if it has a matching `defcal` for `x` on `$1`. If it does, execute the associated `defcal` otherwise, defer to the gate definition.

This should still work on portable scripts. For example, if there is a Bell State script with two logical qubits `q[2]`, one may map `q[0] → $3` etc. The `defcal` just needs to exist for `$3` etc. This way, the scripts can stay logically independent. Note that broadcast (zipped for multiple qubits) invocations are not supported at present.

The following waveforms are in-built (i.e. implicit `extern`):
- `gaussian(duration, amp, sigma)`
- `drag(duration, amp, sigma, beta)`
- `constant(duration, amp)`

To make ease of timing, the following alignment rules shall be enforced:
- All `play` functions within a `defcal` block start from the same time point (unless they are on the same line; in which case they play sequentially)
- All `play` functions from different `defcal` blocks must play sequentially.

Thus, if there was a `rx` on a drive line on a given qubit, and `cpl` on its flux line, these pulses must appear sequentially. If they were wrapped in the same `defcal` block then they play concurrently. The compiler implicitly adds a 

## Variable scoping

Just a reminder:
- Variables in the global scope or the scope exterior to `gatedef` blocks are not seen (i.e. only locally scoped variables)
- Similarly, `defcal` blocks can only see locally scoped variables and any variable declared within the `cal` blocks. Thus, variables declared within `defcal` blocks are unseen outside these blocks.
- Qubits can only be declared in the global scope

The following declaraitons can only appear in the global scope:
- `gate`
- `def`
- `defcal`
- `defcalgrammar`
- `extern`
- `include`
- `qubit`

In addition, the declarations cannot be duplicated within the same scope (can have a `gate` and a `def` with the same name as they occupy different namespaces). Thus, in terms of processing, the following steps are taken:
- A state machine gathers and tracks the scoping of current variables and discards them upon ending the current scope
- All for loops are unrolled if they have constructs within that make use of the looping variable/identifier (this is conducive with the default behaviour of *LabOneQ*; albeit, the CYCLIC/SEQUENTIAL averaging types do differ in behaviour, but only CYCLIC is taken as the default behaviour in the present parser as SEQUENTIAL breaks when there are multiple loops etc... Idea is to use manual Python loops outside the OpenQASM calls in those cases...)


OpenQASM scopes
---------------
global
  ├── block
  ├── for
  ├── if
  ├── def
  └── gate

Calibration scopes
------------------
cal (global calibration namespace)
  ├── cal block
  └── defcal

