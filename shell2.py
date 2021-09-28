#! /usr/bin/env python3

import expript2, importlib, sys, os

def read_from_file(file_name):
    _file = open(file_name, 'r')
    _read = _file.read()
    _file.close()
    return _read

def getArg(argName, defaultValue=None):
    for arg in sys.argv[::-1]:
        if arg.startswith(argName+"="):
            return arg[len(argName)+1:]
    else:
        return defaultValue

def getMdl(pkgName, errorMsg="There was a problem importing the specified module.\nCheck the spelling and try again."):
    if not pkgName: 
        return
    try:
        return importlib.import_module((spkg:=pkgName.split(":"))[0]).__dict__[spkg[1]]
    except (ImportError, KeyError) as err:
        raise err
        sys.exit(1)


w2b = {"on":True,"off":False}
b2w = {True:"on",False:"off"}
try:
    debug = w2b[getArg('debug', 'off')]
except KeyError:
    print("Invalid argument to 'debug' parameter.")
    sys.exit(1)

epl = getArg('epl', 'std-env:Operators')
src = getArg('src', None)
lib = getArg('lib', None)
ext = getArg('ext', None)

ops = getMdl(epl, "There was a problem importing the requested EPL.\nCheck the spelling and try again.")

if src:
    try: source = read_from_file(src)
    except IOError:
        print("Problem reading from source.\nCheck spelling and try again.")
        sys.exit(1)
    
    result, error = expript2.resolve(source, debug, src, ops)
    if error: error.display(); sys.exit(1)
    else: print(result); sys.exit(0)

history = []
while True: 
    try:
        source = input('> ')
        if source.strip().endswith(":") and source.startswith(":") and source != ":":
            cmd = source[1:-1].lower()
            if cmd[0:2] == 'rs':
                print('Restarting...')
                os.execv(__file__, sys.argv + [f"debug={b2w[debug]}"] + source[4:-1].split(" "))
                sys.exit(0)
            elif cmd == 'q':
                break
            elif cmd == 'db':
                debug = not debug
            else: 
                print("Bad command!")
        elif source.strip() != '':
            result, error = expript2.resolve(source, debug, "<repl>", ops)
            if error: error.display()
            else:
                print(result)
                history.append(source)

    except (KeyboardInterrupt, EOFError): print(); break

print("Bye.")