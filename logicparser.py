# Purpose: Contains the Parser class, which is responsible for parsing the tokens generated by the Tokenizer class.
from tokenizer import Tokenizer
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParserError(Exception):
    """Custom exception class for parser errors."""
    pass

class Parser:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.parsed_statements = []

    def parse(self, input_text):
        logger.debug(f"In Parser => input_text: {input_text}")
        try:
            self.tokenizer.tokenize(input_text)
            self.tokenizer.position = 0 
            token = self.tokenizer.peek_next_token()
            logger.debug(f"In Parser => token: {token}")
            if not token:
                return self.parsed_statements
            
            if token['type'] == 'IF':
                self.parsed_statements.append(self.parse_conditional())
            elif token['type'] == 'GOTO':
                # GOTO is standalone, so we process it separately.
                self.parsed_statements.append(self.parse_goto())
            elif token['type'] == 'SET':
                self.parsed_statements.append(self.parse_set())
            elif token['type'] == 'ARRAY':
                self.parsed_statements.append(self.parse_array(token))
            else:
                raise ParserError(f"Unexpected token: {token['type']}")
        except ParserError as e:
            logger.error(f"Parser error: {e}")
            
        logger.info(f"Parser parse: {self.parsed_statements}")
        
        return self.parsed_statements

    def parse_array(self, token):
        # Handle array-specific logic here
        array_name = token['value']  # This contains the array variable name like '@Pizza[size][]'
        
        # Now determine what operation is being performed on the array
        next_token = self.tokenizer.peek_next_token()
        if next_token and next_token['type'] == 'SET':
            self.tokenizer.get_next_token()  # Consume the 'SET' token
            return self.parse_set_array(array_name)
        # Add more cases as needed for other operations like append, remove, etc.
        else:
            raise ParserError(f"Unexpected operation on array: {next_token['type']}")

    def parse_set_array(self, array_name):
        # Here you can handle the logic for setting an array
        # For example, initializing it or setting its elements
        # This will be highly dependent on what your array operations look like
        return {'type': 'set_array', 'name': array_name}
    
    def parse_goto(self):
        # Consume the 'GOTO' token
        goto = self.tokenizer.get_next_token()
        logger.debug(f"parse_goto: {goto}")
        # Next token must be the step number
        step_token_value = goto['value']  # 
        step_token = {'type': 'NUMBER', 'value': step_token_value}
        
        if step_token['type'] != 'NUMBER':
            raise ParserError(f"Expected step number after GOTO, found {step_token['type']}")

        return {'type': 'goto', 'step': str(step_token['value'])}
    
    def parse_conditional_expression(self):
        # Expect a VARIABLE or LITERAL token
        condition_token = self.tokenizer.get_next_token()
        if condition_token['type'] not in ['VARIABLE', 'LITERAL']:
            raise ParserError(f"Unexpected token type {condition_token['type']}, expected VARIABLE or LITERAL")

        # Expect an EQUALS token
        self.tokenizer.expect_token('EQUALS')

        # Expect a value, which could be a literal, another variable, etc.
        value_token = self.tokenizer.get_next_token()
        if value_token['type'] not in ['LITERAL', 'VARIABLE']:
            raise ParserError(f"Unexpected token type {value_token['type']}, expected a value token (LITERAL or VARIABLE)")

        # Return the parsed conditional expression components
        return condition_token, value_token

    def parse_conditional(self):
        self.tokenizer.expect_token('IF')
        self.tokenizer.expect_token('OPEN_PAREN')
        
        # Expect a VARIABLE or LITERAL token for the left-hand side of the comparison
        lhs_token = self.tokenizer.get_next_token()
        if lhs_token['type'] not in ['VARIABLE', 'LITERAL']:
            raise ParserError(f"Unexpected token type {lhs_token['type']}, expected VARIABLE or LITERAL")
        
        # Peek at the next token to check for a comparison operator
        operator_token = self.tokenizer.peek_next_token()

        if operator_token['type'] in ['EQUALS', 'NOTEQUALS']:
            # If there's a comparison operator, consume it and get the right-hand side
            self.tokenizer.get_next_token()  # Consume the operator
            rhs_token = self.tokenizer.get_next_token()
            if rhs_token['type'] not in ['VARIABLE', 'LITERAL', 'VALUE']:
                raise ParserError(f"Unexpected token type {rhs_token['type']}, expected VARIABLE, LITERAL, or VALUE")
            
            condition = {'left': lhs_token['value'], 'operator': operator_token['type'].lower(), 'right': rhs_token['value']}
        else:
            # If there's no comparison operator, it's a standalone condition
            condition = {'value': lhs_token['value']}

        self.tokenizer.expect_token('CLOSE_PAREN')
            
        self.tokenizer.expect_token('THEN')
        then_actions = self.parse_action()
        
        # Handle ELIF clauses
        elif_clauses = []
        while self.tokenizer.peek_next_token() and self.tokenizer.peek_next_token()['type'] == 'ELIF':
            self.tokenizer.get_next_token()  # Consume the 'ELIF'
            self.tokenizer.expect_token('OPEN_PAREN')
            lhs_token = self.tokenizer.get_next_token()
            if lhs_token['type'] not in ['VARIABLE', 'LITERAL']:
                raise ParserError(f"Unexpected token type {lhs_token['type']}, expected VARIABLE or LITERAL")
            elif_condition = self.parse_condition(lhs_token)
            self.tokenizer.expect_token('THEN')
            elif_actions = [self.parse_action()]
            elif_clauses.append({'condition': elif_condition, 'then': elif_actions})
        
        # Handle ELSE clause
        else_actions = None
        if self.tokenizer.peek_next_token() and self.tokenizer.peek_next_token()['type'] == 'ELSE':
            self.tokenizer.expect_token('ELSE')
            else_actions = self.parse_action()

        # Construct the conditional object using the already set 'condition'
        conditional = {
            'type': 'if', 
            'condition': condition, 
            'then': then_actions,
            'elif': elif_clauses,  # Include the ELIF clauses
            'else': else_actions
        }
        logger.debug(f"parse_conditional: {conditional}")
        return conditional
    
    def parse_condition(self, lhs_token):
        # Parse condition based on lhs_token type
        condition = None
        if lhs_token['type'] == 'LITERAL':
            self.tokenizer.expect_token('CLOSE_PAREN')
            condition = {'value': lhs_token['value']}
        else:
            self.tokenizer.expect_token('EQUALS')
            rhs_token = self.tokenizer.get_next_token()
            if rhs_token['type'] not in ['VARIABLE', 'LITERAL', 'VALUE']:
                raise ParserError(f"Unexpected token type {rhs_token['type']}, expected VARIABLE, LITERAL, or VALUE")
            self.tokenizer.expect_token('CLOSE_PAREN')
            condition = {'left': lhs_token['value'], 'operator': 'EQUALS', 'right': rhs_token['value']}
        return condition
    
    def parse_set(self):
        self.tokenizer.expect_token('SET')
        self.tokenizer.expect_token('OPEN_PAREN')

        # Peek at the next token to determine if it's a VARIABLE or ARRAY
        next_token = self.tokenizer.peek_next_token()
        if next_token['type'] == 'VARIABLE':
            var_token = self.tokenizer.expect_token('VARIABLE')
            variable_name = var_token['value']
        elif next_token['type'] == 'ARRAY':
            array_token = self.tokenizer.expect_token('ARRAY')
            variable_name = array_token['value']
        else:
            raise ParserError(f"Unexpected token type {next_token['type']}, expected VARIABLE or ARRAY")

        # Check for an ASSIGNMENT token, indicating an assignment
        if self.tokenizer.peek_next_token()['type'] == 'ASSIGNMENT':
            self.tokenizer.expect_token('ASSIGNMENT')
            value_token = self.tokenizer.expect_token('NUMBER')
            assignment_action = {'type': 'assignment', 'variable': variable_name, 'value': value_token['value']}
            self.tokenizer.expect_token('CLOSE_PAREN')
            return assignment_action
        
        self.tokenizer.expect_token('CLOSE_PAREN')
        then_action = self.parse_action()
        setaction = {'type': 'set', 'variable': variable_name, 'action': then_action}
        #print(f"parse_set: {setaction}")
        return setaction

    def parse_action(self):
        actions = []
        while True:
            if self.tokenizer.peek_next_token() is None:
                break
            
            token = self.tokenizer.get_next_token()
            logger.debug(f"Debugging: parse_action token: {token}")  # Debugging statement
            action = {'type': token['type'].lower(), 'variables': []}
            
            if action['type'] == 'add':
                # Process the value (number or variable) to be added
                next_token = self.tokenizer.peek_next_token()
                if next_token['type'] == 'NUMBER':
                    value_token = self.tokenizer.expect_token('NUMBER')
                    action['value'] = float(value_token['value'])
                elif next_token['type'] == 'VARIABLE':
                    value_token = self.tokenizer.expect_token('VARIABLE')
                    action['value'] = value_token['value']
                else:
                    raise ParserError("Expected NUMBER or VARIABLE token after ADD")

                # Expect the 'TO' token
                self.tokenizer.expect_token('TO')

                # Expect the 'OPEN_PAREN' token
                self.tokenizer.expect_token('OPEN_PAREN')

                # Process the target variable
                variable_token = self.tokenizer.expect_token('VARIABLE')
                action['target_variable'] = variable_token['value']

                # Expect the 'CLOSE_PAREN' token at the end
                self.tokenizer.expect_token('CLOSE_PAREN')
            
            elif action['type'] == 'goto':
                logger.debug(f"parse_action - Found GOTO action: {action}")  # Debugging statement
                step_token_value = token['value']
                step_token = {"type": "NUMBER", "value": step_token_value}
                # # The next token should be the step number for the GOTO action
                # step_token = self.tokenizer.get_next_token()
                logger.debug(f"parse_action - Found step token: {step_token}")  # Debugging statement
                if step_token is None or step_token['type'] != 'NUMBER':
                    raise ParserError("Expected a step number after 'GOTO' keyword")
                action['step'] = step_token['value']
                
                # After getting the step number, expect the 'CLOSE_PAREN' token to close the GOTO action
                if self.tokenizer.peek_next_token()['type'] == 'CLOSE_PAREN':
                    self.tokenizer.get_next_token()  # Consume the 'CLOSE_PAREN' token
            
            elif action['type'] == 'set':
                # Logic for 'set' action
                # Assume the format is SET(variable=value)
                self.tokenizer.expect_token('OPEN_PAREN')
                variable_token = self.tokenizer.expect_token('VARIABLE')
                self.tokenizer.expect_token('ASSIGNMENT')
                value_token = self.tokenizer.get_next_token()  # Can be VARIABLE or NUMBER or LITERAL
                if value_token['type'] not in ['VARIABLE', 'NUMBER', 'LITERAL', 'VALUE']:
                    raise ParserError(f"Expected VARIABLE, NUMBER, LITERAL or 'VALUE' token after '=', found {value_token['type']}")
                self.tokenizer.expect_token('CLOSE_PAREN')
                action['variable'] = variable_token['value']
                action['value'] = value_token['value']
            
            else:
                action['variables'] = []
                while True:
                    if self.tokenizer.peek_next_token() and self.tokenizer.peek_next_token()['type'] == 'OPEN_PAREN':
                        self.tokenizer.expect_token('OPEN_PAREN')
                    if self.tokenizer.peek_next_token() and self.tokenizer.peek_next_token()['type'] in ['VARIABLE', 'NUMBER']:
                        var_token = self.tokenizer.get_next_token()
                        action['variables'].append(var_token['value'])
                        self.tokenizer.expect_token('CLOSE_PAREN')
                    if self.tokenizer.peek_next_token() and self.tokenizer.peek_next_token()['type'] in ['BY', 'TO']:
                        self.tokenizer.get_next_token()
                        continue
                    if not self.tokenizer.peek_next_token() or self.tokenizer.peek_next_token()['type'] in ['CLOSE_PAREN', 'GOTO', 'ADD', 'MULTIPLY', 'SET']:
                        break
                    
            # actions.append(action)
            # logger.debug(f"Action appended: {action}")  # Debugging statement
            if action['type'] not in ['open_paren', 'close_paren']:
                actions.append(action)
                logger.debug(f"Action appended: {action}")
            if self.tokenizer.peek_next_token() and self.tokenizer.peek_next_token()['type'] == 'CLOSE_PAREN':
                self.tokenizer.get_next_token()
            if not self.tokenizer.peek_next_token() or self.tokenizer.peek_next_token()['type'] not in ['ADD', 'MULTIPLY', 'GOTO', 'SET']:
                break
        return actions

