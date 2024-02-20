# Import libraries
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

            # Check for the start of a Python block
            if stripped_line == "[plang python]":
                in_python_block = True
                continue  # Skip the line with the start tag

            # Check for the end of a Python block
            if stripped_line == "[endplang]" and in_python_block:
                in_python_block = False
                code_to_execute.append(('plang', python_code.strip()))  # Queue Python block for execution
                python_code = ""  # Reset the Python code block
                continue

            if in_python_block:
                python_code += line + '\n'  # Collect the Python block lines
            else:
                # Handle function definitions within the .xx script
                if self.in_function_definition:
                    if stripped_line == 'endf':
                        self.functions[self.current_function_name] = self.current_function_body
                        self.in_function_definition = False
                        self.current_function_name = ""
                        self.current_function_body = []
                    else:
                        self.current_function_body.append(stripped_line)
                else:
                    # Queue .xx line for execution
                    code_to_execute.append(('xx', stripped_line))

        # Execute collected code blocks
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

            # Update the interpreter's variables with any changes made by the Python code
            self.variables.update(local_scope)

            # Now, store any functions defined in the Python block
            for var in local_scope:
                if callable(local_scope[var]):
                    self.functions[var] = local_scope[var]

        except Exception as e:
            print(f"Error executing embedded Python code: {e}")




    def custom_print(self, *args, **kwargs):
        # This is a custom print function that can be used to link the print
        # output from the Python code to the .xx language's output system.
        # For now, it simply prints to the console.
        print(*args, **kwargs)

    def convert_to_python_type(self, value):
        # Try to convert the value to an integer
        try:
            return int(value)
        except ValueError:
            pass
        # Try to convert the value to a float
        try:
            return float(value)
        except ValueError:
            pass
        # Return the value as is if it's not a number
        return value


    def parse_line(self, line):
        if not line or line.startswith('//'):
            # It's a comment or a blank line; ignore it.
            return
        if line.startswith('var '):
            # Handle variable assignment
            var_name, var_value = line[4:].split('=')
            self.variables[var_name.strip()] = self.evaluate_expression(var_value.strip())
        elif line.startswith('print(') and line.endswith(')'):
            # Handle print statement with parentheses
            self.handle_print(line[6:-1])
        elif line.startswith('print '):
            # Handle print statement without parentheses
            value_to_print = line[6:].strip()
            if value_to_print in self.functions:
                # If it's a function, call it and print the return value
                print(self.functions[value_to_print]())
            else:
                # Otherwise, evaluate the expression and print
                print(self.evaluate_expression(value_to_print))
        elif '=' in line:
            # Handle variable assignment
            self.handle_assignment(line)
        elif line.startswith('def '):
            # Handle function definition
            self.handle_function_definition(line[4:])
        elif line.startswith('endf'):
            # End of function definition
            return
        elif line.endswith('()'):
            # Handle function call
            func_name = line[:-2].strip()
            if func_name in self.functions:
                # If it's a Python function defined in plang, call it
                self.functions[func_name]()
            else:
                # If it's a .xx function, handle the call
                self.handle_function_call(func_name)
        elif line.startswith('import '):
            # Handle import statement
            self.handle_import(line[7:])
        else:
            # None of the patterns matched; it's a syntax error.
            print(f"Syntax error in line: '{line}'")

    def evaluate_expression(self, expression):
        # This is a simple recursive parser for mathematical expressions
        tokens = expression.split()

        # Base case: if there's only one token, it must be a number, a string, or a variable
        if len(tokens) == 1:
            token = tokens[0]
            try:
                # Try to return it as a number
                return int(token)
            except ValueError:
                # Check if it's a string literal
                if token.startswith('"') and token.endswith('"'):
                    return token[1:-1]  # Remove the quotes and return the string
                # If it's not a number or string, it must be a variable
                return self.variables.get(token, token)

        # Recursive case: find the operator with the lowest precedence and split the expression there
        # For simplicity, we're assuming '+' and '-' have the same precedence, and '*' and '/' have the same (higher) precedence
        while '+' in tokens or '-' in tokens or '*' in tokens or '/' in tokens:
            # This is a naive implementation, a real interpreter should handle operator precedence and parentheses properly
            for i, token in enumerate(tokens):
                if token in ['+', '-', '*', '/']:
                    # We found an operator, now we evaluate the left and right side
                    lhs = self.evaluate_expression(' '.join(tokens[:i]))
                    rhs = self.evaluate_expression(' '.join(tokens[i+1:]))
                    op = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}[token]
                    return op(lhs, rhs)

        # If we didn't find any operators, there's a syntax error
        raise ValueError(f"Invalid expression: {expression}")


    def handle_print(self, line):
        # Evaluate the expression and print the result
        value = self.evaluate_expression(line)
        print(value)

    def handle_assignment(self, line):
        var_name, value = line.split('=')
        var_name = var_name.strip()
        value = value.strip()
        self.variables[var_name] = value

    def handle_function_definition(self, line):
        # Start of function definition
        func_name, _, remainder = line.partition(' ')  # Assuming 'def func_name' syntax
        self.current_function_name = func_name.strip()
        self.in_function_definition = True
        if remainder:
            # If there's more to the line, add it to the function body
            self.current_function_body.append(remainder.strip())

    def handle_function_call(self, function_name):
        # Call a defined function
        if function_name in self.functions:
            # Retrieve the function body
            function_body = self.functions[function_name]
            # Execute each line of the function body
            for func_line in function_body:
                self.parse_line(func_line)
        else:
            print(f"Undefined function: {function_name}")

    def handle_import(self, library_name):
        if library_name in self.imported_libraries:
            # Library already imported; nothing to do
            return
        try:
            # Attempt to open the library file
            with open(f'{library_name}', 'r') as file:
                library_code = file.readlines()

            # Run the library code as if it were part of the main program
            # This should populate self.functions with any functions defined in the library
            self.run(library_code)

            # Mark this library as imported
            self.imported_libraries[library_name] = True
        except FileNotFoundError:
            print(f"Library not found: {library_name}")
            sys.exit(1)


# Example usage
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