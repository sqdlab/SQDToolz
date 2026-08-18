import shutil
import os
import re
import openqasm3
import openpulse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatch
from sqdtoolz.Utilities.OpenQASM import ScheduleParametersBase, QASMCompatibleQubitSingle
import pandas as pd
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import bokeh
from bokeh.models import PanTool
from sqdtoolz.Utilities.FileJSON import SerialiseJSON
from enum import Enum, auto
from pathlib import Path
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous

class SQDQasmCommandType(Enum):
    GATE = auto()
    DELAY = auto()
    MEASURE = auto()
    RESET = auto()
    DEF_CAL = auto()
    END_BLOCK = auto()

class SQDQasmVisitor(openqasm3.visitor.QASMVisitor):
    def __init__(self, qreg_phys_mapping:dict):
        super().__init__()
        #The variables are stored as a stack for the scoping/shadowing. Idea is that it's a list of
        #dictionaries for each scoping level. Each dictionary has keys corresponding to the variable
        #names. The values are tuples with the type and value; e.g. [openqasm3.ast.AngleType, 1.34]
        #or [openqasm3.ast.FloatType, 1.34] where the latter specifies a float where its size (in bits)
        #lives within the object in the size attribute...
        self._variables_stack = [{}]
        self._qarg_stack = [qreg_phys_mapping]
        self._extra_mod_stack = []  #This is to cascade ctrl/negcrtl modifiers through multiple cascading functions! It'll push/pop the modifiers as it enters/leaves scope
        self._extra_mod_qubits = []
        #Similarly, the cal-block variables are stored in a different scope
        self._variables_cal_stack = [{}]
        # self._defs = {}
        self._gate_defs = {}
        self._defcals = {}
        self._commands = []
        self._qubits = {}
        self._bits = {}
        self._in_cal_blk = False
        self._in_defcal_blk = False
        self._qreg_phys_mapping = qreg_phys_mapping

    #Not required as includes are handled separately...
    # def visit_Include(self, node):
    #     node.filename
    #     print(f"Quantum register declared: {node.name} of size {node.size}")
    #     return super().visit_QuantumDeclaration(node)

    def enter_scope(self, with_scope_barrier=False):
        #Idea of with_scope_barrier is that it'll stop backtracking in variable resolution in cases like functions where
        #scope must be local.
        #This stack manipulation is FINE in this case as it's a static compilation sequence. That is, it is not a run-time
        #stack (i.e. the typical concern may occur with an exception that occurs after calling enter_scope and then but
        #before calling leave_scope, so on leaving this subroutine, it would leave the stack unpopped...), so any errors
        #will just fail compilation rather than continue runtime...
        if self._in_cal_blk:
            if with_scope_barrier:
                self._variables_cal_stack.append(None)
            self._variables_cal_stack.append({})
        else:
            if with_scope_barrier:
                self._variables_stack.append(None)
            self._variables_stack.append({})
    def leave_scope(self):
        if self._in_cal_blk:
            self._variables_cal_stack.pop()
            if self._variables_cal_stack[-1] == None:   #Remove any scoping barriers...
                self._variables_cal_stack.pop()
        else:
            self._variables_stack.pop()
            if self._variables_stack[-1] == None:   #Remove any scoping barriers...
                self._variables_stack.pop()
    def extract_commands(self):
        ret_val = self._commands
        self._commands = []
        return ret_val
    def add_var_in_cur_scope(self, var_name, var_type, var_value = None):
        if self._in_cal_blk:
            self._variables_cal_stack[-1][var_name] = [var_type, var_value]
        else:
            self._variables_stack[-1][var_name] = [var_type, var_value]
    def set_var_in_cur_scope(self, var_name, var_value):
        #Check the scoping variable stack...
        if self._in_cal_blk:
            cur_vars = self._variables_cal_stack
        else:
            cur_vars = self._variables_stack
        for m in range(len(cur_vars)-1,-1,-1):
            if cur_vars[m] == None:    #Stop if there is a scoping barrier
                if not search_global_scope:
                    break
                else:
                    continue
            if var_name in cur_vars[m]:
                cur_vars[m][var_name][1] = var_value   #TODO: Consider type-checking on index 0 somehow here or elsewhere?
    def get_var_in_cur_scope(self, var_name, search_global_scope=False):
        #Check the scoping variable stack...
        if self._in_cal_blk:
            cur_vars = self._variables_cal_stack
        else:
            cur_vars = self._variables_stack
        for m in range(len(cur_vars)-1,-1,-1):
            if cur_vars[m] == None:    #Stop if there is a scoping barrier
                if not search_global_scope:
                    break
                else:
                    continue
            if var_name in cur_vars[m]:
                return cur_vars[m][var_name][1]   #TODO: Consider type-checking on index 0 somehow here or elsewhere?
        assert False, f"The identifier {var_name} is undefined in this scope!"

    def visit_QuantumGateDefinition(self, node):
        self._gate_defs[node.name.name] = node

    def visit_QubitDeclaration(self, node):
        if node.size == None:
            reg_size = 1
        else:
            reg_size = node.size.value
        self._qubits[node.qubit.name] = reg_size

    def visit_ClassicalAssignment(self, node):
        #TODO: Check op and properly implement this... Also, check the set_var_in_cur_scope command. It doesn't traverse the stack?
        cur_val = self.get_var_in_cur_scope(node.lvalue.name)
        new_val = self._eval_arg(node.rvalue)
        match node.op:
            case '=':
                self.set_var_in_cur_scope(node.lvalue.name, new_val)
            case '+=':
                self.set_var_in_cur_scope(node.lvalue.name, self._eval_binary_expression(cur_val, new_val, '+'))
            case '-=':
                self.set_var_in_cur_scope(node.lvalue.name,  self._eval_binary_expression(cur_val, new_val, '-'))
            case '*=':
                self.set_var_in_cur_scope(node.lvalue.name,  self._eval_binary_expression(cur_val, new_val, '*'))
            case '/=':
                self.set_var_in_cur_scope(node.lvalue.name,  self._eval_binary_expression(cur_val, new_val, '/'))
            case '%=':
                self.set_var_in_cur_scope(node.lvalue.name,  self._eval_binary_expression(cur_val, new_val, '%'))
            case '**=':
                self.set_var_in_cur_scope(node.lvalue.name,  self._eval_binary_expression(cur_val, new_val, '**'))


    def visit_ClassicalDeclaration(self, node):
        if isinstance(node.type, openqasm3.ast.BitType):
            if node.type.size == None:
                reg_size = 1
            else:
                reg_size = node.type.size.value
            self._bits[node.identifier.name] = reg_size
        elif isinstance(node.type, (openqasm3.ast.FloatType, openqasm3.ast.AngleType)):
            print("Warning: Treating angle variable as a float.")
            assert not (node.identifier.name in self._variables_stack[-1]), f"Variable {node.identifier.name} already defined in this scope."
            val = self._eval_arg(node.init_expression) if node.init_expression != None else 0.0
            self.add_var_in_cur_scope(node.identifier.name, node.type, float(val))    #TODO: Look into not ignoring the bit-size and use numpy for that?
        elif isinstance(node.type, (openqasm3.ast.IntType, openqasm3.ast.UintType)):
            print("Warning: Treating angle variable as a float.")
            assert not (node.identifier.name in self._variables_stack[-1]), f"Variable {node.identifier.name} already defined in this scope."
            val = self._eval_arg(node.init_expression) if node.init_expression != None else 0.0
            self.add_var_in_cur_scope(node.identifier.name, node.type, float(val))    #TODO: Look into not ignoring the bit-size and use numpy for that?
        elif isinstance(node.type, (openqasm3.ast.ComplexType)):
            print("Warning: Treating angle variable as a float.")
            assert not (node.identifier.name in self._variables_stack[-1]), f"Variable {node.identifier.name} already defined in this scope."
            val = self._eval_arg(node.init_expression) if node.init_expression != None else 0.0+0.0j
            self.add_var_in_cur_scope(node.identifier.name, node.type, val)    #TODO: Look into not ignoring the bit-size and use numpy for that?
        elif isinstance(node.type, openpulse.ast.WaveformType):
            assert not (node.identifier.name in self._variables_cal_stack[-1]), f"Variable {node.identifier.name} already defined in this pulse-calibration scope."
            val = self._eval_arg(node.init_expression) if node.init_expression != None else []
            self._variables_cal_stack[-1][node.identifier.name] = ['waveform_literal',val]


    
    def visit_QuantumGate(self, node):
        #TODO: Support broadcast invocations here by just calling visit_QuantumGate n times for each qubit in the qreg...
        args = [self._eval_arg(x) for x in node.arguments]
        qargs = [self._eval_qarg(x) for x in node.qubits]   #Already mapped to physical qubit indices...
        #Check if it is satisfied by a defcal
        candidate_defcal = (node.name.name, tuple(qargs))
        is_cal = False
        if candidate_defcal in self._defcals:
            leFunc = self._defcals[candidate_defcal]
            num_extra_modifiers = 0
            is_cal = True
            self._cur_defcal = []
        #Otherwise, proceed with a gatedef or U
        elif node.name.name == 'U':
            assert len(args) == 3, f"Line {node.span.start_line}: The operator 'U' must have 3 angles."
            ctrl_mods = []
            for cur_modifier in self._extra_mod_stack + node.modifiers: #i.e. the extra_mods (extra modifiers) list prepends any internal ctrl commands etc...
                if cur_modifier.argument == None:
                    num = 1
                else:
                    num = self._eval_arg(cur_modifier.argument)
                if cur_modifier.modifier.name == 'ctrl':
                    ctrl_mods += ['ctrl']*num
                elif cur_modifier.modifier.name == 'negctrl':
                    ctrl_mods += ['negctrl']*num
            self._commands.append( {'type': SQDQasmCommandType.GATE, 'angles':  args, 'controls':ctrl_mods, 'targets': self._extra_mod_qubits+qargs} )
            return
        else:
            #or cur_func_name in self._def?
            assert self._gate_defs, f"Line {node.span.start_line}: Function '{node.name.name}' is undefined"
            leFunc = self._gate_defs[node.name.name]
            num_extra_modifiers = len(node.modifiers)
            self._extra_mod_stack = self._extra_mod_stack + node.modifiers
            self._extra_mod_qubits = self._extra_mod_qubits + qargs[:num_extra_modifiers]
            qargs = qargs[num_extra_modifiers:]
        assert len(qargs) == len(leFunc.qubits), f"Line {node.span.start_line}: The gate {node.name.name} requires {len(qargs)} qubits, not {len(leFunc.qubits)} (ignoring ctrl/negctrl etc.)."
        #
        #Now Evaluate...
        self._in_cal_blk = is_cal
        self.enter_scope(with_scope_barrier=True)
        #Add function arguments into new scope
        for m,cur_func_arg in enumerate(leFunc.arguments):
            if isinstance(cur_func_arg, openqasm3.ast.Identifier):
                self.add_var_in_cur_scope(cur_func_arg.name, None, args[m])
            elif isinstance(cur_func_arg, openqasm3.ast.ClassicalArgument):
                self.add_var_in_cur_scope(cur_func_arg.name.name, cur_func_arg.type, args[m])   #TODO: Consider adding type-checking here?
        #Qubits in gate-definitions/defcals cannot be multi-qubit registers, so just default to index-0
        self._qarg_stack.append({(x.name,0):qargs[m] for m,x in enumerate(leFunc.qubits)})
        #Visit every function/statement in the function body
        for cur_stmt in leFunc.body:
            self._in_cal_blk = is_cal   #In case the visitation went to another defcal gate and it set it to false...
            self.visit(cur_stmt)
        self.leave_scope()
        self._qarg_stack.pop()
        for m in range(num_extra_modifiers):
            self._extra_mod_stack.pop()
            self._extra_mod_qubits.pop()
        if is_cal:
            self._commands.append({'type':SQDQasmCommandType.DEF_CAL, 'targets':qargs, 'play_commands':self._cur_defcal})  #Synchronisation barrier to ensure everything outside is run sequentially
        self._in_cal_blk = False
        # self._commands += self._eval_func(node, args, qargs)

    
    def visit_ExpressionStatement(self, node):
        self.visit(node.expression)

    def visit_FunctionCall(self, node):
        return self._eval_arg(node)

    def visit_QuantumReset(self, node):
        qargs = self._eval_qarg(node.qubits)    #TODO: Look into whole-register reset...
        self._commands.append({'type':SQDQasmCommandType.RESET, 'targets':qargs})

    def visit_QuantumBarrier(self, node):
        # self._commands.append({'type':'barrier'})
        #Pointless as we won't be doing commutation/collapse optimisation here...
        pass

    def visit_DelayInstruction(self, node):
        cur_delay = self._eval_arg(node.duration)
        if not isinstance(cur_delay, tuple):    #Typically must have unit, but 0 delay doesn't require units...abs
            cur_delay = (cur_delay, 's')
        qargs = []
        for cur_qubits in node.qubits:
            qargs += self._eval_qarg(cur_qubits, allow_entire_regs=True)
        self._commands.append({'type':SQDQasmCommandType.DELAY, 'targets':qargs, 'length':cur_delay})

    def visit_QuantumMeasurementStatement(self, node):
        qargs = [self._eval_qarg(node.measure.qubit)]   #TODO: Expand to support registers expanding...
        self._commands.append( {'type': SQDQasmCommandType.MEASURE, 'qubit': qargs, 'store': self._eval_bits_arg(node.target)} )

    def visit_RangeDefinition(self, node):
        leStep = 1 if node.step==None else self._eval_arg(node.step)
        #Note that ranges in openqasm3 are inclusive of the end-point...
        leLoopRange = np.arange(self._eval_arg(node.start), self._eval_arg(node.end)+leStep/2, leStep)
        self._last_loop_range = leLoopRange      

    def _eval_qarg(self, qarg, allow_entire_regs=False):
        #It returns a list as a register passed without indices implies automatic slicing over all the individual qubits within the register...
        #NOTE: Quantum types cannot be an array, so the only Indexed Identifier will be [[n]] for the register index n...
        if isinstance(qarg, openqasm3.ast.Identifier):
            #Qubits cannot be sent as the entire register to quantum gates etc. Thus, it's fine to just presume index-0 here...
            #Unless it's a multi-qubit delay...
            if allow_entire_regs:
                ret_qubits = []
                for cur_qubit in self._qarg_stack[-1]:
                    if cur_qubit[0] == qarg.name:
                        ret_qubits.append(self._qarg_stack[-1][cur_qubit])
                assert len(ret_qubits) > 0, f"The qubit register '{qarg.name}' is undefined."
                return ret_qubits
            else:
                cur_qubit = (qarg.name,0)
            assert cur_qubit in self._qarg_stack[-1], f"The qubit register '{qarg.name}' is undefined."
            return self._qarg_stack[-1][cur_qubit]
        elif isinstance(qarg, openqasm3.ast.IndexedIdentifier):
            assert qarg.name.name in self._qubits, f"The qubit register '{qarg.name.name}' is undefined."
            cur_qubit = (qarg.name.name, self._eval_arg(qarg.indices[0][0]))    #Indexed qubits should only appear in the global scope anyway...
            if allow_entire_regs:
                return [self._qarg_stack[-1][cur_qubit]]
            else:
                return self._qarg_stack[-1][cur_qubit]

    def _eval_bits_arg(self, bit_arg):
        #NOTE: Quantum types cannot be an array, so the only Indexed Identifier will be [[n]] for the register index n...
        if isinstance(bit_arg, openqasm3.ast.Identifier):
            assert bit_arg.name in self._bits, f"The register '{bit_arg.name}' is undefined."
            return [(bit_arg.name, x) for x in range(self._bits[bit_arg.name])]   #THIS MEANS IT IS FULL REG SIZE AND MUST BE MAPPED AS THUS!
        elif isinstance(bit_arg, openqasm3.ast.IndexedIdentifier):
            assert bit_arg.name.name in self._bits, f"The register '{bit_arg.name.name}' is undefined."
            return [(bit_arg.name.name, self._eval_arg(bit_arg.indices[0][0]))]

    def _eval_arg(self, argument, search_global_scope=False):
        if isinstance(argument, (int, float)):    #More just here for safety...
            return argument
        elif isinstance(argument, (openqasm3.ast.IntegerLiteral, openqasm3.ast.FloatLiteral)):
            return argument.value
        elif isinstance(argument, (openqasm3.ast.ImaginaryLiteral)):
            return argument.value * 1j
        elif isinstance(argument, openqasm3.ast.Identifier):
            if argument.name == 'π' or argument.name == 'pi':
                return np.pi
            else:
                return self.get_var_in_cur_scope(argument.name, search_global_scope)
        elif isinstance(argument, openqasm3.ast.DurationLiteral):
            return (argument.value, argument.unit.name)
        elif isinstance(argument, openqasm3.ast.UnaryExpression):
            if argument.op.name == '-':
                return -self._eval_arg(argument.expression)
            assert False, f"Unsupported unary operation {argument.op.name}."
        elif isinstance(argument, openqasm3.ast.BinaryExpression):
            lhs = self._eval_arg(argument.lhs)
            rhs = self._eval_arg(argument.rhs)
            return self._eval_binary_expression(lhs, rhs, argument.op.name)
        elif isinstance(argument, openqasm3.ast.FunctionCall):
            match argument.name.name:
                case 'load_numpy_encoded':
                    assert len(argument.arguments) == 1 and isinstance(argument.arguments[0], openqasm3.ast.IntegerLiteral), "The function load_numpy_encoded must have only one hashed encoded hex value."
                    return self._temp_numpy_arrays[argument.arguments[0].value]
                #
                case 'drive':
                    assert len(argument.arguments) == 1 and argument.arguments[0].name[0]=='$', "Must give a single physical qubit (i.e. starts with $) to extract the line for the 'drive' function."
                    cur_qubit = (argument.arguments[0].name,0)
                    assert cur_qubit in self._qarg_stack[-1], f"The physical qubit {argument.arguments[0].name} is not defined here in the defcal function signature?"
                    return ('drive', self._qarg_stack[-1][cur_qubit])
                case 'flux':
                    assert len(argument.arguments) == 1 and argument.arguments[0].name[0]=='$', "Must give a single physical qubit (i.e. starts with $) to extract the line for the 'drive' function."
                    cur_qubit = (argument.arguments[0].name,0)
                    assert cur_qubit in self._qarg_stack[-1], f"The physical qubit {argument.arguments[0].name} is not defined here in the defcal function signature?"
                    return ('flux', self._qarg_stack[-1][cur_qubit])
                case 'gaussian':
                    assert len(argument.arguments) >= 2, "Must provide at least, the duration and amplitude for 'gaussian'."
                    ret_dict = {'type': 'gaussian'}
                    ret_dict['length'] = self._eval_arg(argument.arguments[0])
                    ret_dict['amplitude'] = self._eval_arg(argument.arguments[1])
                    if len(argument.arguments) > 2:
                        ret_dict['sigma'] = argument.arguments[2]
                    return ret_dict
                case 'set_phase':
                    assert len(argument.arguments) == 2, "Must give 2 arguments: the frame (i.e. drive/flux/measure etc.) of the signal line and the phase in radians."
                    frame_var = self._eval_arg(argument.arguments[0])
                    angle_var = self._eval_arg(argument.arguments[1])
                    self._cur_defcal.append( {'type': 'pulse_attribute', 'frame_var':  frame_var, 'set_phase_val':angle_var} )
                case 'shift_phase':
                    assert len(argument.arguments) == 2, "Must give 2 arguments: the frame (i.e. drive/flux/measure etc.) of the signal line and the phase in radians."
                    frame_var = self._eval_arg(argument.arguments[0])
                    angle_var = self._eval_arg(argument.arguments[1])
                    self._cur_defcal.append( {'type': 'pulse_attribute', 'frame_var':  frame_var, 'shift_phase_val':angle_var} )
                case 'play':
                    # assert self._in_defcal_blk, "The play function is reserved for defcal blocks only."
                    assert len(argument.arguments) == 2, "Must give 2 arguments: the frame (i.e. drive/flux/measure etc.) of the signal line and the waveform."
                    frame_var = self._eval_arg(argument.arguments[0])
                    waveform_var = self._eval_arg(argument.arguments[1], search_global_scope=True)
                    if isinstance(waveform_var, np.ndarray):
                        waveform_var = {'type': 'sampled', 'samples': waveform_var}
                    self._cur_defcal.append( {'type': 'play', 'frame_var':  frame_var, 'waveform_var':waveform_var} )
                    pass
                case _:
                    #TODO: For non-extern functions that have an internal def, run a visit pattern and use visit_ReturnStatement to capture its output...
                    pass
        else:
            assert False, f"Type {argument} not implemented!"

    def _eval_binary_expression(self, lhs, rhs, operator):
        units = [None, None]
        if isinstance(lhs, (list,tuple)):
            val_lhs = lhs[0]
            units[0] = lhs[1]
        else:
            val_lhs = lhs
        if isinstance(rhs, (list,tuple)):
            val_rhs = rhs[0]
            units[1] = rhs[1]
        else:
            val_rhs = rhs
        #
        if operator == '+':
            assert (units[0] == None or units[1] == None) or (units[0] == units[1]), "Inconsistent units in addition."
            ret_val = val_lhs + val_rhs
        elif operator == '-':
            assert (units[0] == None or units[1] == None) or (units[0] == units[1]), "Inconsistent units in subtraction."
            ret_val = val_lhs - val_rhs
        elif operator == '*':
            assert (units[0] == None or units[1] == None), "Cannot multiply two numbers with different (dimensioned) units."
            ret_val = val_lhs * val_rhs
        elif operator == '/':
            assert (units[0] == None or units[1] == None), "Cannot divide two numbers with different (dimensioned) units."
            ret_val = val_lhs / val_rhs
        elif operator == '**':
            assert (units[0] == None and units[1] == None), "Cannot take powers with variables containing units."
            ret_val = val_lhs ** val_rhs
        elif operator == '%':
            assert (units[0] == None and units[1] == None), "Cannot take modulo with variables containing units."
            ret_val = val_lhs % val_rhs
        #
        if units[0] == None and units[1] == None:
            return ret_val
        else:
            return (ret_val,units[0] if units[0] != None else units[1])

    def _preprocess_encoded_numpy_arrays(self, cal_string:str):
        """
        Basically decodes the numpy arrays within the load_numpy_encoded functions...
        This is because the parser will convert it into integers with any leading zeros
        removed... This should technically work in scoped blocks as well - even in for
        loops as the bytes form a static immutable hex-string...
        """
        func_name = "load_numpy_encoded("
        arrays = {}
        out = []
        pos = 0
        next_id = 0
        while True:
            start = cal_string.find(func_name, pos)
            if start == -1:
                out.append(cal_string[pos:])
                break
            # Copy everything before the func_name.
            out.append(cal_string[pos:start])
            # Find matching ')'.
            m = start + len(func_name)
            depth = 1
            while m < len(cal_string) and depth:
                c = cal_string[m]
                assert c != ',', "The function load_numpy_encoded only takes one argument being the encoded hex value..."
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                m += 1
            if depth:
                raise SyntaxError("Unmatched '(' in load_numpy_encoded")
            # Contents inside the parentheses.
            payload = cal_string[start + len(func_name):m - 1].strip()
            # Decode however you currently do it.
            assert payload[:2] == '0x', "The function load_numpy_encoded must have a hexadecimal argument (i.e. 0x9874AF...)"
            arrays[next_id] = SerialiseJSON.decode_ndarray(payload[2:], use_hex=True)
            # Replace with integer literal.
            out.append(f"load_numpy_encoded({next_id})")
            next_id += 1
            pos = m
        return "".join(out), arrays

    def visit_CalibrationDefinition(self, node):
        leQubits = [x.name for x in node.qubits]
        phys_qubit_indices = []
        for cur_qubit in leQubits:
            assert cur_qubit.startswith('$'), "Must only supply physical qubits (i.e. starting with $) in defcal blocks."
            phys_qubit_indices.append(int(cur_qubit[1:]))
        new_source, self._temp_numpy_arrays = self._preprocess_encoded_numpy_arrays(node.body)
        #Overwrite the string body with the parsed statement list
        defcal_ast = openpulse.parse(new_source)
        node.body = defcal_ast.statements
        #
        self._defcals[(node.name.name, tuple(phys_qubit_indices))] = node        
        return
        #This should just be stored/colleced like gatedefs. Then called when it's called for a gate? Then requires evaluation and inference of length and signals...
        #When it processes a gate that's a defcal, it converts every play into a separate pulse. In the execution of the schedule, pulses are created in-situ
        #and not duplicated if there is an identical one (i.e. reuses the previously defined instance) and played within the section...
        #
        #Make default behavior to just append the pulses as one would normal gates. User must throw a delay[0] to sync the qubits before calling custom cz functions?
        #Or have a scheduler flag that implicitly adds a qubit sync (i.e. delay[0]) before all multi-qubit instructions to MATCH what it does already?


    def visit_CalibrationStatement(self, node):
        new_source, self._temp_numpy_arrays = self._preprocess_encoded_numpy_arrays(node.body)
        cal_ast = openpulse.parse(f"cal{{{new_source}}}")
        assert not self._in_cal_blk, "Cannot declare a cal statement while already in a defcal/cal block..."
        self._in_cal_blk = True
        for cur_stmt in cal_ast.statements[0].body:
            self.visit(cur_stmt)
        self._in_cal_blk = False
        pass


