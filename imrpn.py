#!/usr/bin/env python
#
import os, sys, operator, numpy, traceback

sys.path.insert(0, os.path.join(os.getenv("HOME"), ".imrpn"))

import xpa, fits

Home = os.getenv("HOME")
Conf = os.path.join(Home,  ".imrpn")

# Fetch and Store variables
#
varib = {}

def store(value, name): varib[name] = value
def fetch(name): return varib[name]

# Standard stack ops
#
def drop(x): 	  pass
def dup(x): 	  stak.extend([x, x])
def swap(x, y):   stak.extend([y, x])
def rot(x, y, z): stak.extend([z, y, x])

def extparse(file, deffile="", defextn=0):
    x = file.split(",")

    if ( x[0] != "" ) : file = x[0]
    else: 		file = deffile

    if ( len(x) == 2 ): extn  = int(x[1])
    else: 		extn  = defextn

    return (file, extn)

def dot(result):						# Generic output operator
    if ( type(result) == str and result[:4] == "ds9:" ):	# Maybe push the result to ds9?
	    (target, frame) = extparse(result[4:], "ds9", 1)

	    result = num(stak.pop())

	    try:
		if ( frame != 0 ) :
		    xpa.xpa(target, debug=0).set("frame " + str(frame))

		fp = xpa.xpa(target, debug=0).set("fits", xpa.xpa.fp)

	    except TypeError:
	        traceback.print_exc()
		print "imrpn cannot talk to ds9: " + target + "," + str(frame)
	   	exit(1)

	    hdu = fits.PrimaryHDU(result)

	    try:
		hdu.writeto(fp)
		fp.close()
	    except(ValueError, IOError):
		print "imrpn cannot write to ds9: " + target + "," + str(frame), fp
	   	exit(1)

    elif type(result) == list or type(result) == str or len(numpy.shape(result)) == 0:	# Just a scalar
	print result

    elif sys.stdout.isatty() : 					# Last chance, write FITS to stdout?
	sys.stderr.write("Refuse to write image to a tty.\n")
	exit(1)

    else:
	hdu = fits.PrimaryHDU(result)
	hdu.writeto(sys.stdout)

def xdotdot(op):
    while ( len(stak) and len(stak) >= len(op["signature"]) ): pydef(op)

def dotdot() :
    if ( state ):
	body.append(ops["(lit)"])
	body.append(ops[input.pop(0)])
	body.append(ops["(dotdot)"])
    else:
	stak.append(ops[input.pop(0)])
	pydef(ops["(dotdot)"])

def python(code) : return eval(code)
 
def Int(x):
    if type(x) == str and x == "None" :
	return None
	
    return int(x)

def any(x): return     x
def num(x) :
    if type(x) == list :
	return map(num, x)

    if type(x) == str  :
	try:
	    return float(x)
	except ValueError:
	    pass

	if ( x[:4] == "ds9:" ):
	    (target, frame) = extparse(x[4:], "ds9")

	    if ( frame != 0 ) :
		xpa.xpa(target, debug=0).set("frame " + str(frame))

	    x = xpa.xpa(target, debug=0).get("file").strip()

	    if ( x == "" ):
		print "imrpn: cannot get file name from ds9: " + target + "," + str(frame)
		exit(1)

	    if ( x == "stdin" ):
		return fits.open(xpa.xpa(target, debug=0).get("fits", xpa.xpa.fp))[0].data

	if ( x == "stdin" ):
	    try:
	        x = fits.open(sys.stdin)[0].data
	    except IOError:
	        sys.stderr.write("Error opening fits from stdin.\n")

	else:
	    (file, extn) = extparse(x)

	    try:
		x = fits.open(file)[extn].data

		if x == None :
		    print "imrpn: hdu has no data : " + x
		    exit(1)

	    except IOError:
		print "imrpn: cannot read file: " + x
		exit(1)

    return x

# Return the contents of a file.
#
def cat(file) : fp = open(file);  data = fp.read();  fp.close();  return data

# Run a file as input.  Can be used to read ":" definitions
#
def macro(file): return cat(file).split()
def mcode(file): outer(macro(file))

# Import python code and define the new operators.
#
def rpndef(name, func, signature) :
    ops[name] = { "op" : func, "imm": 0, "signature": signature }

__builtins__.num    = num	# Cast functions must be available in the new module
__builtins__.any    = any	# so stuff them in __builtins__
__builtins__.rpndef = rpndef

def pcode(file): __import__(file).init()

# Run a python def off the stack
#
def pydef(dentry):
    operands = []
    for (x, filter) in zip(range(-len(dentry["signature"]), 0, 1)
			 , dentry["signature"]):
	operands.append(filter(stak.pop(x)))

    result = dentry["op"](*operands)

    if ( result != None ) :
	stak.append(result)

