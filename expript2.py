import string as s

ops = None

# TODO Comments, List


I = lambda _:_

class Error(EnvironmentError):
    def __init__(self, msg, origin, expr, name, scope, module):
        self.msg = msg
        self.origin = origin
        self.expr = expr
        self.line = 0
        total = 0
        mod = 0

        for i, line in enumerate(expr.split("\n")):
            if self.origin < total:
                self.line = i
                break
            mod = total
            total += len(line) + 1
            self.expr = line
        else:
            self.line=len(expr.split("\n"))

        self.origin -= mod
        self.name = name
        self.scope = scope
        self.module = module
        self.callbacks = []

    def addCallback(self, callback):
        if self.callbacks and self.callbacks[-1][0] == callback:
            self.callbacks[-1][1] += 1
        else:
            self.callbacks.append([callback, 1])
        return self

    def display(self):
        print('Uncaught '*(self.scope != 'runtime')+{
            'scan': 'scanning Eerror',
            'syntax': 'syntax error',
            'parse': 'parsing error',
            'runtime': 'Unhandled exception'
        }[self.scope],f"on line {self.line}", "in",self.module+":")
        for callback in self.callbacks[::-1]:
            print('  in', callback[0] + ":")
            if callback[1] > 2:
                print(f'  [previous line repeated {callback[1]-1} more times]')
        print(self.expr+"\n"+" "*self.origin+"^")
        print(self.name+":",self.msg)

def stringifyType(x): return str(type(x))[8:-2].split('.')[-1]

def valueOf(context, side, _vars={}, lazy={}): return context[side].value(context["vars"] | _vars, context["lazy"] | lazy, context["expr"], context["module"])

class Node:
    def __init__(self, node_info, node_type, node_origin):
        self.info = node_info
        self.type = node_type
        self.origin = node_origin

        self.is_operation = False
        self.left = None
        self.right = None

    def __repr__(self):
        return 'Node: {0}, Type: {1}, Origin: {2}, Is_op: {3}'.format(self.info, self.type, self.origin, self.is_operation)

    def visualise(self, depth=0, buffer=0):
        print(' ' * buffer * 3 + (' ' * (depth-1) * 3 + '|- ' if depth != 0 else '') + str(self))
        if self.left : self.left .visualise(depth + 1, buffer)
        if self.right: self.right.visualise(depth + 1, buffer)

    def value(self, _vars, lazy_vars,  expr, module):
        def notimplemented(msg):
            raise Error(msg, self.origin, expr, "NotImplementedFeatureError", 'runtime', module)

        if self.is_operation:
            # notimplemented("Evaluating operators is NI.")
            if self.left: # Binary
                # notimplemented("Evaluating binary operators is NI.")
                for priority in ops.binary:
                    if self.info in priority['ops']:
                        operator = priority['ops'][self.info]

                        ignores = None
                        valid = None
                        py = None

                        if "pointer" in operator:
                            ignores = operator["pointer"].ignores
                            valid = operator["pointer"].valid
                            py = operator["pointer"].function
                        else:
                            ignores = operator["ignores"]
                            valid = operator["valid"]
                            py = operator["py"]

                        operands = [None, None] 

                        sides = ["left", "right"]
                        for i, side in enumerate(sides):
                            if side not in ignores:
                                operands[i] = self.__dict__[side].value(_vars, lazy_vars, expr, module)
                                
                        for validType in valid:
                            break
                            isValidTypes = True
                            for i, side in enumerate(sides): 
                                if not (side in ignores or issubclass(type(operands[i]), validType[-i])): 
                                    isValidTypes = False
                            if isValidTypes: break
                        else:
                            raise Error(f"The types {stringifyType(operands[0])}, {stringifyType(operands[1])} are unsupported by the '{self.info}' operator.", self.origin, expr, f"UnsupportedBinaryOperandTypesError", 'runtime', module)
                        
                        return py(*operands, {
                            "self": self,
                            "left": self.left,
                            "right": self.right,
                            "typeLeft": type(operands[0]),
                            "typeRight": type(operands[1]),
                            "vars": _vars,
                            "lazy": lazy_vars,
                            "expr": expr,
                            "module": module
                        })
                else:
                    raise Error(f"Undefined binary operator '{self.info}'.", self.origin, expr, "UndefinedBinaryOperatorError", 'runtime', module)
            else: # Unary
                if self.info in ops.unary:
                    operator = ops.unary[self.info]

                    ignores = None
                    valid = None
                    py = None

                    if "pointer" in operator:
                        ignores = operator["pointer"].ignores
                        valid = operator["pointer"].valid
                        py = operator["pointer"].function
                    else:
                        ignores = operator["ignores"]
                        valid = operator["valid"]
                        py = operator["py"]

                    left = None
                    right = None
                    if "right" not in ignores:
                        right = self.right.value(_vars, lazy_vars, expr, module)
                        for validType in valid:
                            if issubclass(type(right), validType):
                                break
                        else:
                            raise Error("Unsupported unary operand type.\n" + stringifyType(right) + " is unsupported by the '" + self.info + "' operator.", self.right.origin, expr, "UnsupportedUnaryOperandTypeError", 'runtime', module) 
                    
                    try:
                        return py(right, {
                            "self": self,
                            "left": left,
                            "right": self.right,
                            "typeLeft": type(left),
                            "typeRight": type(right),
                            "vars": _vars,
                            "lazy": lazy_vars,
                            "expr": expr,
                            "module": module
                        })
                    except RecursionError as err:
                        raise Error("Too much recursion in unary operator.", self.origin, expr, "UnaryOperatorRecusionError", 'runtime', module)
                else:
                    raise Error(f"Undefined unary operator '{self.info}'.", self.origin, expr, "UndefinedUnaryOperatorError", 'runtime', module)
        else: # Literals
            if self.info in _vars: # Variable
                return _vars[self.info]

            elif self.info in lazy_vars: # Lazy variables
                return lazy_vars[self.info]()

            elif self.info.isnumeric(): # Number
                if self.info == '0': return 0
                return eval((x:=self.info.lstrip("0")))
            elif self.info[:1]=='"': # String
                return self.info[1:-1] # Removes the '' at the start and end of the string
            else: 
                raise Error(f"Undefined variable '{self.info}'.", self.origin, expr, "UndefinedVariableError", 'runtime', module)

