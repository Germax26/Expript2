from typing import TypeVar, Generic

L = TypeVar('L')
R = TypeVar('R')

oppisite = {"left": "right", "right": "left"}

class OperandTypeTools:
    @staticmethod
    def gencls(name, valid): return type(name, (), {'ignores':{}, 'valid': [[]]} | valid)

    @classmethod
    def ignore(cls, side, T): return cls.gencls(f"{side}({[str(t) for t in T]})", {'ignores':{oppisite[side]}, 'valid':[[t] for t in T]})

def Join(R, T): return OperandTypeTools.gencls(f"Join({R}, {T})", {'valid': R.valid + T.valid})    

def Left(*T): return  OperandTypeTools.ignore("left", T)

def Right(*T): return OperandTypeTools.ignore("right", T)

def Both(): return OperandTypeTools.gencls("Both", {'ignores': {"left", "right"}})

def Specify(S, T, name=None): return OperandTypeTools.gencls(name or f"Specify({S}, {T})", {'valid': [[S, T]]})

def Double(T):
    return Specify(T, T, f"Double({T})")

def Square(*T):
    return OperandTypeTools.gencls(f"Square({', '.join([str(t) for t in T])})", {'valid': list(set([(R, S) for R in T for S in T]))})

class Base:
    Arithmetic = Square(int, float)
    Universal = Double(object)
    Both = Both()