# The inner loop - threads the words of a colon def
#
def inner(text):
    global ip 
    global code

    ipsave = ip
    cdsave = code

    ip   = 0
    code = text

    while ( ip < len(code) ):
	pydef(code[ip])
	ip += 1

    ip   = ipsave
    code = cdsave

def lit():
    global ip

    ip += 1
    return code[ip]

def colon():
    global name, body, state 

    name  = input.pop(0)
    body  = []
    state = 1

def semi():
    global state

    text = list(body)

    ops[name] = { "op": lambda : inner(list(text)), "imm": 0, "signature": [] }
    state     = 0

def comment() :
    while input.pop(0) != ")" : pass

def quote() :
    word = []
    while 1 :
    	tok = input.pop(0)
        if tok[-1] == "\"" :
    	    word.append(tok[0:-1])
    	    break
    	else:
    	    word.append(tok)

    if state :
	body.append(ops["(lit)"])
	body.append(" ".join(word))
    else:
	stak.append(" ".join(word))

# The outer loop - consumes input and corrosponds to 4th's evaluate
#
def outer(Input):
    global input

    saved = input
    input = Input

    while ( len(input) ) :
	word = input.pop(0)

	if word in ops:		# Lookup word
	    if ( state and not ops[word]["imm"] ):
		body.append(ops[word])
	    else:
		pydef(ops[word])
	else:
	    if ( state ):
		body.append(ops["(lit)"])
		body.append(word)
	    else:
		stak.append(word)

    input = saved

def xdo():
    body.append(ops[">R"])
    body.append(ops[">R"])
    rtrn.append(len(body))

def xloop():
    global ip

    limit = rtrn[-2]
    count = rtrn[-1]

    if count < limit:
	count += 1
    else:
	count -= 1

    if ( count != limit ) :
    	ip = code[ip]
    else:
	ip += 1
	rtrn[-1] = count

def xbegin():
    rtrn.append(len(body))

def xrepeat():
    body.append(ops["(branch)"])
    body.append(rtrn.pop())

def xwhile():
    body.append(ops["(branch1)"])
    body.append(rtrn.pop())

def xuntil():
    body.append(ops["(branch0)"])
    body.append(rtrn.pop())

def xif():
    body.append(ops["(branch0)"])
    rtrn.append(len(body))
    body.append(0)

def xelse():
    body.append(ops["(branch)"])
    body[rtrn.pop()] = len(body)
    body.append(0)

    rtrn.append(len(body)-1)

def xthen():
    body[rtrn.pop()] = len(body)-1

def xbranch():
    global ip

    ip = code[ip+1]

def xbranch0(x):
    global ip

    ip += 1

    if x == 0:
    	ip = code[ip]


def xbranch1(x):
    global ip

    ip += 1

    if x == 1:
    	ip = code[ip]


def array(x):
    dims = []
    for i in range(int(x)):
        dims.append(int(stak.pop()))

    return numpy.zeros(dims)

def pyslice(data, s):
    sx = []
    for dim in s.split(",") :
	ss = []
	for x in dim.split(":") :
	    if x == '':
		ss.append(None)
	    else :
		ss.append(int(x))

	sx.append(slice(*ss))

    return data[sx]

def mkmark() : rtrn.append(len(stak))
def mklist() :
	global stak

	if len(rtrn) == 0 :
		f = 0
	else :
		f = rtrn.pop()


	l = list(stak[f:])

	stak = stak[:f]

	return l

def imstack(im, dim) :
	if dim == 1: return numpy.hstack(im)
	if dim == 2: return numpy.vstack(im)
	if dim == 3: return numpy.dstack(im)

	raise Exception("stack dimension must be 1, 2, or 3")

