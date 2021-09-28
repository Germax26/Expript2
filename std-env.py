# ---------------------------------------------------------------- #
# Imports
# ---------------------------------------------------------------- #

from expript2 import Error, valueOf, resolve
from operandTypeTools import *
import sys

# ---------------------------------------------------------------- #
# Constants
# ---------------------------------------------------------------- #

functionType = type(lambda _:_)

# ---------------------------------------------------------------- #
# Custom Classes
# ---------------------------------------------------------------- #

class Assignment:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        if type(value) == Function:
            self.value = self.value.copy()
            self.value.name = self.name

    def __repr__(self): 
        return str(self.value)
    def __eq__(self, other):
        return self.name == other.name and self.value == other.value if type(other) == type(self) else False
    def __ne__(self, other):
        return not self.__eq__(other)
    def toDict(self):
        return {self.name: self.value}

class Turnary:
    def __init__(self, truth, value):
        self.truth = truth
        self.value = value

    def __repr__(self): return str(self.value) if self.value != None else ""

class Function:
    def __init__(self, context):
        self.param = context["left"].info
        self.tree = context["right"]
        self.context = context
        self.name = None

    def copy(self):
        return Function(self.context)

    def __call__(self, context):
        def lazy():
            return valueOf(context, "right")
        return valueOf(self.context | {"tree": self.tree}, "tree", lazy={self.param: lazy})

    def __repr__(self):
        return f"<fn {self.name}>" if self.name else f"<fn of {self.param}>" 

# ---------------------------------------------------------------- #
# Implementation of Operators
# ---------------------------------------------------------------- #