def parse(expr, originalExpr, module, buffer=0, depth=0, debug=False):
    def notimplemented(msg, origin, scope="syntax"): raise Error(msg, origin, originalExpr, "NotImplementedFeatureError", scope, module) 
   
    # Step 1 : Tokenise

    if expr == '':
        raise Error("Unexpected EOF.", 0, '', "UnexpectedEOFError", 'scan', module)

    nodes = []

    if debug: # Evaluating:
        print('   ' * depth + 'Evaluating:', expr, 'Buffer:', buffer, "Module:", module)
        print()

    isAtEnd = False
    currentIx = 0
    currentChar = expr[0]

    def advance():
        nonlocal currentChar, currentIx, isAtEnd
        currentIx += 1
        isAtEnd = currentIx >= len(expr)
        currentChar = expr[currentIx] if not isAtEnd else None

    def charType(c):
        if c in ' \n\t':
            return 'wsp'
        if c == '(':
            return 'lpn'
        if c == ')':
            return 'rpn'
        if c == '"':
            return 'qte'
        if c in s.ascii_letters+s.digits+'_':
            return 'val'
        return 'opr'

    def value():
        # nonlocal currentChar, currentIx, isAtEnd, lineN
        # notimplemented("Values are NI.")
        if currentChar == '"':
            # notimplemented("Strings are NI.")
            stringOrigin = currentIx
            string = ''
            advance() # initial "
            shouldEscape = False
            while (shouldEscape or currentChar != '"') and not isAtEnd:
                if currentChar == '\\':
                    shouldEscape = True
                else:
                    string += currentChar
                    shouldEscape = False
                advance()

            if isAtEnd:
                raise Error("Unterimated string.", currentIx, originalExpr, "UnterminatedStringError", "syntax", module)

            advance() # ending "

            nodes.append(Node(f'"{string}"', 'val', buffer+stringOrigin))
        else:
            # notimplemented("Non-string values are NI.")
            current = ''
            currentOrigin = currentIx
            while not isAtEnd and charType(currentChar) == 'val':
                current += currentChar
                advance()

            nodeType = 'val'
            if current in ops.unary:
                nodeType = 'opr'
            else:
                for priority in ops.binary:
                    if current in priority['ops']:
                        nodeType = 'opr'
                        break
            nodes.append(Node(current, nodeType, buffer+currentOrigin))

    def operator():
        nonlocal currentChar, currentIx, isAtEnd

        current = ''
        currentOrigin = currentIx
        while not isAtEnd and charType(currentChar) == 'opr':
            current += currentChar
            advance()

        nodes.append(Node(current, 'opr', buffer+currentOrigin))

    def unmatchedParen(side="right"):
        raise Error(f"Unmatched {side} parentheses.", currentIx, originalExpr, "UnmatchedParenError", "syntax", module)

    def parentheses():
        nonlocal currentChar, currentIx, isAtEnd

        current = ''
        currentOrigin = currentIx

        indent = 0

        advance()

        while not isAtEnd and (currentChar != ')' or indent):
            if currentChar == '(':
                indent += 1
            elif currentChar == ')':
                indent -= 1
            
            current += currentChar
            advance()

        if isAtEnd:
            unmatchedParen("left")

        if currentIx - currentOrigin == 1:
            raise Error("Unexpected ')'. There is nothing in this subexpression.", currentIx, originalExpr, "UnexpectedRightParenError", 'syntax', module)
        
        result, error = parse(expr[currentOrigin+1:currentIx], expr, module=module, buffer=buffer+currentOrigin+1, depth=depth+1, debug=debug)

        advance()

        if error: raise error

        nodes.extend(result)

    def invalidchartype():
        raise Error("Invalid character type. Got " + currentType + ".", currentIx, originalExpr, "InvalidCharacterTypeError", 'scan', module)
    
    while not isAtEnd:
        currentType = charType(currentChar)
        try:
            {
                'qte': value,
                'val': value,
                'opr': operator,
                'lpn': parentheses,
                'rpn': unmatchedParen,
                'wsp': advance,
            }.get(currentType, invalidchartype)()
        except Error as err: return None, err
    
    if debug: # Given:
        print('   ' * depth + "Given:")
        print()
        [node.visualise(buffer=depth) for node in nodes]
        print()

    # Step 2 : AST Generation

    # Step 2.1 : Unary operators and Adjacent values

    currentIx = len(nodes) - 1
    wasChanged = False

    while currentIx > -1:
        currentType = nodes[currentIx].type

        nextType = 'opr'
        if currentIx != 0:
            nextType = nodes[currentIx - 1].type

        if currentType == nextType:
            if currentType == 'val': 
                notimplemented("Default operator between values is NI.", nodes[currentIx].origin, 'parse')
                #raise Error("Expect operator.", nodes[currentIx].origin, originalExpr, "UnexpectedValueError", "parse", module)
            elif currentType == 'opr':
                if currentIx + 1 == len(nodes):
                    raise Error("Expect value.", len(expr)+buffer, originalExpr, "ExpectValueError", 'parse', module)
                else:
                    if nodes[currentIx + 1].type == 'opr':
                        raise Error("Expect value.", nodes[currentIx+1].origin, originalExpr, "UnexpectedOperatorError", 'parse', module)
                    
                    nodes[currentIx].right = nodes[currentIx+1]
                    nodes[currentIx].type = 'val'
                    nodes[currentIx].is_operation = True

                    nodes.pop(currentIx + 1)
                    wasChanged = True
            else:
                raise Error(f'Invalid node type. Got {currentType}.\nAlso somehow this was also the previous node\'s type?', nodes[currentIx].origin, originalExpr, "InvalidCurrentAndPreviousNodeTypeError", "parse", module)
        
        currentIx -= 1

    if debug and wasChanged: # unary:
        print('   ' * depth + "After unary:")
        print()
        [node.visualise(buffer=depth) for node in nodes]
        print()

    if nodes[-1].type == 'opr': 
        return None, Error("Expect value.", len(expr)+buffer, originalExpr, "ExpectValueError", 'parse', module)
    
    # Step 2.2 : Defined binary operators

    for priority in ops.binary:
        direction = "right" if "collapse" in priority['tags'] else "left"
        step = 1 if direction == "left" else -1
        currentIx = len(nodes) - 1 if direction == "right" else 0
        wasChanged = False
        while currentIx < len(nodes) and currentIx >= 0:
            if nodes[currentIx].type == 'opr' and nodes[currentIx].info in priority['ops']:
                nodes[currentIx].left = nodes[currentIx-1]
                nodes[currentIx].right = nodes[currentIx+1]
                nodes[currentIx].type = 'val'
                nodes[currentIx].is_operation = True
                nodes.pop(currentIx-1)
                nodes.pop(currentIx)
                currentIx -= 1
                wasChanged = True
            currentIx += step

        if debug and wasChanged: # Priority:
            print('   ' * depth + "After priority " + priority['name'] + ":")
            print()
            [node.visualise(buffer=depth) for node in nodes]
            print()
        
        # prevNodes = nodes # ???? what was this for ????
    
    # Step 2.3 : Undefined binary operators
    
    while len(nodes) > 2:
        nodes[1].left = nodes[0]
        nodes[1].right = nodes[2]
        nodes[1].type = 'val'
        nodes[1].is_operation = True
        nodes.pop(0)
        nodes.pop(1)

    if len(nodes) == 2:
        return None, Error("2 Nodes left after collapse.", nodes[1].origin, originalExpr, "[ThisWillBeHardToDebugBecauseItMeansThatSomehowTwoNodesWereLeftAfterTheUnknownOperatorsCollapse]Error", 'parse', module)

    if debug: # Result:
        print('   ' * depth + "Result:")
        print()
        [node.visualise(buffer=depth) for node in nodes]
        print()

    return nodes, None

def resolve(source, debug, module="<module>", _operator=None, _vars={}):
    global ops
    if _operator:
        ops = _operator
    
    try: result, error = parse(source, source, debug=debug, module=module)

    except Error as err: return None, err
    if error: return None, error

    try:
        result = result[0].value({
            "true": True,
            "false": False,
            "M": lambda f:f(f)
        }|_vars,{}, source, module=module)
    except Error as err: return None, err
    except RecursionError as err: raise err

    if type(result) == str: return f'"{result}"', None
    if type(result) == type(I): return '<fn>', None

    return result, None