ops = { 
    "abs":     	{ "op": abs,		"imm" : 0, "signature": [num] },
    "min":     	{ "op": min,		"imm" : 0, "signature": [num] },
    "max":     	{ "op": max,		"imm" : 0, "signature": [num] },
    "sin":     	{ "op": numpy.sin,	"imm" : 0, "signature": [num] },
    "cos":     	{ "op": numpy.cos,	"imm" : 0, "signature": [num] },
    "tan":     	{ "op": numpy.tan,	"imm" : 0, "signature": [num] },
    "arctan":  	{ "op": numpy.arctan,	"imm" : 0, "signature": [num] },
    "arctan2":  { "op": numpy.arctan2,	"imm" : 0, "signature": [num, num] },
    "atan":  	{ "op": numpy.arctan,	"imm" : 0, "signature": [num] },
    "atan2":    { "op": numpy.arctan2,	"imm" : 0, "signature": [num, num] },
    "sqrt":    	{ "op": numpy.sqrt,	"imm" : 0, "signature": [num] },
    "log":    	{ "op": numpy.log,	"imm" : 0, "signature": [num] },
    "log10":   	{ "op": numpy.log10,	"imm" : 0, "signature": [num] },
    "exp":    	{ "op": numpy.exp,	"imm" : 0, "signature": [num] },

    "sum":    	{ "op": numpy.sum,	"imm" : 0, "signature": [num, Int] },
    "prod":    	{ "op": numpy.prod,	"imm" : 0, "signature": [num, Int] },
    "mean":    	{ "op": numpy.mean,	"imm" : 0, "signature": [num, Int] },
    "median":   { "op": numpy.median,	"imm" : 0, "signature": [num, Int]},
    "std":      { "op": numpy.std,	"imm" : 0, "signature": [num, Int]},
    "var":      { "op": numpy.var,	"imm" : 0, "signature": [num, Int]},
    "normal":  	{ "op": numpy.random.normal,"imm" : 0, "signature": [num, num]},

    "+": 	{ "op": operator.add,	"imm" : 0, "signature": [num, num] },
    "-": 	{ "op": operator.sub,	"imm" : 0, "signature": [num, num] },
    "*": 	{ "op": operator.mul,	"imm" : 0, "signature": [num, num] },
    "/": 	{ "op": operator.div,	"imm" : 0, "signature": [num, num] },
    "**": 	{ "op": operator.pow,	"imm" : 0, "signature": [num, num] },
    "^": 	{ "op": operator.pow,	"imm" : 0, "signature": [num, num] },

    "and": 	{ "op": operator.and_,	"imm" : 0, "signature": [num, num] },
    "or": 	{ "op": operator.or_,	"imm" : 0, "signature": [num, num] },
    "not": 	{ "op": operator.not_,	"imm" : 0, "signature": [num] },

    "dup":	{ "op": dup,            "imm" : 0, "signature": [any] },
    "rot":	{ "op": rot,            "imm" : 0, "signature": [any, any, any] },
    "drop":	{ "op": drop,           "imm" : 0, "signature": [any] },
    "swap":	{ "op": swap,           "imm" : 0, "signature": [any, any] },

    ".":	{ "op": dot,            "imm" : 0, "signature": [any] },
    "..":       { "op": dotdot,		"imm" : 1, "signature": [] },

    "!":	{ "op": store,		"imm" : 0, "signature": [any, str] },
    "@":	{ "op": fetch,		"imm" : 0, "signature": [str] },

    ".py":      { "op": pcode,		"imm" : 0, "signature": [str] },
    ".rc":      { "op": mcode,		"imm" : 0, "signature": [str] },
    "python":   { "op": python,		"imm" : 0, "signature": [str] },
    ":": 	{ "op": colon,		"imm" : 0, "signature": [] },
    ";": 	{ "op": semi,		"imm" : 1, "signature": [] },
    "\"": 	{ "op": quote,		"imm" : 1, "signature": [] },

    "(lit)": 	{ "op": lit, 		"imm" : 0, "signature": [] },
    "(dotdot)":	{ "op": xdotdot, 	"imm" : 0, "signature": [any] },

    "if":    	{ "op": xif,            "imm" : 1, "signature": [] },
    "then":     { "op": xthen,          "imm" : 1, "signature": [] },
    "else":     { "op": xelse,          "imm" : 1, "signature": [] },
    "begin":    { "op": xbegin,         "imm" : 1, "signature": [] },
    "repeat":   { "op": xrepeat,        "imm" : 1, "signature": [] },
    "while":    { "op": xwhile,         "imm" : 1, "signature": [] },
    "until":    { "op": xuntil,         "imm" : 1, "signature": [] },

    "(branch)": { "op": xbranch,        "imm" : 0, "signature": [] },
    "(branch0)":{ "op": xbranch0,       "imm" : 0, "signature": [num] },
    "(branch1)":{ "op": xbranch1,       "imm" : 0, "signature": [num] },
    "[":	{ "op": mkmark,		"imm" : 0, "signature": [] },
    "]":	{ "op": mklist,		"imm" : 0, "signature": [] },

    "stack":    { "op": imstack,	"imm" : 0, "signature": [num, int] },
    "[]": 	{ "op": pyslice,	"imm" : 0, "signature": [num, str] },
    "array":    { "op": array,  	"imm" : 0, "signature": [num] },
}

# Main script action
#
name  = ""	# Colon definition pieces.
body  = []
state = 0

ip   = 0	# Colon execution state
code = []

input = []	# Machine state
stak  = []
rtrn  = []

try : 
    file = os.path.join(Home, ".imrpn", "imrpn-extend.py")

    if os.path.exists(file) and os.path.isfile(file) : 
	imports = __import__("imrpn-extend").init()
except:
    pass

start = sorted(set([os.path.join(Home, ".imrpn", "imrpn.rc")
		  , os.path.join(os.getcwd(), "imrpn.rc")
		  , os.path.join(os.getcwd(), ".imrpn")]))

for file in start :
    if os.path.exists(file) and os.path.isfile(file) : mcode(file)

outer(sys.argv[1:] + ["..", "."])	# Evaluate the command line & Dump the stack.

