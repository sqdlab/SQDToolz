import os
import re
import openqasm3
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatch
from sqdtoolz.HAL.SOFTqpu import SOFTqpu
from sqdtoolz.Utilities.OpenQASM import ScheduleParametersBase, QASMCompatibleQubitSingle
import pandas as pd
from sqdtoolz.Utilities.Miscellaneous import Miscellaneous
import bokeh
from bokeh.models import PanTool

class SQDQasmVisitor(openqasm3.visitor.QASMVisitor):
    def __init__(self):
        super().__init__()
        self.variables = {}
        self._gate_defs = {}
        self._commands = []
        self._qubits = {}
        self._bits = {}

    #Not required as includes are handled separately...
    # def visit_Include(self, node):
    #     node.filename
    #     print(f"Quantum register declared: {node.name} of size {node.size}")
    #     return super().visit_QuantumDeclaration(node)

    def visit_QuantumGateDefinition(self, node):
        self._gate_defs[node.name.name] = node

    def visit_QubitDeclaration(self, node):
        if node.size == None:
            reg_size = 1
        else:
            reg_size = node.size.value
        self._qubits[node.qubit.name] = reg_size

    def visit_ClassicalDeclaration(self, node):
        if isinstance(node.type, openqasm3.ast.BitType):
            if node.type.size == None:
                reg_size = 1
            else:
                reg_size = node.type.size.value
            self._bits[node.identifier.name] = reg_size
    
    def visit_QuantumGate(self, node):
        args = [self._eval_arg(x) for x in node.arguments]
        qargs = []
        for x in node.qubits:
            qargs += self._eval_qarg(x)
        self._commands += self._eval_func(node, args, qargs)

    def visit_QuantumBarrier(self, node):
        # self._commands.append({'type':'barrier'})
        #Pointless as we won't be doing commutation/collapse optimisation here...
        pass

    def visit_DelayInstruction(self, node):
        cur_delay = self._eval_arg(node.duration)
        if not isinstance(cur_delay, tuple):    #Typically must have unit, but 0 delay doesn't require units...abs
            cur_delay = (cur_delay, 's')
        qargs = []
        for x in node.qubits:
            qargs += self._eval_qarg(x)
        self._commands.append({'type':'delay', 'targets':qargs, 'length':cur_delay})

    def visit_QuantumMeasurementStatement(self, node):
        self._commands.append( {'type': 'measure', 'qubit': self._eval_qarg(node.measure.qubit), 'store': self._eval_bits_arg(node.target)} )

    def _eval_func(self, node, override_args:list, override_qargs:list, extra_mods:list=[]):
        cur_func_name = node.name.name
        assert cur_func_name == 'U' or cur_func_name in self._gate_defs, f"Line {node.span.start_line}: Function '{cur_func_name}' is undefined"

        if cur_func_name == 'U':
            assert len(override_args) == 3, f"Line {node.span.start_line}: The operator 'U' must have 3 angles."
            ctrl_mods = []
            if len(override_qargs) > 1:
                for cur_modifier in extra_mods + node.modifiers: #i.e. the extra_mods list prepends any internal ctrl commands etc...
                    if cur_modifier.argument == None:
                        num = 1
                    else:
                        num = self._eval_arg(cur_modifier.argument)
                    if cur_modifier.modifier.name == 'ctrl':
                        ctrl_mods += ['ctrl']*num
                    elif cur_modifier.modifier.name == 'negctrl':
                        ctrl_mods += ['negctrl']*num
            return [{'type': 'gate', 'angles': override_args, 'controls':ctrl_mods, 'targets': override_qargs}]
        else:
            cur_func_defn = self._gate_defs[cur_func_name]
            args = [x.name for x in cur_func_defn.arguments]
            qargs = [x.name for x in cur_func_defn.qubits]
            #NOTE: OpenQASM3 specification does not seem to allow for default arguments here...
            assert len(override_args) == len(args), f"Line {node.span.start_line}: The gate {cur_func_name} requires {len(args)} arguments, not {len(override_args)}."
            map_args = {args[x]:override_args[x] for x in range(len(args))}
            num_qargs = len(extra_mods) + len(node.modifiers) + len(qargs)
            assert len(override_qargs) == num_qargs, f"Line {node.span.start_line}: The gate {cur_func_name} requires {num_qargs} qubits, not {len(override_qargs)}."
            q_mod_args = [override_qargs[x] for x in range(len(extra_mods))]
            q_mod_args += [override_qargs[x+len(q_mod_args)] for x in range(len(node.modifiers))]
            map_qargs = {qargs[x]:override_qargs[len(q_mod_args) + x] for x in range(len(qargs))}
            #
            ret_instructions = []
            for cur_statement in cur_func_defn.body:
                ret_instructions += self._eval_func(cur_statement, [self._eval_arg(x, map_args) for x in cur_statement.arguments], q_mod_args + [map_qargs[x.name] for x in cur_statement.qubits], extra_mods + node.modifiers)
            return ret_instructions

    def _eval_qarg(self, qarg):
        #It returns a list as a register passed without indices implies automatic slicing over all the individual qubits within the register...
        #NOTE: Quantum types cannot be an array, so the only Indexed Identifier will be [[n]] for the register index n...
        if isinstance(qarg, openqasm3.ast.Identifier):
            assert qarg.name in self._qubits, f"The qubit register '{qarg.name}' is undefined."
            return [(qarg.name, x) for x in range(self._qubits[qarg.name])]   #THIS MEANS IT IS FULL REG SIZE AND MUST BE MAPPED AS THUS!
        elif isinstance(qarg, openqasm3.ast.IndexedIdentifier):
            assert qarg.name.name in self._qubits, f"The qubit register '{qarg.name.name}' is undefined."
            return [(qarg.name.name, self._eval_arg(qarg.indices[0][0]))]

    def _eval_bits_arg(self, bit_arg):
        #NOTE: Quantum types cannot be an array, so the only Indexed Identifier will be [[n]] for the register index n...
        if isinstance(bit_arg, openqasm3.ast.Identifier):
            assert bit_arg.name in self._bits, f"The register '{bit_arg.name}' is undefined."
            return [(bit_arg.name, x) for x in range(self._bits[bit_arg.name])]   #THIS MEANS IT IS FULL REG SIZE AND MUST BE MAPPED AS THUS!
        elif isinstance(bit_arg, openqasm3.ast.IndexedIdentifier):
            assert bit_arg.name.name in self._bits, f"The register '{bit_arg.name.name}' is undefined."
            return [(bit_arg.name.name, self._eval_arg(bit_arg.indices[0][0]))]

    def _eval_arg(self, argument, dict_args = {}):
        if isinstance(argument, (int, float)):    #More just here for safety...
            return argument
        elif isinstance(argument, (openqasm3.ast.IntegerLiteral, openqasm3.ast.FloatLiteral)):
            return argument.value
        elif isinstance(argument, openqasm3.ast.Identifier):
            if argument.name == 'π' or argument.name == 'pi':
                return np.pi
            elif argument.name in dict_args:
                return self._eval_arg(dict_args[argument.name]) #More just here for safety - could just return the dictionary value...
        elif isinstance(argument, openqasm3.ast.DurationLiteral):
            return (argument.value, argument.unit.name)
        elif isinstance(argument, openqasm3.ast.UnaryExpression):
            if argument.op.name == '-':
                return -self._eval_arg(argument.expression, dict_args)
        elif isinstance(argument, openqasm3.ast.BinaryExpression):
            if argument.op.name == '+':
                return self._eval_arg(argument.lhs, dict_args) + self._eval_arg(argument.rhs, dict_args)
            elif argument.op.name == '-':
                return self._eval_arg(argument.lhs, dict_args) - self._eval_arg(argument.rhs, dict_args)
            elif argument.op.name == '*':
                return self._eval_arg(argument.lhs, dict_args) * self._eval_arg(argument.rhs, dict_args)
            elif argument.op.name == '/':
                return self._eval_arg(argument.lhs, dict_args) / self._eval_arg(argument.rhs, dict_args)
            elif argument.op.name == '**':
                return self._eval_arg(argument.lhs, dict_args) ** self._eval_arg(argument.rhs, dict_args)
        else:
            assert False, f"Type {argument} not implemented!"


