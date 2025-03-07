from typing import List
import os
import re
import ply.lex
import ply.yacc

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
        'measure' : 'MEASURE'
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
        'ASSIGNOLD'
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


    def t_ID(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
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
        '''statement : ID LBRACKET expressions RBRACKET params SEMICOLON
                      |  ID params SEMICOLON
        '''
        if len(p) == 4:
            p[0] = ('functioncall', {'name':p[1], 'arguments':p[2]})
        else:
            p[0] = ('functioncall', {'name':p[1], 'options':p[3], 'arguments':p[5]})

    def p_functioncall_global(self, p):
        '''statement : ID LBRACKET expressions RBRACKET indexedparams SEMICOLON
                      |  ID indexedparams SEMICOLON
        '''
        if len(p) == 4:
            p[0] = ('functioncall', {'name':p[1], 'arguments':p[2]})
        else:
            p[0] = ('functioncall', {'name':p[1], 'options':p[3], 'arguments':p[5]})
    
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
            pass


ParserOpenQASM('qpe.qasm',[])