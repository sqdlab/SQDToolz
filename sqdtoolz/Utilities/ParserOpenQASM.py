from typing import List
import os
import re
import ply.lex
import ply.yacc
import numpy as np

class _ParserOpenQASM:
    # literals = r'=<>,.^"'
    reserved = {
        'gate' : 'GATE',
        'OPENQASM' : 'VERSION',
        'if' : 'IF',
        'else' : 'ELSE',
        'for' : 'FOR',
        'int' : 'INT',
        'opaque' : 'OPAQUE',
        'save_statevector' : 'SAVE_STATEVECTOR',
        'qubit' : 'QUBIT',
        'bit' : 'BIT',
        'measure' : 'MEASURE',
        'ctrl' : 'CONTROL',
        'negctrl' : 'NEGCONTROL'
        }
    tokens = (
        'ID',
        'NUMBER',
        'LBRACKET',
        'RBRACKET',
        'COMMA',
        'LBRACE',
        'RBRACE',
        'SEMICOLON',
        'LARRAY',
        'RARRAY',

        'PLUS',
        'MINUS',
        'MULTIPLY',
        'DIVIDE',
        'ASSIGN',
        'ASSIGNOLD',
        'ATCTRL'
        ) + tuple(reserved.values())
    t_ignore  = ' \t' #QASM is uses semi-colons, so new-lines are meaningless...
    #
    t_LBRACKET = r'\('
    t_RBRACKET = r'\)'
    t_COMMA = r','
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_SEMICOLON = r';'
    t_LARRAY = r'\['
    t_RARRAY = r'\]'
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_MULTIPLY = r'\*'
    t_DIVIDE = r'/'
    t_ASSIGN = r'='
    t_ASSIGNOLD = r'->'
    t_ATCTRL = r'@'


    def t_ID(self, t):
        r'[a-zA-Zα-ωΑ-Ω][a-zA-Z_0-9]*'
        t.type = self.reserved.get(t.value, 'ID')  # Check for reserved words
        return t

    def t_NUMBER(self,t):
        r'[.]?[+-]?\d+\.?\d*'
        try:
            t.value = int(t.value)
        except:
            t.value = float(t.value)
        return t

    def t_newline(self, t):
        r'\n+'
        self.lineno += len(t.value)     #i.e. if there are multiple new-lines...

    # Error handling rule
    def t_error(self, t):
        print(f"Illegal character '{t.value[0]}' in line {self.lineno}")
        t.lexer.skip(1)


    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('left', 'MULTIPLY', 'DIVIDE'),
    )
    start='program'

    def p_gatedec(self, p):
        '''gatedec : GATE ID params LBRACE statements RBRACE
                    | GATE ID LBRACKET params RBRACKET params LBRACE statements RBRACE
        '''
        if len(p) == 7:
            p[0] = ('gatedec', p[2], [], p[3], p[5])
        else:
            p[0] = ('gatedec', p[2], p[4], p[6], p[8])

    def p_params(self, p):
        '''params : ID
                | ID COMMA params
        '''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = [p[1]] + p[3]

    def p_ctrl_params_func_signature1(self, p):
        '''functionsignature : ID
                | ID LBRACKET expressions RBRACKET
                | ID LBRACKET expressions RBRACKET ATCTRL functionsignature
        '''
        if len(p) == 2:
            p[0] = [(p[1], [])]
        elif len(p) == 5:
            p[0] = [(p[1], p[3])]
        else:
            p[0] = [(p[1], p[3])] + p[6]

    def p_ctrl_params_func_signature2(self, p):
        '''functionsignature :
                | CONTROL
                | NEGCONTROL
                | CONTROL LBRACKET NUMBER RBRACKET
                | NEGCONTROL LBRACKET NUMBER RBRACKET
                | CONTROL ATCTRL functionsignature
                | NEGCONTROL ATCTRL functionsignature
                | CONTROL LBRACKET NUMBER RBRACKET ATCTRL functionsignature
                | NEGCONTROL LBRACKET NUMBER RBRACKET ATCTRL functionsignature
        '''
        if len(p) == 1:
            #TODO: Look into whether the compile-time constants can be allowed for ctrl/negctrl rather than just numbers...
            #It unwraps it here - perhaps do it like a preprocessor sweep before lex/yacc?
            #
            #ctrl/negctrl shouldn't conflict with function names as it's a reserved keyword...
            if p[1] == 'CONTROL':
                p[0] = [('ctrl')]
            else:
                p[0] = [('negctrl')]
        elif len(p) == 4:
            p[0] = [p[1]] + p[3]
        elif len(p) == 5:
            p[0] = [p[1]]*p[3]
        else:
            p[0] = [p[1]]*p[3] + p[6]


    #OPENQASM only allows indexing of qubits in the global scope...
    def p_params_indexed(self, p):
        '''indexedparams : ID
                        | ID COMMA indexedparams
                        | ID LARRAY NUMBER RARRAY
                        | ID LARRAY NUMBER RARRAY COMMA indexedparams
        '''
        if len(p) == 2:
            p[0] = [p[1]]
        elif len(p) == 4:
            p[0] = [p[1]] + p[3]
        elif len(p) == 5:
            p[0] = [(p[1], p[3])]
        else:
            p[0] = [(p[1], p[3])] + p[6]

    def p_expression(self, p):
        '''expression : expression PLUS expression
                    | expression MINUS expression
                    | expression MULTIPLY expression
                    | expression DIVIDE expression
                    | LBRACKET expression RBRACKET
                    | MINUS ID
                    | MINUS NUMBER
                    | MINUS expression
                    | ID
                    | NUMBER
        '''
        if len(p) == 4:
            if p[1] == '(' and p[3] == ')':
                p[0] = (p[2])
            else:
                p[0] = (p[2], p[1], p[3])
        elif len(p) == 3:
            p[0] = (p[1], p[2])
        else:
            p[0] = p[1]
    
    def p_expressions(self, p):
        '''expressions : expression
                | expression COMMA expressions
        '''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = [p[1]] + p[3]

    def p_functioncall(self, p):
        '''statement : functionsignature params SEMICOLON
        '''
        p[0] = ('functioncall', {'name':p[1], 'arguments':p[2]})

    def p_functioncall_global(self, p):
        '''statement : functionsignature indexedparams SEMICOLON
        '''
        p[0] = ('functioncall', {'name':p[1], 'arguments':p[2]})
    
    def p_version(self, p):
        '''globalstatement : VERSION NUMBER SEMICOLON
        '''
        p[0] = ('version', p[2])
    
    def p_savestatevector(self, p):
        '''globalstatement : OPAQUE SAVE_STATEVECTOR params SEMICOLON
                    | SAVE_STATEVECTOR params SEMICOLON
                    | OPAQUE SAVE_STATEVECTOR indexedparams SEMICOLON
                    | SAVE_STATEVECTOR indexedparams SEMICOLON
        '''
        p[0] = ('sim_construct', p[1:])

    def p_qubit(self, p):
        '''globalstatement : QUBIT ID SEMICOLON
                            | QUBIT LARRAY NUMBER RARRAY ID SEMICOLON
        '''
        if len(p) == 7:
            p[0] = ('dec_qubit', p[5], p[3])
        else:
            p[0] = ('dec_qubit', p[2], 1)

    def p_bit(self, p):
        '''globalstatement : BIT ID SEMICOLON
                            | BIT LARRAY NUMBER RARRAY ID SEMICOLON
        '''
        if len(p) == 7:
            p[0] = ('dec_bit', p[5], p[3])
        else:
            p[0] = ('dec_bit', p[2], 1)

    def p_measure(self, p):
        '''globalstatement : ID ASSIGN MEASURE ID SEMICOLON
                            |  ID LARRAY NUMBER RARRAY ASSIGN MEASURE ID SEMICOLON
                            |  ID ASSIGN MEASURE ID LARRAY NUMBER RARRAY SEMICOLON
                            |  ID LARRAY NUMBER RARRAY ASSIGN MEASURE ID LARRAY NUMBER RARRAY SEMICOLON
        '''
        if len(p) == 5:
            p[0] = ('measure', p[4], p[1])
        elif len(p) == 8:
            if p[2] == '[':
                p[0] = ('measure', p[7], (p[1], p[3]))
            else:
                p[0] = ('measure', (p[4], p[6]), p[1])
        else:
            p[0] = ('measure', (p[7], p[9]), (p[1], p[3]))
    #
    #NOTE: The measurement tuples are: (Qubit to Measure, Classical Register to Store)
    def p_measure_old(self, p):
        '''globalstatement : MEASURE ID ASSIGNOLD ID SEMICOLON
                            |  MEASURE ID LARRAY NUMBER RARRAY ASSIGNOLD ID SEMICOLON
                            |  MEASURE ID ASSIGNOLD ID LARRAY NUMBER RARRAY SEMICOLON
                            |  MEASURE ID LARRAY NUMBER RARRAY ASSIGNOLD ID LARRAY NUMBER RARRAY SEMICOLON
        '''
        if len(p) == 5:
            p[0] = ('measure', p[2], p[4])
        elif len(p) == 8:
            if p[3] == '[':
                p[0] = ('measure', (p[2], p[4]), p[7])
            else:
                p[0] = ('measure', p[2], (p[4], p[6]))
        else:
            p[0] = ('measure', (p[2], p[4]), (p[7], p[9]))


    def p_statements(self, p):
        '''statements : statement
                    | statement statements
                    | globalstatement
                    | globalstatement statements
        '''
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = [p[1]] + p[2]

    def p_program(self, p):
        '''program : 
                    | statement
                    | globalstatement
                    | gatedec
                    | statement program
                    | globalstatement program
                    | gatedec program
        '''
        if len(p) == 1:
            pass
        elif len(p) == 2:
            p[0] = [p[1]]
        elif p[2] == None:
            p[0] = [p[1]]
        else:
            p[0] = [p[1]] + p[2]
    
    def p_error(self, p):
        assert False, f"Syntax error on line number {self.lineno} at '{p.value}'"

    def build(self, **kwargs):
        self.lexer = ply.lex.lex(object=self,**kwargs)

    def __init__(self):
        pass
    
    def _tokenise(self, str_input):
        self.lexer.input(str_input)
        self.lineno = 1
        while True:
            tok = self.lexer.token()
            if not tok:
                break      # No more input
            print(tok)
        print("\n")
    
    def parse(self, str_input):
        self.lineno = 1
        parser = ply.yacc.yacc(module=self)
        result = parser.parse(str_input, lexer=self.lexer, debug=True)
        return result