class Operator:
    class Unary:
        class Boolean:
            class Not:
                valid = [object]
                ignores = {}
                @staticmethod
                def function(right, context):
                    return right == False
        class Misc:
            class Eval:
                valid = [str]
                ignores = {}
                @staticmethod
                def function(right, context):
                    result, error = resolve(right, False, _vars=context["vars"], module=context["module"])
                    if error: raise error.addCallback("<string>")
                    return result
            class Comment:
                valid = [str]
                ignores = {}
                @staticmethod
                def function(right, context):
                    return None
    class Binary:
        class Comment:
            class Comment:
                class End(Right(object)):
                    @staticmethod
                    def function(ignored, right, context):
                        return right
        class Primary:
            class Primary:
                class Radix(Left(int, list)):
                    @staticmethod
                    def function(left, ignored, context):
                        if context["typeLeft"] == int:
                            if context["right"].info.isdigit():
                                return eval('{}.{}'.format(left, context["right"].info))
                            raise Error("Illegal postradix. Expect int.", context["right"].origin, context["expr"], "IllegalPostradixError", 'runtime', context["module"])
                        right = valueOf(context, "right")
                        if type(right) != int:
                            raise Error("Illegal index.", context["right"].origin, context["expr"], "IllegalIndexError", 'runtime', context["module"])
                        if right >= len(left) or right < 0:
                            raise Error("List index out of range.", context["right"].origin, context["expr"], "IndexOutOfRangeError", 'runtime', context["module"])
                        return left[right]
                class Call(Left(Function, functionType)):
                    @staticmethod
                    def function(left, ignored, context):
                        try:
                            try:
                                if type(left) == functionType:
                                    return left(valueOf(context, "right"))
                                else:
                                    return left(context)
                            except RecursionError:
                                raise Error("Too much recursion!", context["self"].origin, context["expr"], "RecursionError", 'runtime', context["module"])
                        except Error as err:
                            raise err.addCallback(str(left))
        class Arithmetic:
            class Tertiary:
                class Exponentiation(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        return left ** right
                class Root(Base.Arithmetic): # NI
                    pass 
            class Secondary:
                class Multiplication(Join(Base.Arithmetic, Specify(str, int))):
                    @staticmethod
                    def function(left, right, context):
                        return left * right
                class Division(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        if right == 0:
                            raise Error("Division by 0.", context["self"].origin, context["expr"], "DivisionByZeroError", 'runtime', context["module"])
                        return left / right
                class Modulo(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        if right == 0:
                            raise Error("Division by 0.", context["self"].origin, context["expr"], "DivisionByZeroError", 'runtime')
                        return left % right
            class Primary:
                class Addition(Join(Base.Arithmetic, Double(str))):
                    @staticmethod
                    def function(left, right, context):
                        return left + right
                class Subtraction(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        return left - right
        class Bitwise:
            class And:
                class And(Base.Universal):
                    valid = [[object, object]]
                    ignores = {}
                    @staticmethod
                    def function(left, right, context):
                        return left & right
        class Boolean:
            class Comparision:
                class LessThan(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        return left < right
                class LessThanOrEqualTo(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        return left <= right
                class GreaterThan(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        return left > right
                class GreaterThanOrEqualTo(Base.Arithmetic):
                    @staticmethod
                    def function(left, right, context):
                        return left >= right
                class NotEqualTo(Base.Universal):
                    valid = [[object, object]]
                    ignores = {}
                    @staticmethod
                    def function(left, right, context):
                        return left != right
                class EqualTo(Base.Universal):
                    valid = [[object, object]]
                    ignores = {}
                    @staticmethod
                    def function(left, right, context):
                        return left == right
            class And:
                class And(Left(object)):
                    @staticmethod
                    def function(left, right, context):
                        return valueOf(context, "right") if left else left
            class Or:
                class Or(Left(object)):
                    @staticmethod
                    def function(left, right, context):
                        return left if left else valueOf(context, "right")
        class Tertiary:
            class Tertiary:
                class Then(Left(object)):
                    @staticmethod
                    def function(left, right, context):
                        if left:
                            return Turnary(True, valueOf(context, "right"))
                        return Turnary(False, None)
                class Else(Left(Turnary)):
                    @staticmethod
                    def function(left, right, context):
                        if left.truth:
                            return left.value
                        return valueOf(context, "right")
        class Function:
            class Function:
                class Function(Base.Both):
                    @staticmethod
                    def function(_, __, context):
                        if context["left"].is_operation:
                            raise Error("Illegal paramater for function.", context["left"].origin, context["expr"], "IllegalParamaterError", 'runtime', context["module"])
                        return Function(context)
        class Assignment:
            class Assignment:
                class Assignment(Right(object)):
                    @staticmethod
                    def function(left, right, context):
                        if context["left"].right:
                            raise Error("Invalid assignment target.", context["left"].origin, context["expr"], "InvalidAssignmentTargetError", 'runtime', context["module"])
                        
                        return Assignment(context["left"].info, right)
        class Statement:
            class Statement:
                class Semicolon(Left(object)):
                    @staticmethod
                    def function(left, right, context):
                        return valueOf(context, "right", left.toDict() if isinstance(left, Assignment) else {})

# ---------------------------------------------------------------- #
# Storage of Operators
# ---------------------------------------------------------------- #

class Operators:
    unary = {
        "-": { # Minus
            "ignores": {},
            "valid": [int, float],
            "py": lambda a, context: -a
            },
        "+": { # Add
            "ignores": {},
            "valid": [int, float],
            "py": lambda a, context: +a
            },
        "!": { # Not
            "ignores": {},
            "valid": [object],
            "py": lambda a, context: not a
            },
        "eval": {"pointer": Operator.Unary.Misc.Eval},
        "/*": {"pointer": Operator.Unary.Misc.Comment}
        }
    binary = [
        # Primary
        { # Primary
            'name': 'Primary',
            'tags': [],
            'ops': {
                '.': {"pointer": Operator.Binary.Primary.Primary.Radix},
                '<-': {"pointer": Operator.Binary.Primary.Primary.Call}
            }
            },
        
        # Arithmetic
        { # Tertiary
            'name': 'Exp',
            'tags': [],
            'ops': {
                '**': {"pointer": Operator.Binary.Arithmetic.Tertiary.Exponentiation}
            }
            },
        { # Secondary
            'name': 'Mult, Div, & Mod',
            'tags': [],
            'ops': {
                '*': {"pointer": Operator.Binary.Arithmetic.Secondary.Multiplication},
                '/': {"pointer": Operator.Binary.Arithmetic.Secondary.Division},
                '%': {"pointer": Operator.Binary.Arithmetic.Secondary.Modulo}
            }
            },
        { # Primary
            'name': 'Add & Sub',
            'tags': [],
            'ops': {
                '+': {"pointer": Operator.Binary.Arithmetic.Primary.Addition},
                '-': {"pointer": Operator.Binary.Arithmetic.Primary.Subtraction}
            }
            },
        
        # Bitwise NI

        # Boolean
        { # Comparisions
            'name': 'Comparisions',
            'tags': [],
            'ops': {
                '<' : {"pointer": Operator.Binary.Boolean.Comparision.LessThan},
                '<=' : {"pointer": Operator.Binary.Boolean.Comparision.LessThanOrEqualTo},
                '>' : {"pointer": Operator.Binary.Boolean.Comparision.GreaterThan},
                '>=' : {"pointer": Operator.Binary.Boolean.Comparision.GreaterThanOrEqualTo},
                '!=' : {"pointer": Operator.Binary.Boolean.Comparision.NotEqualTo},
                '==' : {"pointer": Operator.Binary.Boolean.Comparision.EqualTo}
            }
            },
        
        # Conditional Expression
        { # Conditional Expression
            'name': 'Turnary',
            'tags': [],
            'ops': {
                '?': {"pointer": Operator.Binary.Tertiary.Tertiary.Then},
                ':': {"pointer": Operator.Binary.Tertiary.Tertiary.Else}
            }
            },

        {
            'name': 'Lambda',
            'tags': ['collapse'],
            'ops': {
                '=>': {"pointer": Operator.Binary.Function.Function.Function}
            }
            },
        
        # Assignment
        { # Assignment
            'name': 'Assign',
            'tags': ['collapse'],
            'ops': {
                '=': {"pointer": Operator.Binary.Assignment.Assignment.Assignment}
            }
            }, 
        
        # Statement
        { # Semicolon
            'name': 'Semicolon',
            'tags': ['collapse'],
            'ops': {
                ';': {"pointer": Operator.Binary.Statement.Statement.Semicolon},
                '*/': {"pointer": Operator.Binary.Comment.Comment.End}
            }
            }
        ]