#logic_lines="SET (@Dessert.quantity) \nTHEN (MULTIPLY) (@Dessert.quantity) (BY) (@Dessert.price) (ADD) TO (@Price) \n GOTO: 13"logic_lines = 

# logic_line = "IF (@petType==고양이) THEN (GOTO: 5) ELSE (GOTO: 6)"
#logic_line = "IF (#강아지) THEN SET(@petType=dog) ELSE SET(@petType=cat)\nGOTO: 2"
# # #logic_line = "SET (@weight)\nIF (@petType==고양이) THEN (GOTO: 5) ELSE (GOTO: 6)"
# #logic_line = "GOTO: 2"
# logic_lines = logic_line.split("\n")

#logic_line = "IF (#Y) THEN (GOTO: 19) ELIF (@type==dog) THEN (GOTO: 21) ELSE (GOTO: 24)"
# logic_line = "SET(heartworm_prevention)"
#logic_line = "IF (#Y) THEN (GOTO: 11) ELSE (GOTO: 13)"

# logic_line = "IF (#N) THEN IF (@type==dog) THEN (GOTO: 21) ELSE (GOTO: 24)"
logic_line = "IF (#Y) THEN (GOTO: 19) ELIF (@type==dog) THEN (GOTO: 21) ELSE (GOTO: 24)"
# logic_lines = logic_line.split("\n")
# for line in logic_lines:
#     if line.strip() == "":
#         continue
#     print(f"Logic line: {line}")
#     tokenizer = Tokenizer()
#     parser = Parser(tokenizer)
#     parsed_statements = parser.parse(line)
#     parse_info = {
#         "parsed_statements": parsed_statements
#     }
#     print(f"parse_info: {parse_info}")  # Debugging statement