class ParserOpenQASM:
    def __init__(self, main_file: str, source_dirs: List[str]):
        self._extract_includes(main_file, source_dirs)
        overall_includes = []
        self._get_include_tree([main_file], overall_includes, source_dirs)
        self._gate_defs = {}
        self._qubits = []
        self._bits = []
        self._operations = []
        for m, cur_file in enumerate(overall_includes):
            self._parse_file(cur_file)
        self.compiled_operations = self._final_compile()

    def _get_include_tree(self, cur_includes_stack: List[str], overall_includes: List[str], source_dirs: List[str]):
        current_file = cur_includes_stack[-1]
        cur_includes = self._extract_includes(current_file, source_dirs)
        for cur_include in cur_includes:
            assert not cur_include in cur_includes_stack, f"There is a circular dependency with {cur_include}."
            self._get_include_tree(cur_includes_stack + [cur_include], overall_includes, source_dirs)
        overall_includes.append(current_file)
        return

    def _extract_includes(self, file_path: str, source_dirs: List[str]):
        if not os.path.exists(file_path):
            found = False
            for cur_source_dir in source_dirs:
                cur_path = os.path.join(cur_source_dir, file_path)
                if os.path.exists(cur_path):
                    file_path = cur_path
                    found = True
                    break
            assert found, f"Could not find file {file_path}"
        #################
        lines = self._open_file_strip_comments(file_path)
        lines = "".join(lines).replace('\n','').split(';')
        inc_files = []
        for line in lines:
            leLine = line.strip().lower()
            if leLine.startswith("include"):
                inc_files.append(leLine.split("\"")[-2])
        return inc_files

    def _open_file_strip_comments(self, file_path):
        with open(file_path) as file:
            lines = [line.rstrip() for line in file]
        lines = "\n".join(lines)
        lines = re.sub('//.*?\n','\n', lines, flags=re.DOTALL)
        #
        lines = lines.split('\n')
        lines = [x.strip() for x in lines if x != '']
        return lines

    def _parse_file(self, file_path: str):
        gate_defs = {}
        lines = self._open_file_strip_comments(file_path)
        
        str_code = '\n'.join(lines)
        str_code = re.sub('include?(.*?);', '', str_code, flags=re.DOTALL) #Strip include statements
        leParser = _ParserOpenQASM()
        leParser.build()
        leParser._tokenise(str_code)
        parsed_data = leParser.parse(str_code)

        for statement in parsed_data:
            if statement[0] == 'gatedec':
                self._gate_defs[statement[1]] = {'input_args': statement[2], 'output_args': statement[3], 'function': statement[4]}
            elif statement[0] == 'sim_construct':
                print("Warning: Ignoring simulation constructs.")
            elif statement[0] == 'dec_qubit':
                self._qubits.append((statement[1], statement[2]))
            elif statement[0] == 'dec_bit':
                self._bits.append((statement[1], statement[2]))
            elif statement[0] == 'functioncall':
                self._operations.append(statement[1])
    
    def _eval_expression(self, expr, wildcards):
        if isinstance(expr, (int, float)):
            return expr
        if isinstance(expr, str):
            #TODO: Look up default fundamental constants supported by OpenQASM...
            if expr == 'pi' or expr == 'π':
                return np.pi
            assert expr in wildcards, f"Argument {expr} could not be evaluated."
            return self._eval_expression(wildcards[expr], wildcards)
            
        #Should be fine as the wildcards cannot be the reserved tokens...
        expr = [(wildcards[x] if x in wildcards else x) for x in list(expr)]
        if len(expr) == 1:
            return self._eval_expression(expr, wildcards)
        elif len(expr) == 2:
            return -self._eval_expression(expr[1],wildcards)
        else:
            arg1, arg2 = self._eval_expression(expr[1],wildcards) , self._eval_expression(expr[2],wildcards)
            if expr[0] == '+':
                return arg1 + arg2
            elif expr[0] == '-':
                return arg1 - arg2
            elif expr[0] == '*':
                return arg1 * arg2
            elif expr[0] == '/':
                return arg1 / arg2

    def _evaluate_func_signature(self, func_sign_list, wildcards):
        if len(func_sign_list) > 1:
            found_ind = -1
            new_sign_list = []
            for m, cur_func_sign_arg in enumerate(func_sign_list):
                if isinstance(cur_func_sign_arg, str) and (cur_func_sign_arg == 'ctrl' or cur_func_sign_arg == 'negctrl'):
                    new_sign_list.append(cur_func_sign_arg)
                else:
                    assert isinstance(cur_func_sign_arg, (tuple, list)), f"The argument {cur_func_sign_arg} is invalid in this controlled qubit sequence..."
                    assert found_ind == -1, "Ill-formed control argument for a controlled-gate; there can only be a unitary on one qubit..."
                    found_ind = m
                    new_sign_list.append(cur_func_sign_arg)
            assert found_ind != -1, "A controlled-gate sequence does not have a unitary on one of the qubits."
            cur_func = new_sign_list[found_ind]
        else:
            cur_func = func_sign_list[0]
        ret_list = [ (cur_func[0], [self._eval_expression(x, wildcards) for x in cur_func[1]]) ]
        if len(func_sign_list) > 1:
            new_sign_list[found_ind] = ret_list[0]
            ret_list = new_sign_list
        return ret_list

    def _replace_func_with_arguments(self, func_name, func_inputs, func_outputs):
        assert len(func_inputs) == len(self._gate_defs[func_name]['input_args']), f"The function {func_name} has {len(self._gate_defs[func_name]['input_args'])} arguments, not {len(func_inputs)}."
        input_wildcards = {k:func_inputs[m] for m,k in enumerate(self._gate_defs[func_name]['input_args'])}
        output_wildcards = {k:func_outputs[m] for m,k in enumerate(self._gate_defs[func_name]['output_args'])}
        sub_func = []
        for cur_func in self._gate_defs[func_name]['function']:
            #Basically iterating over potential ctrl/negctrl etc...
            new_func = {'name': self._evaluate_func_signature(cur_func[1]['name'],input_wildcards),
                        'arguments': [output_wildcards[x] for x in cur_func[1]['arguments']]}
            sub_func.append(new_func)
        return sub_func


    def _eval_func(self, dict_operation):
        if len(dict_operation['name']) == 1:
            if dict_operation['name'][0][0] == 'U':
                return [{'name': [(dict_operation['name'][0][0], dict_operation['name'][0][1])], 'arguments': dict_operation['arguments']}]
            else:
                assert dict_operation['name'][0][0] in self._gate_defs, f"The gate operation {dict_operation['name'][0][0]} is undefined."
                temp_func_list = self._replace_func_with_arguments(*dict_operation['name'][0], dict_operation['arguments'])
                ret_list = []
                for cur_func in temp_func_list:
                    ret_list += self._eval_func(cur_func)
                return ret_list
        else:
            func_sign_list = dict_operation['name']
            found_ind = -1
            new_sign_list = []
            for m, cur_func_sign_arg in enumerate(func_sign_list):
                if isinstance(cur_func_sign_arg, str) and (cur_func_sign_arg == 'ctrl' or cur_func_sign_arg == 'negctrl'):
                    new_sign_list.append(cur_func_sign_arg)
                else:
                    assert isinstance(cur_func_sign_arg, (tuple, list)), f"The argument {cur_func_sign_arg} is invalid in this controlled qubit sequence..."
                    assert found_ind == -1, "Ill-formed control argument for a controlled-gate; there can only be a unitary on one qubit..."
                    found_ind = m
                    new_sign_list.append(cur_func_sign_arg)
            assert found_ind != -1, "A controlled-gate sequence does not have a unitary on one of the qubits."
            cur_func = new_sign_list[found_ind]
            if cur_func[0] == 'U':
                return [dict_operation]
            else:
                assert cur_func[0] in self._gate_defs, f"Function {cur_func[0]} is undefined."
                assert len(self._gate_defs[cur_func[0]]['output_args']) == 1, f"The function {cur_func[0]} is not a single-qubit unitary!"
                temp_func_list = self._replace_func_with_arguments(*cur_func, dict_operation['arguments'])
                func_sign_args = []
                for cur_func in temp_func_list:
                    func_sign_args += self._eval_func(cur_func)
                ret_list = []
                for cur_func in func_sign_args:
                    le_list = [x for x in new_sign_list]
                    le_list[found_ind] = cur_func['name'][0]
                    ret_list.append({'name': le_list, 'arguments': dict_operation['arguments']})
                    
                return ret_list
        

    def _final_compile(self):
        #Flatten the qubit registers into a single qubit array
        qubit_reg_offset_and_size = {}
        cur_offset = 0
        qubit_regs = []
        for cur_q in self._qubits:
            qreg_name, qreg_size = cur_q
            qubit_reg_offset_and_size[qreg_name] = (cur_offset, qreg_size)
            cur_offset += qreg_size
            qubit_regs.append((qreg_name, qreg_size))
        
        #Process operations
        ops = []
        for cur_op in self._operations:
            ops += self._eval_func(cur_op)
        #Check qubit registers are valid
        for cur_op in ops:
            for cur_qubit_arg in cur_op['arguments']:
                if isinstance(cur_qubit_arg, (list, tuple)):
                    assert cur_qubit_arg[1] < qubit_reg_offset_and_size[cur_qubit_arg[0]][1], f"Index of qubit {cur_qubit_arg[0]}[{cur_qubit_arg[1]}] exceeds register size of {qubit_reg_offset_and_size[cur_qubit_arg[0]][1]}."
        #Note that the format of ops is a list of gates where each element is a dictionary with keys:
        #   name - a list of controls with exactly one unitary in the list
        #   arguments - the target qubits upon which to apply the controlled unitary gates
        return ops
    

        

poqasm = ParserOpenQASM('qpe.qasm',[])
a=0