class ScheduleParametersSoftQPUZI(ScheduleParametersBase):
    def __init__(self, softQPU_ZI:SOFTqpu):
        self._qpu = softQPU_ZI
    
    def get_duration(self, qubit_index:int, gate_type: str|list|tuple) -> float:
        if isinstance(gate_type, (list,tuple)):
            if gate_type[0] == 'D':
                return gate_type[1]
            elif gate_type[0] == 'Measure':
                return self.get_duration_measurement(qubit_index)
        return self._qpu.get_qubit_obj(qubit_index).get_gate_duration(gate_type)
    
    def get_duration_measurement(self, qubit_index:int):
        return self._qpu.get_qubit_obj(qubit_index).get_measure_duration()

    def get_duration2QG(self, qubit1_index:int, qubit2_index:int, gate_type:list) -> float:
        zi_elem,_ = self._qpu.get_qubit_coupling_objs(qubit1_index, qubit2_index)[0].get_ZI_parameters()
        return zi_elem.get_gate_duration(gate_type, [self._qpu.get_qubit_obj(qubit1_index), self._qpu.get_qubit_obj(qubit2_index)])
    
    @property
    def dt(self):
        return 1.0/2e9  #TODO: Maybe make this properly query it?


class ParserOpenQASM:
    def __init__(self, main_file: str, source_dirs: list[str], **kwargs):
        self._extract_includes(main_file, source_dirs)
        overall_includes = []
        self._get_include_tree([main_file], overall_includes, source_dirs)
        #
        self._visitor = SQDQasmVisitor()
        for m, cur_file in enumerate(overall_includes):
            ast = openqasm3.parser.parse(self._open_file_strip_comments(cur_file))
            self._visitor.visit(ast)
        #
        self._measure_label = kwargs.get('measure_label', "∅")

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
        cur_includes = self._extract_includes(current_file, source_dirs)
        for cur_include in cur_includes:
            assert not cur_include in cur_includes_stack, f"There is a circular dependency with {cur_include}."
            self._get_include_tree(cur_includes_stack + [cur_include], overall_includes, source_dirs)
        overall_includes.append(self._find_file(current_file, source_dirs))
        return

    def _extract_includes(self, file_path: str, source_dirs: list[str]):
        file_path = self._find_file(file_path, source_dirs)
        #################
        lines = self._open_file_strip_comments(file_path)
        lines = "".join(lines).replace('\n','').split(';')
        inc_files = []
        for line in lines:
            leLine = line.strip().lower()
            if leLine.startswith("include"):
                inc_files.append(leLine.replace('\'','\"').split("\"")[-2])
        return inc_files

    def _open_file_strip_comments(self, file_path):
        with open(file_path, encoding="utf-8") as file: #If it is not UTF-8, it'll read the pi symbol as the Euro symbol etc...
            lines = [line.rstrip() for line in file]
        # lines = "\n".join(lines)
        # lines = re.sub('//.*?\n','\n', lines, flags=re.DOTALL)
        #
        # lines = lines.split('\n')
        # lines = [x.strip() for x in lines if x != '']
        return '\n'.join(lines)

    def create_schedule(self, params:ScheduleParametersBase):
        #Initialise qubits and sync times
        qubit_reg_mappings = {}
        for cur_qreg in self._visitor._qubits:
            for m in range(self._visitor._qubits[cur_qreg]):
                qubit_reg_mappings[(cur_qreg,m)] = len(qubit_reg_mappings)
        final_commands = []
        cur_qubit_commands = [[] for x in range(len(qubit_reg_mappings))]
        qubit_sync_times = np.zeros(len(qubit_reg_mappings))
        last_sync_command_indices = [-1]*len(qubit_reg_mappings)
        #
        for cur_command in self._visitor._commands + [{'type':'end', 'targets':[x for x in qubit_reg_mappings]}]:
            sync_command = False
            if cur_command['type'] == 'gate' and len(cur_command['controls']) > 0:
                sync_command = True
            elif cur_command['type'] == 'delay' and len(cur_command['targets']) > 1:
                sync_command = True
            elif cur_command['type'] == 'end':
                sync_command = True

            if not sync_command:
                if cur_command['type'] == 'gate':
                    cur_qubit_commands[qubit_reg_mappings[cur_command['targets'][0]]].append(self._process_1Q_gate(cur_command['angles']))
                elif cur_command['type'] == 'delay':
                    cur_qubit_commands[qubit_reg_mappings[cur_command['targets'][0]]].append(self._process_delay(cur_command['length'], params.dt))
                elif cur_command['type'] == 'measure':
                    cur_qubit_commands[qubit_reg_mappings[cur_command['qubit'][0]]].append(('Measure',cur_command['store'][0]))   #TODO: Check if multi-qubit registers can be stored/measured in OpenQASM3?
            else:
                ####
                #Calculate new synchronisation point
                #
                cur_targ_indices = [qubit_reg_mappings[x] for x in cur_command['targets']]
                cur_seq_lens = np.zeros(len(cur_targ_indices))
                for m,cur_qubit_ind in enumerate(cur_targ_indices):
                    cur_len = 0
                    for cur_op in cur_qubit_commands[cur_qubit_ind]:
                        if cur_op[0] == 'D':    #It is a delay...
                            cur_len += cur_op[1]
                        elif cur_op[0] == 'Measure':
                            cur_len += params.get_duration_measurement(cur_qubit_ind)
                        else:   #It is just X, Y, Z for the gate type...
                            cur_len += params.get_duration(cur_qubit_ind, cur_op)
                    cur_seq_lens[m] = cur_len
                new_sync_point = np.max(qubit_sync_times[cur_targ_indices] + cur_seq_lens)
                ####
                #Pad/sequence Delays on qubits and add qubit sequences to final command list
                #
                for m,cur_qubit_ind in enumerate(cur_targ_indices):
                    #Process residual/stretch delays
                    residual = new_sync_point - (qubit_sync_times[cur_qubit_ind] + cur_seq_lens[m])
                    cur_seg_len = new_sync_point - qubit_sync_times[cur_qubit_ind]
                    #TODO: Check for stretches and synthesise delays here!
                    cur_qubit_commands[cur_qubit_ind].append(('D',residual))
                    #
                    #Add sequence to command list and update current synchronised time for the qubit
                    play_after = None if last_sync_command_indices[cur_qubit_ind] == -1 else last_sync_command_indices[cur_qubit_ind]
                    final_commands.append({'qubit_index': cur_qubit_ind, 'sequence': cur_qubit_commands[cur_qubit_ind], 'after':play_after, 'length':cur_seg_len})
                    cur_qubit_commands[cur_qubit_ind] = []
                    qubit_sync_times[cur_qubit_ind] = new_sync_point
                ####
                #Add the actual command for the qubits and update the last synchronised command-sequence index
                if cur_command['type'] == 'gate':
                    cur_target_gate = self._process_1Q_gate(cur_command['angles'])
                    cur_play_after_index = None if len(final_commands) == 0 else len(final_commands)-1
                    gate_duration = params.get_duration2QG(cur_targ_indices[0], cur_targ_indices[1], cur_command['controls'] + [cur_target_gate])
                    final_commands.append({'qubit_index': cur_targ_indices, 'sequence': cur_command['controls'] + [cur_target_gate], 'after':cur_play_after_index, 'length':gate_duration})
                    #Set all gate-sequences on these qubits to be synchronised to come after this new multi-qubit gate...
                    for cur_qubit_ind in cur_targ_indices:
                        qubit_sync_times[cur_qubit_ind] += gate_duration   #TODO: Must add 2QG time and pass this in - perhaps by a graph?
                        last_sync_command_indices[cur_qubit_ind] = len(final_commands)-1
                elif cur_command['type'] == 'delay':
                    for cur_qubit_ind in cur_targ_indices:
                        cur_delay_cmd = self._process_delay(cur_command['length'], params.dt)
                        cur_play_after_index = None if last_sync_command_indices[cur_qubit_ind] == -1 else last_sync_command_indices[cur_qubit_ind]
                        final_commands.append({'qubit_index': cur_qubit_ind, 'sequence': [cur_delay_cmd], 'after':cur_play_after_index, 'length':cur_delay_cmd[1]})
                        qubit_sync_times[cur_qubit_ind] += cur_delay_cmd[1]
                        last_sync_command_indices[cur_qubit_ind] = len(final_commands)-1
                #Don't need to check if it's 'end' as it's the end...
        #
        return {'qubit_mappings': qubit_reg_mappings, 'commands':final_commands}

    def _process_delay(self, delay_params, dt_time):
        if delay_params[1] == 's':
            return ('D', delay_params[0])
        elif delay_params[1] == 'ms':
            return ('D', delay_params[0] * 1e-3)
        elif delay_params[1] == 'µs' or delay_params[1] == 'us':
            return ('D', delay_params[0] * 1e-6)
        elif delay_params[1] == 'ns':
            return ('D', delay_params[0] * 1e-9)
        elif delay_params[1] == 'dt':
            return ('D', delay_params[0] * dt_time)
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

    def get_axis_angle_from_unitary(self, unitary_angles):
        #Based on their definition here: https://openqasm.com/language/gates.html
        #That is for theta,phi,lambda, it's a ZYZ rotation done via lambda, theta and phi...
        vtheta,vphi,vlambda = unitary_angles
        matU = 1/2*np.array([[1+np.exp(1j*vtheta), -1j*np.exp(1j*vlambda)*(1-np.exp(1j*vtheta))],
                             [1j*np.exp(1j*vphi)*(1-np.exp(1j*vtheta)), np.exp(1j*(vlambda+vphi))*(1+np.exp(1j*vtheta))]])
        #Note that R(x) = cos(x/2)*I_2 - i*sin(x/2)*(n.sigma)
        pauli_I2 = (matU[0,0]+matU[1,1])/2
        pauli_Z  = ((matU[0,0]-matU[1,1]))/2
        pauli_X = ((matU[0,1]+matU[1,0]))/2
        pauli_Y = ((matU[0,1]-matU[1,0]))/2j
        #Calculate global phase
        pauli_vec = np.array([pauli_I2, pauli_X/-1j, pauli_Y/-1j, pauli_Z/-1j])
        global_phase = np.exp(-1j*np.angle(pauli_vec[np.argmax(np.abs(pauli_vec))]))
        pauli_vec *= global_phase
        #
        #It's now in a form: cos(x/2)*I_2 + sin(x/2)*(n.sigma)
        rotation_axis = pauli_vec[1:]
        sin_angle_2 = np.linalg.norm(rotation_axis)
        rotation_axis = rotation_axis / sin_angle_2
        rotation_angle = 2*np.arctan2(np.real(sin_angle_2), np.real(pauli_vec[0]))

        return np.real(rotation_axis), rotation_angle

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
        if axis == 'Measure':
            return self._measure_label
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
        cur_qubit_gate_time_indices = [0.0 for x in range(len(gate_schedule['qubit_mappings']))]
        #
        arr_qubits = []
        arr_qubit_auxs = []
        arr_start_times = []
        arr_end_times = []
        arr_gate_types = []
        arr_col_intens = []
        #
        for cur_sec_ind,cur_sec_ops in enumerate(gate_schedule['commands']):
            cur_qubit = cur_sec_ops['qubit_index']
            if isinstance(cur_qubit, (list,tuple)):
                if len(cur_qubit) == 1:
                    cur_qubit = cur_qubit[0]    #A strange case that may never exist?
                else:
                    #Process it as a 2QG
                    cur_gate_time = qubit_params.get_duration2QG(*cur_qubit, cur_sec_ops['sequence'])   #NOTE: This assumes that it's not a sequence, but just a singular list for control/target operations
                    arr_qubit_auxs.append(cur_qubit[0])
                    arr_qubits.append(cur_qubit[1])
                    for m in range(2):
                        start_time = cur_qubit_gate_time_indices[cur_qubit[m]]  #Should start/end times be the same across all qubits...
                        cur_qubit_gate_time_indices[cur_qubit[m]] += cur_gate_time
                        end_time = cur_qubit_gate_time_indices[cur_qubit[m]]
                    arr_start_times.append(start_time)
                    arr_end_times.append(end_time)
                    arr_gate_types.append( self._get_1QG_name(*(cur_sec_ops['sequence'][1])) )
                    arr_col_intens.append(cur_sec_ind/len(gate_schedule['commands']))
                    continue
            #Process it as a 1QG
            for cur_gate in cur_sec_ops['sequence']:
                cur_name = self._get_1QG_name(*cur_gate)
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
            'col_intensity':arr_col_intens
        })

        return df

    def plot_schedule(self, gate_schedule, qubit_params:ScheduleParametersBase, output_file_path:str, title: str = "Quantum Circuit Timeline (Simplified Data Model)"):
        """
        Generates an interactive Bokeh timeline plot using a simplified data model.
        """

        df = self.tabulate_schedule(gate_schedule, qubit_params)
        df['duration'] = df['end_time'] - df['start_time']
        df['centre'] = (df['start_time']+df['end_time'])/2
        df['durationBy4'] = df['duration']/4

        source = bokeh.models.ColumnDataSource(df)
        
        all_qubits = pd.concat([df['qubits'], df['qubitsAux']]).dropna()
        num_qubits = all_qubits.max() + 1 if not all_qubits.empty else 1
        
        wheel_zoom = bokeh.models.WheelZoomTool(dimensions="width")
        wheel_zoom.modifiers = {"ctrl": True}
        p = bokeh.plotting.figure(width=1000, height=500, title=title,x_axis_label="Time",y_axis_label="Qubit Index",x_axis_type="linear",
                                  y_range=(-0.5, num_qubits - 0.5),tools="",active_scroll=wheel_zoom, sizing_mode="stretch_width"
        )
        p.add_tools(PanTool(dimensions="width"), wheel_zoom, bokeh.models.BoxZoomTool(dimensions="width"), bokeh.models.ResetTool())

        #Plot 1Q gates
        source_1q = bokeh.models.ColumnDataSource(df[df['qubitsAux'] == -1])
        mapper = bokeh.transform.linear_cmap('col_intensity', palette=bokeh.palettes.Viridis256, low=0, high=1)
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

        p.legend.click_policy = "hide"
        bokeh.io.save(p, output_file_path)