class IdentifierCollector(openqasm3.visitor.QASMVisitor):
    def visit_Identifier(self, node, context=None):
        self.names.add(node.name)
        return node
    def get_identifiers(self, block:list):
        self.names = set()
        for cur_stmt in block:
            self.visit(cur_stmt)
        return sorted(self.names)

class IncludeCollector(openqasm3.visitor.QASMVisitor):
    def __init__(self):
        self.includes = []
    def visit_Include(self, node):
        self.includes.append(node.filename)

class QubitCollector(openqasm3.visitor.QASMVisitor):
    def __init__(self):
        self.qubits = {}
    def visit_QubitDeclaration(self, node):
        self.qubits[node.qubit.name] = 1 if node.size == None else node.size.value

class BitCollector(openqasm3.visitor.QASMVisitor):
    def __init__(self):
        self.bits = {}
    def visit_ClassicalDeclaration(self, node):
        if isinstance(node.type, openqasm3.ast.BitType):
            if node.type.size == None:
                reg_size = 1
            else:
                reg_size = node.type.size.value
            self.bits[node.identifier.name] = reg_size


class ParserOpenQASM:
    def __init__(self, main_file: str, source_dirs: list[str], **kwargs):
        if 'main_qasm' in kwargs:
            assert main_file == '', "Do not give a file path if supplying the main QASM a direct string in the argument 'main_qasm'"
            main_file = ('str', kwargs.pop('main_qasm'))

        else:
            main_file = ('file', main_file)
        self._main_file = (main_file[0], main_file[1])

        source_dirs = source_dirs + [str(Path(__file__).parent) + "/includes/"]
        self._overall_includes = []
        self._get_include_tree([main_file], self._overall_includes, source_dirs)
        #
        self._scope_stack = [{}]
        #
        #Collect just the qubit declarations (don't need to go through loops or scoping brackets as they should only exist in the global scope anyway)
        #Note that this is only here for the purpose of the get_qubit_registers function...
        collectorQ = QubitCollector()
        collectorC = BitCollector()
        for m, cur_file in enumerate(self._overall_includes):
            if cur_file[0] == 'file':
                ast = openqasm3.parser.parse(self._open_file_strip_comments(cur_file[1]))
            else:
                ast = openqasm3.parser.parse(cur_file[1])
            collectorQ.visit(ast)
            collectorC.visit(ast)
        self._qregs = collectorQ.qubits
        self._cregs = collectorC.bits
        #
        if 'mapping' in kwargs:
            self._qreg_phys_mapping = kwargs.pop('mapping')
        else:
            self._qreg_phys_mapping = {}
            for cur_qreg in self._qregs:
                for m in range(self._qregs[cur_qreg]):
                    self._qreg_phys_mapping[(cur_qreg,m)] = len(self._qreg_phys_mapping)
        #
        self._measure_label = kwargs.get('measure_label', "∅")

    def save_main_script(self, file_path):
        if self._main_file[0] == 'file':
            shutil.copy2(self._main_file[1], file_path)
        else:
            with open(file_path, 'w', encoding="utf-8") as file:
                file.write(self._main_file[1])

    def get_qregs(self):
        leQregs = []
        for cur_qreg in self._qregs:
            for m in range(self._qregs[cur_qreg]):
                leQregs += [(cur_qreg,m)]
        return leQregs

    def set_qreg_physical_mapping(self, mapping):
        """
        Given as key-value pairs where key is a key from get_qubit_regs and value is the index of the physical qubit
        """
        self._qreg_phys_mapping = mapping

    def perform_parsing(self):
        self._visitor = SQDQasmVisitor(self._qreg_phys_mapping)
        self._command_blocks = []
        for m, cur_file in enumerate(self._overall_includes):
            if cur_file[0] == 'file':
                ast = openqasm3.parser.parse(self._open_file_strip_comments(cur_file[1]))
            else:
                ast = openqasm3.parser.parse(cur_file[1])
            self._process_block(ast.statements)
        pass

    def _find_file(self, file_path, source_dirs):
        if not os.path.exists(file_path):
            found = False
            for cur_source_dir in source_dirs:
                cur_path = os.path.join(cur_source_dir, file_path)
                if os.path.exists(cur_path):
                    file_path = cur_path
                    found = True
                    break
            assert found, f"Could not find file {file_path}"
        return file_path

    def _get_include_tree(self, cur_includes_stack: list[str], overall_includes: list[str], source_dirs: list[str]):
        current_file = cur_includes_stack[-1]
        #
        collectorI = IncludeCollector()
        if current_file[0] == 'file':
            ast = openqasm3.parser.parse(self._open_file_strip_comments(current_file[1]))
        else:
            ast = openqasm3.parser.parse(current_file[1])
        collectorI.visit(ast)
        cur_includes = [('file',self._find_file(x, source_dirs)) for x in collectorI.includes]
        #
        for cur_include in cur_includes:
            assert not cur_include in cur_includes_stack, f"There is a circular dependency with {cur_include}."
            self._get_include_tree(cur_includes_stack + [cur_include], overall_includes, source_dirs)
        if current_file[0] == 'file':
            overall_includes.append(('file', self._find_file(current_file[1], source_dirs)))
        else:
            overall_includes.append(('str', current_file[1]))
        return

    def _open_file_strip_comments(self, file_path):
        with open(file_path, encoding="utf-8") as file: #If it is not UTF-8, it'll read the pi symbol as the Euro symbol etc...
            lines = [line.rstrip() for line in file]
        # lines = "\n".join(lines)
        # lines = re.sub('//.*?\n','\n', lines, get_qubit_registersflags=re.DOTALL)
        #
        # lines = lines.split('\n')
        # lines = [x.strip() for x in lines if x != '']
        return '\n'.join(lines)
    
    def _process_block(self, statements:list):
        #Separate the block into bits that must be run strictly sequentially - e.g. for-loops etc...
        all_sub_blocks = []
        cur_sub_block = []
        for cur_statement in statements:
            if isinstance(cur_statement, openqasm3.ast.ForInLoop):
                all_sub_blocks.append(cur_sub_block)
                cur_sub_block = []
                all_sub_blocks.append(cur_statement)
            else:
                cur_sub_block.append(cur_statement)
        if len(cur_sub_block) > 0:
            all_sub_blocks.append(cur_sub_block)
        #Now process the blocks
        for cur_sub_block in all_sub_blocks:
            if isinstance(cur_sub_block, list):
                for cur_stmt in cur_sub_block:
                    self._visitor.visit(cur_stmt)
                cur_cmds = self._visitor.extract_commands()
                if len(cur_cmds) > 0:
                    self._command_blocks.append(cur_cmds)
            elif isinstance(cur_sub_block, openqasm3.ast.ForInLoop):
                used_ids = IdentifierCollector().get_identifiers(cur_sub_block.block)
                #Unroll loop if the looping variable exists within the loop
                #TODO: Make this stricter; i.e. unroll iff it is changing the time across more than one qubit...
                if True: #cur_sub_block.identifier.name in used_ids:
                    #Process For Loop Range...
                    self._visitor.visit(cur_sub_block.set_declaration)
                    leLoopRange = self._visitor._last_loop_range*1
                    #
                    self._visitor.enter_scope()
                    loop_var = cur_sub_block.identifier.name
                    self._visitor.add_var_in_cur_scope(loop_var,cur_sub_block.type)
                    for cur_val in leLoopRange:
                        self._visitor.set_var_in_cur_scope(loop_var, cur_val)
                        #All variables defined in the loop exist only in this iteration...
                        self._visitor.enter_scope()
                        self._process_block(cur_sub_block.block)
                        self._visitor.leave_scope()    
                    self._visitor.leave_scope()
                # else:
                #     pass

        pass
            




    def get_qubit_registers(self):
        ret_list = []
        for cur_qreg in self._qregs:
            for m in range(self._qregs[cur_qreg]):
                ret_list.append((cur_qreg,m))
        return ret_list

    def create_schedule(self, params:ScheduleParametersBase, flatten_blocks=False):
        #Initialise qubits and sync times
        phys_qubit_ids = list(self._qreg_phys_mapping.values())
        #
        meas_store_ids = {}
        meas_index = 0
        final_blocks = []
        for cur_block in self._command_blocks:
            final_commands = []
            cur_qubit_commands = {x:[] for x in phys_qubit_ids}
            qubit_sync_times = {x:0 for x in phys_qubit_ids}
            last_sync_command_indices = {x:-1 for x in phys_qubit_ids}
            #
            for cur_command in cur_block + [{'type':SQDQasmCommandType.END_BLOCK, 'targets':phys_qubit_ids}]:
                sync_command = False
                if cur_command['type'] == SQDQasmCommandType.GATE and len(cur_command['controls']) > 0:
                    sync_command = True
                elif cur_command['type'] == SQDQasmCommandType.DELAY and len(cur_command['targets']) > 1:
                    sync_command = True
                elif cur_command['type'] == SQDQasmCommandType.END_BLOCK:
                    sync_command = True
                elif cur_command['type'] == SQDQasmCommandType.DEF_CAL:
                    sync_command = True

                if not sync_command:
                    if cur_command['type'] == SQDQasmCommandType.GATE:
                        cur_qubit_commands[cur_command['targets'][0]].append(self._process_1Q_gate(cur_command['angles']))
                    elif cur_command['type'] == SQDQasmCommandType.DELAY:
                        cur_qubit_commands[cur_command['targets'][0]].append(('D', self._process_delay(cur_command['length'], params.dt())))  #Using Drive/Measure lines as the baseline dt...
                    elif cur_command['type'] == SQDQasmCommandType.MEASURE:
                        cur_meas_id = f'm{meas_index}'
                        cur_qubit_commands[cur_command['qubit'][0]].append(('Measure',cur_meas_id))   #TODO: Check if multi-qubit registers can be stored/measured in OpenQASM3?
                        meas_store_ids[cur_command['store'][0]] = cur_meas_id
                        meas_index += 1
                    elif cur_command['type'] == SQDQasmCommandType.RESET:
                        #Reset does not synchronise
                        cur_qubit_commands[cur_command['targets']].append(('Reset',)) #TODO: Adapt to multi-qubit registers
                else:
                    ####
                    #Calculate new synchronisation point
                    #
                    cur_targ_phys_indices = cur_command['targets']
                    cur_seq_lens = {x:0 for x in cur_targ_phys_indices}
                    for cur_phys_qubit_index in cur_targ_phys_indices:
                        cur_len = 0
                        for cur_op in cur_qubit_commands[cur_phys_qubit_index]:
                            if cur_op[0] == 'D':    #It is a delay...
                                cur_len += cur_op[1]
                            elif cur_op[0] == 'Measure':
                                cur_len += params.get_duration_measurement(cur_phys_qubit_index)
                            elif cur_op[0] == 'pulse':
                                cur_len += cur_op[1]['length']
                            else:   #It is just X, Y, Z for the gate type...
                                cur_len += params.get_duration(cur_phys_qubit_index, cur_op)
                        cur_seq_lens[cur_phys_qubit_index] = cur_len
                    new_sync_point = np.max([qubit_sync_times[x]+cur_seq_lens[x] for x in cur_targ_phys_indices])
                    ####
                    #Pad/sequence Delays on qubits and add qubit sequences to final command list
                    #
                    for cur_phys_qubit_index in cur_targ_phys_indices:
                        #Process residual/stretch delays
                        residual = new_sync_point - (qubit_sync_times[cur_phys_qubit_index] + cur_seq_lens[cur_phys_qubit_index])
                        cur_seg_len = new_sync_point - qubit_sync_times[cur_phys_qubit_index]
                        #TODO: Check for stretches and synthesise delays here!
                        if residual > 0:    #Discard if 0.0...
                            cur_qubit_commands[cur_phys_qubit_index].append(('D',residual))
                        #
                        #Add sequence to command list and update current synchronised time for the qubit
                        if cur_seg_len == 0:
                            continue
                        play_after = None if last_sync_command_indices[cur_phys_qubit_index] == -1 else last_sync_command_indices[cur_phys_qubit_index]
                        final_commands.append({'qubit_index': cur_phys_qubit_index, 'custom_waveform':False, 'sequence': cur_qubit_commands[cur_phys_qubit_index], 'after':play_after, 'length':cur_seg_len})
                        cur_qubit_commands[cur_phys_qubit_index] = []
                        qubit_sync_times[cur_phys_qubit_index] = new_sync_point
                    ####
                    #Add the actual command for the qubits and update the last synchronised command-sequence index
                    if cur_command['type'] == SQDQasmCommandType.GATE:
                        cur_target_gate = self._process_1Q_gate(cur_command['angles'])
                        cur_play_after_index = None if len(final_commands) == 0 else len(final_commands)-1
                        gate_duration = params.get_duration2QG(cur_command['targets'][0], cur_command['targets'][1], cur_command['controls'] + [cur_target_gate])
                        final_commands.append({'qubit_index': cur_targ_phys_indices, 'custom_waveform':False, 'sequence': cur_command['controls'] + [cur_target_gate], 'after':cur_play_after_index, 'length':gate_duration})
                        #Set all gate-sequences on these qubits to be synchronised to come after this new multi-qubit gate...
                        for cur_phys_qubit_index in cur_targ_phys_indices:
                            qubit_sync_times[cur_phys_qubit_index] += gate_duration   #TODO: Must add 2QG time and pass this in - perhaps by a graph?
                            last_sync_command_indices[cur_phys_qubit_index] = len(final_commands)-1
                    elif cur_command['type'] == SQDQasmCommandType.DELAY:
                        for cur_phys_qubit_index in cur_targ_phys_indices:
                            cur_delay_cmd = ('D', self._process_delay(cur_command['length'], params.dt()))  #Using Drive/Measure lines as the baseline dt...
                            if cur_delay_cmd[1] > 0: #Don't add the command if the delay is 0...
                                cur_play_after_index = None if last_sync_command_indices[cur_phys_qubit_index] == -1 else last_sync_command_indices[cur_phys_qubit_index]
                                final_commands.append({'qubit_index': cur_phys_qubit_index, 'custom_waveform':False, 'sequence': [cur_delay_cmd], 'after':cur_play_after_index, 'length':cur_delay_cmd[1]})
                                qubit_sync_times[cur_phys_qubit_index] += cur_delay_cmd[1]
                                last_sync_command_indices[cur_phys_qubit_index] = len(final_commands)-1
                    elif cur_command['type'] == SQDQasmCommandType.DEF_CAL:
                        cur_pulse_seq = self._process_defcal_command(cur_command, params)
                        cur_play_after_index = None if len(final_commands) == 0 else len(final_commands)-1
                        gate_duration = cur_pulse_seq['length']
                        final_commands.append({'qubit_index': cur_targ_phys_indices, 'custom_waveform':True, 'sequence': cur_pulse_seq['play_commands'], 'after':cur_play_after_index, 'length':gate_duration})
                        #Set all gate-sequences on these qubits to be synchronised to come after this new multi-qubit gate...
                        for cur_phys_qubit_index in cur_targ_phys_indices:
                            qubit_sync_times[cur_phys_qubit_index] += gate_duration   #TODO: Must add 2QG time and pass this in - perhaps by a graph?
                            last_sync_command_indices[cur_phys_qubit_index] = len(final_commands)-1
                    #Don't need to check if it's SQDQasmCommandType.END_BLOCK as it's the end...
            final_blocks.append(final_commands)
        #
        ret_dict = {'commands':final_blocks, 'meas_store_ids': meas_store_ids}
        if flatten_blocks:
            ret_dict = {'commands':[item for sublist in ret_dict['commands'] for item in sublist], 'meas_store_ids':ret_dict['meas_store_ids']}
        return ret_dict

    def _process_delay(self, delay_params, dt_time):
        if delay_params[1] == 's':
            return delay_params[0]
        elif delay_params[1] == 'ms':
            return delay_params[0] * 1e-3
        elif delay_params[1] == 'µs' or delay_params[1] == 'us':
            return delay_params[0] * 1e-6
        elif delay_params[1] == 'ns':
            return delay_params[0] * 1e-9
        elif delay_params[1] == 'dt':
            return delay_params[0] * dt_time
        else:
            assert False, f"Cannot interpret delay parameters {delay_params}."


    def _process_1Q_gate(self, unitary_angles):
        axis, angle = self.get_axis_angle_from_unitary(unitary_angles)
        self._normalise_name(axis, angle)
        if axis[0] > 1-1e-6:
            return ('X', angle)
        elif axis[0] < -1+1e-6:
            return ('X', -angle)
        elif axis[1]>1-1e-6:
            return ('Y', angle)
        elif axis[1] < -1+1e-6:
            return ('Y', -angle)
        elif axis[2]>1-1e-6:
            return ('Z', angle)
        elif axis[2] < -1+1e-6:
            return ('Z', angle)
        else:
            assert False, f"A gate is required on axis {axis}. Convert it into equivalent rotations about the basis axes X/Y/Z."

    def _process_defcal_command(self, dict_command:dict, params:ScheduleParametersBase):
        pulse_lengths = {}
        for cur_target in dict_command['targets']:
            pulse_lengths[('drive', cur_target)] = 0
            pulse_lengths[('flux', cur_target)] = 0
            pulse_lengths[('measure', cur_target)] = 0
        #Process the lengths based on the waveforms...
        for cur_cmd in dict_command['play_commands']:
            dt_time = params.dt(cur_cmd['frame_var'][0])
            if cur_cmd['type'] == 'pulse_attribute':
                cur_len = 0
            elif cur_cmd['waveform_var']['type'] in ['gaussian']:
                cur_len = self._process_delay(cur_cmd['waveform_var']['length'],dt_time)
            elif cur_cmd['waveform_var']['type'] == 'sampled':  #Shouldn't be anything else given how everything so far is hard-coded...
                assert len(cur_cmd['waveform_var']['samples'].shape) == 1, "Must be 1D array. There is a custom sampled waveform that is not 1D..."
                cur_len = cur_cmd['waveform_var']['samples'].shape[0]*dt_time
            else:
                assert False, f"Cannot process waveform type {cur_cmd['waveform_var']['type']}" #Shouldn't happen given how everything preceding this is hard-coded...
            if cur_cmd['type'] == 'play':
                cur_cmd['waveform_var']['length'] = cur_len
            #
            pulse_lengths[cur_cmd['frame_var']] += cur_len
        dict_command['length'] = max([pulse_lengths[x] for x in pulse_lengths])
        return dict_command

    def get_axis_angle_from_unitary(self, unitary_angles):
        """
        Convert OpenQASM U(theta, phi, lambda) parameters to
        axis-angle representation.
        Based on their definition here: https://openqasm.com/language/gates.html

        Returns:
            rotation_axis : np.ndarray, shape (3,)
            rotation_angle : float
        """
        theta, phi, lam = unitary_angles
        matU = np.array([[np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
                         [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)]], dtype=complex)
        # Remove global phase so that det(U) = 1.
        detU = np.linalg.det(matU)
        matU *= np.exp(-0.5j * np.angle(detU))  #Note that for a 2x2 matrix, pulling a global factor out squares it...
        #U = a I - i (bx X + by Y + bz Z) with: a  = cos(angle/2) and bi = sin(angle/2) * n_i
        a = 0.5 * np.trace(matU)
        bx = 0.5j * (matU[0, 1] + matU[1, 0])
        by = 0.5  * (matU[1, 0] - matU[0, 1])
        bz = 0.5j * (matU[0, 0] - matU[1, 1])
        b = np.array([bx, by, bz], dtype=complex)
        #Numerical cleanup
        a = np.real_if_close(a).item()
        b = np.real_if_close(b).astype(float)
        #Normalize against tiny numerical errors
        a = float(np.clip(np.real(a), -1.0, 1.0))
        sin_half_angle = np.linalg.norm(b)
        #Identity / zero rotation
        if sin_half_angle < 1e-12:
            return np.array([0.0, 0.0, 1.0]), 0.0
        #Make angle lie in [0, 2*pi]
        rotation_angle = 2.0 * np.arctan2(sin_half_angle, a)
        rotation_axis = b / sin_half_angle
        return rotation_axis, rotation_angle

    def _normalise_name(self, axis, angle):
        if axis[0]>1-1e-6:
            return r"$X_{angle}$"
        elif axis[0] < -1+1e-6:
            return r"$-X_{angle}$"
        elif axis[1]>1-1e-6:
            return r"$Y_{angle}$"
        elif axis[1] < -1+1e-6:
            return r"$-Y_{angle}$"
        elif axis[2]>1-1e-6:
            return r"$Z_{angle}$"
        elif axis[2] < -1+1e-6:
            return r"$-Z_{angle}$"
        else:
            return "U"#f"({axis[0]}, {axis[1]}, {axis[2]}), {angle}"  

    def _get_1QG_name(self, axis:str, angle:float):
        if axis == 'D':
            return f'{Miscellaneous.get_units(angle)}s'
        if np.abs(angle - np.pi) < 1e-6:
            return f'{axis}(π)'
        if np.abs(angle - np.pi/2) < 1e-6:
            return f'{axis}(π/2)'
        if np.abs(angle + np.pi/2) < 1e-6:
            return f'{axis}(-π/2)'
        if np.abs(angle - np.pi/4) < 1e-6:
            return f'{axis}(π/4)'
        if np.abs(angle + np.pi/4) < 1e-6:
            return f'{axis}(-π/4)'
        return f'{axis}({angle})'


    def _plot_gate(self, ax, x,y,text, time_span, col):
        ax.add_artist(mpatch.Rectangle((x,y), time_span, 0.9, facecolor=col))
        ax.annotate(text, (x,y), color='w', weight='bold', 
                    fontsize=6, ha='center', va='center')
    def _plot_ctrl(self, ax, x,y, col):
        ax.add_artist(mpatch.Circle((x,y), 0.2, facecolor=col))

    def tabulate_schedule(self, gate_schedule, qubit_params:ScheduleParametersBase):
        phys_qubit_ids = list(self._qreg_phys_mapping.values())
        cur_qubit_gate_time_indices = {x:0.0 for x in phys_qubit_ids}
        #
        arr_qubits = []
        arr_qubit_auxs = []
        arr_start_times = []
        arr_end_times = []
        arr_gate_types = []
        arr_col_intens = []
        arr_operations = []
        #
        for cur_sec_ind,cur_sec_ops in enumerate(gate_schedule['commands']):
            cur_qubit = cur_sec_ops['qubit_index']
            if cur_sec_ops['custom_waveform']:
                cur_gate_time = cur_sec_ops['length']
                cur_name = f'Wfm ({Miscellaneous.get_units(cur_gate_time)}s)'
                #
                if not isinstance(cur_qubit, (list,tuple)):
                    cur_qubit = [cur_qubit]
                for x in cur_qubit:
                    arr_qubits.append(x)
                    arr_qubit_auxs.append(-1)
                    arr_start_times.append(cur_qubit_gate_time_indices[x])
                    cur_qubit_gate_time_indices[x] += cur_gate_time
                    arr_end_times.append(cur_qubit_gate_time_indices[x])
                    arr_gate_types.append(cur_name)
                    arr_operations.append('W')
                    arr_col_intens.append(cur_sec_ind/len(gate_schedule['commands']))
                continue
            elif isinstance(cur_qubit, (list,tuple)):
                if len(cur_qubit) == 1:
                    cur_qubit = cur_qubit[0]    #A strange case that may never exist?
                else:
                    #Process it as a 2QG
                    cur_gate_time = qubit_params.get_duration2QG(cur_qubit[0], cur_qubit[1], cur_sec_ops['sequence'])   #NOTE: This assumes that it's not a sequence, but just a singular list for control/target operations
                    arr_qubit_auxs.append(cur_qubit[0])
                    arr_qubits.append(cur_qubit[1])
                    for m in range(2):
                        start_time = cur_qubit_gate_time_indices[cur_qubit[m]]  #Should start/end times be the same across all qubits...
                        cur_qubit_gate_time_indices[cur_qubit[m]] += cur_gate_time
                        end_time = cur_qubit_gate_time_indices[cur_qubit[m]]
                    arr_start_times.append(start_time)
                    arr_end_times.append(end_time)
                    arr_gate_types.append( self._get_1QG_name(*(cur_sec_ops['sequence'][1])) )
                    arr_operations.append(cur_sec_ops['sequence'][1][0])
                    arr_col_intens.append(cur_sec_ind/len(gate_schedule['commands']))
                    continue
            #Process it as a 1QG
            for cur_gate in cur_sec_ops['sequence']:
                if cur_gate[0] == 'Reset':
                    cur_name = 'Reset'
                    arr_operations.append('R')
                elif cur_gate[0] == 'Measure':
                    cur_name = self._measure_label
                    arr_operations.append('M')
                else:
                    cur_name = self._get_1QG_name(*cur_gate)
                    arr_operations.append(cur_gate[0])

                cur_gate_time = qubit_params.get_duration(cur_qubit, cur_gate)
                #
                arr_qubits.append(cur_qubit)
                arr_qubit_auxs.append(-1)
                arr_start_times.append(cur_qubit_gate_time_indices[cur_qubit])
                cur_qubit_gate_time_indices[cur_qubit] += cur_gate_time
                arr_end_times.append(cur_qubit_gate_time_indices[cur_qubit])
                arr_gate_types.append(cur_name)
                arr_col_intens.append(cur_sec_ind/len(gate_schedule['commands']))
                pass

        df = pd.DataFrame({
            'qubits':arr_qubits,
            'qubitsAux':arr_qubit_auxs,
            'start_time':arr_start_times,
            'end_time':arr_end_times,
            'gate_type':arr_gate_types,
            'col_intensity':arr_col_intens,
            'operation':arr_operations
        })

        return df

    def plot_schedule(self, gate_schedule, qubit_params:ScheduleParametersBase, output_file_path:str, title: str = "", debug_colour_scheme=False):
        """
        Generates an interactive Bokeh timeline plot using a simplified data model.
        """

        df = self.tabulate_schedule(gate_schedule, qubit_params)
        
        end_times = df['end_time'].to_numpy()
        norm_fac, norm_prefix = Miscellaneous.get_metric_multiplier(end_times)
        df['start_time'] /= norm_fac
        df['end_time'] /= norm_fac
        
        df['duration'] = df['end_time'] - df['start_time']
        df['centre'] = (df['start_time']+df['end_time'])/2
        df['durationBy4'] = df['duration']/4

        source = bokeh.models.ColumnDataSource(df)
        
        all_qubits = pd.concat([df['qubits'], df['qubitsAux']]).dropna()
        num_qubits = all_qubits.max() + 1 if not all_qubits.empty else 1
        
        wheel_zoom = bokeh.models.WheelZoomTool(dimensions="width")
        wheel_zoom.modifiers = {"ctrl": True}
        p = bokeh.plotting.figure(width=1000, height=500, title=title,x_axis_label=f"Time ({norm_prefix}s)",y_axis_label="Physical Qubit Index",x_axis_type="linear",
                                  y_range=bokeh.models.Range1d(num_qubits - 0.5, -0.5), tools="",active_scroll=wheel_zoom, sizing_mode="stretch_width"
        )
        p.add_tools(PanTool(dimensions="width"), wheel_zoom, bokeh.models.BoxZoomTool(dimensions="width"), bokeh.models.ResetTool())
        p.yaxis.ticker = list(range(num_qubits))
        p.xaxis.axis_label_text_font_size = "16pt"
        p.yaxis.axis_label_text_font_size = "16pt"
        p.xaxis.major_label_text_font_size = "14pt"
        p.yaxis.major_label_text_font_size = "14pt"

        #Plot 1Q gates
        source_1q = bokeh.models.ColumnDataSource(df[df['qubitsAux'] == -1])
        if debug_colour_scheme:
            mapper = bokeh.transform.linear_cmap('col_intensity', palette=bokeh.palettes.Viridis256, low=0, high=1)
        else:
            gate_types = ['X', 'Y', 'Z', 'M', 'D', 'W', 'R']
            gate_colors = ['#0077BB', '#33BBEE', '#009988', '#CC3311', '#BBBBBB', '#EE3377', '#BBBBBB']
            mapper = bokeh.transform.factor_cmap('operation', palette=gate_colors, factors=gate_types)
        rect_renderer = p.rect(
            x='centre', 
            y='qubits', 
            width='duration', 
            height=0.8, 
            source=source_1q, 
            line_color="black",
            fill_color=mapper,
            alpha=1.0,
            legend_field='gate_type'
        )
        p.text(x='centre', y='qubits', text='gate_type', source=source_1q, text_align='center', text_baseline='middle', text_color="black")

        #Plot 2Q gates
        source_2q = bokeh.models.ColumnDataSource(df[df['qubitsAux'] != -1])
        inter_renderer = p.segment(x0='centre', y0='qubits', x1='centre', y1='qubitsAux', 
            source=source_2q, line_color="black", line_width=4, legend_label="2-Qubit Gate",alpha=0.9
        )
        rect_renderer = p.rect( x='centre',  y='qubitsAux',  width='durationBy4', height=0.6,
            border_radius=15, source=source_2q,  line_color="black", fill_color="black", alpha=0.9
        )
        rect_renderer = p.rect(x='centre', y='qubits', width='duration', height=0.8, 
            source=source_2q, line_color="black", fill_color=mapper, alpha=1.0,
        )
        p.text(x='centre', y='qubits', text='gate_type', source=source_2q, text_align='center', text_baseline='middle', text_color="black")

        z_source = bokeh.models.ColumnDataSource( df[(df['operation'] == 'Z') & (df['qubitsAux'] == -1)] )
        p.text(
            x='centre',
            y='qubits',
            text='gate_type',
            source=z_source,
            text_align='center',
            text_baseline='middle',
            text_color='black',
            background_fill_color='#009988',
            background_fill_alpha=0.99,
            border_line_color='black',
            border_line_alpha=1.0,
        )

        p.legend.click_policy = "hide"
        bokeh.io.save(p, output_file_path)

    def check_ZI_compatibility(self, timing_schedule, qasm_qubit_params:ScheduleParametersBase, **kwargs):
        #Perform simple checks before compilation
        leTable = self.tabulate_schedule(timing_schedule, qasm_qubit_params)
        leTableMeas = leTable[leTable['gate_type'].str.contains("QMEAS", na=False)]
        if len(leTableMeas) > 1:
            leTableMeas = leTableMeas.sort_values(by='start_time').reset_index(drop=True)
            ###################
            #Overlap check
            #
            #Apparently this exists as LabOneQ calculates the measurement final multiplexed pulse by summing all the
            #signals together. This aligns with the kernel and has a fixed length in memory - i.e. it could be theoretically
            #unbounded with cascading measurement pulses. Making them start at the same time places an upper bound - i.e.
            #the maximum allowed measurement time... 
            for m in range(len(leTableMeas)):
                for n in range(m + 1, len(leTableMeas)):
                    start_m, end_m = leTableMeas.loc[m, 'start_time'], leTableMeas.loc[m, 'end_time']
                    start_n, end_n = leTableMeas.loc[n, 'start_time'], leTableMeas.loc[n, 'end_time']
                    # Check for overlap: max(starts) < min(ends)
                    overlap = max(start_m, start_n) < min(end_m, end_n)
                    # Check condition 1: Overlap AND different start times
                    Miscellaneous
                    assert not (overlap and start_m != start_n), f"ZI HW limitation: overlapping measure pulses at {Miscellaneous.get_units(start_m)}s and {Miscellaneous.get_units(start_n)}s do not start at the same time."
            #
            ###################
            #Gap check
            #
            #Basically there must be about 20-30ns gap between multiple acquisitions...
            time_threshold = kwargs.get('min_buffer_between_acquisitions', 40e-9)
            for m in range(len(leTableMeas) - 1):   #It's a sorted list, so it can be checked sequentially...
                end_m = leTableMeas.loc[m, 'end_time']
                start_n = leTableMeas.loc[m+1, 'start_time']            
                # Check for non-overlap (gap exists)
                if end_m < start_n:
                    gap = start_n - end_m
                    # Check condition 2: Gap is small
                    assert gap >= time_threshold, f"ZI HW limitation: the gap between multiple non-overlapping measure pulses must be at least 20-30ns. Check gap between {Miscellaneous.get_units(end_m)}s and {Miscellaneous.get_units(start_n)}s."

    def check_ZI_max_shots(self, timing_schedule, qasm_qubit_params:ScheduleParametersBase, AcquisitionMode:str, AveragingType:str):
        """
        AcquisitionMode = Discrimination | Integration | Raw
        AveragingType = AverageRepetitions | SingleShotCounts
        """
        leTable = self.tabulate_schedule(timing_schedule, qasm_qubit_params)
        leTableMeas = leTable[leTable['gate_type'].str.contains("QMEAS", na=False)]
        acq_mode = AcquisitionMode.lower()
        avg_mode = AveragingType.lower()
        if acq_mode == 'raw':
            req_samples = 4096 * len(leTableMeas)   #TODO: Remove the 2us hard-coding on SHFQC+...
            assert req_samples < 2**16, f"Cannot fit all the measurements into memory when using RAW mode in a single cycle of acquisition ({req_samples} samples cannot fit in 64k)."
            if avg_mode == 'singleshotcounts':
                return int(2**16 / req_samples * 2) #No idea why we need that extra factor of 2 here...
            else:
                return 2**16
        elif acq_mode == 'discrimination':
            if avg_mode == 'singleshotcounts':
                assert len(leTableMeas) <= 2**16, f"Cannot take this many measurements in a single cycle of acquisition ({len(leTableMeas)} samples cannot fit in 64k)."
                return int(2**16 / len(leTableMeas))
            else:
                return 2**16
        else:
            return 2**16

