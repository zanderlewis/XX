import operator
import sys

class Interpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.imported_libraries = {}
        self.in_function_definition = False
        self.current_function_name = ""
        self.current_function_body = []

    def run_from_file(self, filename):
        with open(filename, 'r') as file:
            code = file.readlines()
            self.run(code)

    def run(self, lines):
        in_python_block = False
        python_code = ""
        code_to_execute = []

        for line in lines:
            stripped_line = line.strip()
             
            if stripped_line == "[plang python]":
                in_python_block = True
                continue   
             
            if stripped_line == "[endplang]" and in_python_block:
                in_python_block = False
                code_to_execute.append(('plang', python_code.strip()))   
                python_code = ""   
                continue

            if in_python_block:
                python_code += line + '\n'   
            else:
                 
                if self.in_function_definition:
                    if stripped_line == 'endf':
                        self.functions[self.current_function_name] = self.current_function_body
                        self.in_function_definition = False
                        self.current_function_name = ""
                        self.current_function_body = []
                    else:
                        self.current_function_body.append(stripped_line)
                else:   
                    code_to_execute.append(('xx', stripped_line))
         
        for code_type, code in code_to_execute:
            if code_type == 'plang':
                self.execute_python_code(code)
            elif code_type == 'xx':
                self.parse_line(code)

    def execute_python_code(self, python_code):
        local_scope = {**self.variables}
        global_scope = {"__builtins__": __builtins__, "print": self.custom_print}

        try:
            exec(python_code, global_scope, local_scope)
             
            self.variables.update(local_scope)
             
            for var in local_scope:
                if callable(local_scope[var]):
                    self.functions[var] = local_scope[var]

        except Exception as e:
            print(f"Error executing embedded Python code: {e}")

    def custom_print(self, *args, **kwargs):
        print(*args, **kwargs)

    def convert_to_python_type(self, value):
        try:
            return int(value)
        except ValueError:
            pass  
        try:
            return float(value)
        except ValueError:
            pass
         
        return value

    def parse_line(self, line):
        if not line or line.startswith('//'):
            return
        if line.startswith('def '):
            self.handle_function_definition(line[4:])
            return 
        if self.in_function_definition:
            if line == 'endf':
                self.in_function_definition = False
                self.functions[self.current_function_name] = self.current_function_body
                self.current_function_name = ""
                self.current_function_body = []
            else:
                self.current_function_body.append(line)
            return
        if line.startswith('var '):
            var_name, var_value = line[4:].split('=')
            self.variables[var_name.strip()] = self.evaluate_expression(var_value.strip())
        elif line.startswith('print(') and line.endswith(')'):
            self.handle_print(line[6:-1])
        elif line.startswith('import '):
            library_name = line[7:].strip()   
            self.handle_import(library_name)
        elif line.startswith('print '):
            value_to_print = line[6:].strip()
            if value_to_print in self.functions:
                 
                print(self.functions[value_to_print]())
            else:
                print(self.evaluate_expression(value_to_print))
        elif '=' in line:
            self.handle_assignment(line)
        elif line.endswith('()'):
             
            func_name = line[:-2].strip()
            if func_name in self.functions:
                self.handle_function_call(func_name)
            else:
                print(f"Undefined function: {func_name}")
         

    def evaluate_expression(self, expression):
        tokens = expression.split()
         
        if len(tokens) == 1:
            token = tokens[0]
            try:
                return int(token)
            except ValueError:
                if token.startswith('"') and token.endswith('"'):
                    return token[1:-1]
                return self.variables.get(token, token)

        while '+' in tokens or '-' in tokens or '*' in tokens or '/' in tokens:
            for i, token in enumerate(tokens):
                if token in ['+', '-', '*', '/']:
                    lhs = self.evaluate_expression(' '.join(tokens[:i]))
                    rhs = self.evaluate_expression(' '.join(tokens[i+1:]))
                    op = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}[token]
                    return op(lhs, rhs)

        raise ValueError(f"Invalid expression: {expression}")

    def handle_print(self, line):  
        value = self.evaluate_expression(line)
        print(value)

    def handle_assignment(self, line):
        var_name, value = line.split('=')
        var_name = var_name.strip()
        value = value.strip()
        self.variables[var_name] = value

    def handle_function_definition(self, line):
        func_name, _, remainder = line.partition(' ')
        self.current_function_name = func_name.strip()
        self.in_function_definition = True
         
        if remainder:
            print(f"Error: Unexpected code after function definition on the same line: {remainder.strip()}")

    def handle_function_call(self, function_name):
        if function_name in self.functions and not self.in_function_definition:
            function_body = self.functions[function_name]
             
            for func_line in function_body:
                self.parse_line(func_line)
        else:
            print(f"Attempt to execute function '{function_name}' during its definition or function is undefined.")

    def handle_import(self, library_name):
        if library_name in self.imported_libraries:
            return

        try:
            with open(f'{library_name}.xxl', 'r') as file:
                library_code = file.readlines()

            current_vars = self.variables.copy()
            current_funcs = self.functions.copy()
            current_in_func_def = self.in_function_definition
            current_func_name = self.current_function_name
            current_func_body = self.current_function_body.copy()
             
            self.run(library_code)

            self.variables = current_vars
            self.functions.update(current_funcs)   
            self.in_function_definition = current_in_func_def
            self.current_function_name = current_func_name
            self.current_function_body = current_func_body

            self.imported_libraries[library_name] = True
        except FileNotFoundError:
            print(f"Library not found: {library_name}")
            sys.exit(1)

 
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python main.py <filename.xx>")
        sys.exit(1)

    filename = sys.argv[1]
    if not filename.endswith('.xx'):
        print("Error: File must have a .xx extension")
        sys.exit(1)

    interpreter = Interpreter()
    interpreter.run_from_file(filename)
