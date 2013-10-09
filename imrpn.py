#!/usr/bin/env python2.7
#
import os, sys, operator, numpy

sys.path.insert(0, os.path.join(os.getenv("HOME"), ".imrpn"))

import xpa, fits, dotable

Dot = dotable.Dotable

vm = Dot()

Home = os.getenv("HOME")
Conf = os.path.join(Home,  ".imrpn")

vm.varib   = {} 						# Fetch and Store variables
vm.primary = True

								#
def store(value, name): vm.varib[name] = value
def fetch(name): return vm.varib[name]

def drop(x): 	  pass 						# Standard stack ops
def dup(x): 	  vm.stak.extend([Dot(value=x), Dot(value=x)]) 			#
def swap(x, y):   vm.stak.extend([Dot(value=y), Dot(value=x)])
def rot(x, y, z): vm.stak.extend([Dot(value=z), Dot(value=y), Dot(value=x)])

def getshape(x)    : return list(x.shape)
def setshape(x, y) : x.shape = y; return x

def flatten(x)	   : vm.stak.extend(x)

def normal(center, width, shape): return numpy.random.normal(center, width , shape)
def poisson(lam, shape): 	  return numpy.random.poisson(lam, shape)

def extparse(file, deffile="", defextn=0):			# Helper to parse FITS,extn
    x = file.split(",")

    if x[0] != "" : file = x[0]
    else: 	    file = deffile

    if len(x) == 2 :
	y = x[1].split(":")

	if len(y) == 2 :
	    start = None
	    ends  = None

	    if y[0] != "" : start = int(y[0])
	    if y[1] != "" : ends  = int(y[1])

	    extn = slice(start, ends)
	else:
	    extn  = int(x[1])

    else: 	     extn  = defextn

    return (file, extn)

def dot(result):						# Generic output operator
    if type(result) == str and result[:4] == "ds9:" :		# Maybe push the result to ds9?
	    (target, frame) = extparse(result[4:], "ds9", 0)

	    result = num(vm.stak.pop())

	    try:
		if ( frame != 0 ) :
		    xpa.xpa(target).set("frame " + str(frame))

		fp = xpa.xpa(target).set("fits", xpa.xpa.fp)

	    except TypeError:
		print "imrpn cannot talk to ds9: " + target + "," + str(frame)
	   	exit(1)

    	    try:
		hdu = fits.hdu(result, vm.primary)
		vm.primary = False
    	    except fits.Huh:
	    	print "imrpn: cannot convert to FITS: ", result
		exit(1)

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
	print type(result)
	print result.dtype
	print result.shape
	print result
	

    else:
	try:
	    hdu = fits.hdu(result, vm.primary)
	    vm.primary = False
	except fits.Huh:
	    print "imrpn: cannot convert to FITS: ", result
	    exit(1)

	hdu.writeto(sys.stdout)

def xdotdot(op):
    while len(vm.stak) and len(vm.stak) >= len(op["signature"]) : pydef(op)

def dotdot() :
    if ( vm.state ):
	vm.body.append(vm.ops["(lit)"])
	vm.body.append(vm.ops[vm.input.pop(0)])
	vm.body.append(vm.ops["(dotdot)"])
    else:
	vm.stak.append(Dot(value=vm.ops[vm.input.pop(0)]))
	pydef(vm.ops["(dotdot)"])

def python(code) : return eval(code)				# Run python string from the stack.
 
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

	if x[:4] == "ds9:" :
	    (target, frame) = extparse(x[4:], "ds9", 0)

	    if ( frame != 0 ) :
		xpa.xpa(target).set("frame " + str(frame))

	    x = xpa.xpa(target).get("file").strip()

	    if x == "" :
		print "imrpn: cannot get file name from ds9: " + target + "," + str(frame)
		exit(1)

	    if x == "stdin" :
		return fits.open(xpa.xpa(target).get("fits", xpa.xpa.fp))[0].data

	if x == "stdin" :
	    try:
	        x = fits.open(sys.stdin)[0].data
	    except IOError:
	        sys.stderr.write("Error opening fits from stdin.\n")

	else:
	    (file, extn) = extparse(x)

	    try:
		
		x = fits.open(file)

		if type(extn) == int :  x = x[extn].data
		else :
		    x = numpy.dstack([hdu.data for hdu in x[extn]])

		if x == None :
		    print "imrpn: hdu has no data : " + x
		    exit(1)

	    except IOError:
		print "imrpn: cannot read file: " + x
		exit(1)

    return x

def cat(file) : 						# Return the contents of a file.
    fp = open(file);  data = fp.read();  fp.close();

    return data

def macro(file): outer(cat(file).split())			# Run a file as input.

def rpndef(name, func, signature) : 				# Import python code and define the new operators.
    vm.ops[name] = { "op" : func, "imm": 0, "signature": signature }

__builtins__.num    = num					# Cast functions must be available in the new module
__builtins__.any    = any					# so stuff them in __builtins__
__builtins__.rpndef = rpndef

def pcode(file): __import__(file).init()

def pydef(dentry): 						# Run a python def off the stack
    operands = []
    for ( x, cast ) in zip(range(-len(dentry["signature"]), 0, 1)	# Pop each arg from the stack
			 , dentry["signature"]): 			# in reverse order.
	operands.append(cast(vm.stak.pop(x).value))			# Cast the stak value to the expected type.

    result = dentry["op"](*operands)					# Make the call.

    if result != None :
	vm.stak.append(Dot(value=result))

def inner(text): 						# The inner loop - threads the words of a colon def
    ipsave = vm.ip
    cdsave = vm.code

    vm.ip   = 0
    vm.code = text

    while vm.ip < len(vm.code) :
	pydef(vm.code[vm.ip])
	vm.ip += 1

    vm.ip   = ipsave
    vm.code = cdsave

def lit():
    vm.ip += 1
    return vm.code[vm.ip]

def colon():
    vm.name  = vm.input.pop(0)
    vm.body  = []
    vm.state = 1

def semi():
    vm.ops[vm.name] = { "op": lambda text=list(vm.body): inner(text), "imm": 0, "signature": [] }
    vm.state = 0

def comment() :
    while vm.input.pop(0) != ")" : pass

def quote() :
    word = []
    while 1 :
    	tok = vm.input.pop(0)
        if tok[-1] == "\"" :
    	    word.append(tok[0:-1])
    	    break
    	else:
    	    word.append(tok)

    if vm.state :
	vm.body.append(vm.ops["(lit)"])
	vm.body.append(" ".join(word))
    else:
	vm.stak.append(Dot(value=" ".join(word)))

# The outer loop - consumes input and corrosponds to 4th's evaluate
#
def outer(Input):
    saved = vm.input
    vm.input = Input

    while len(vm.input) :
	word = vm.input.pop(0)

	if word in vm.ops:		# Lookup word
	    if ( vm.state and not vm.ops[word]["imm"] ):
		vm.body.append(vm.ops[word])
	    else:
		pydef(vm.ops[word])
	else:
	    if ( vm.state ):
		vm.body.append(vm.ops["(lit)"])
		vm.body.append(word)
	    else:
		vm.stak.append(Dot(value=word))

    vm.input = saved

def xdo():
    vm.body.append(vm.ops[">R"])
    vm.body.append(vm.ops[">R"])
    vm.rtrn.append(len(vm.body))

def xloop():
    limit = vm.rtrn[-2]
    count = vm.rtrn[-1]

    if count < limit:
	count += 1
    else:
	count -= 1

    if count != limit :
    	vm.ip = vm.code[ip]
    else:
	vm.ip += 1
	vm.rtrn[-1] = count

def xbegin():
    vm.rtrn.append(len(vm.body))

def xrepeat():
    vm.body.append(vm.ops["(branch)"])
    vm.body.append(vm.rtrn.pop())

def xwhile():
    vm.body.append(vm.ops["(branch1)"])
    vm.body.append(vm.rtrn.pop())

def xuntil():
    vm.body.append(vm.ops["(branch0)"])
    vm.body.append(vm.rtrn.pop())

def xif():
    vm.body.append(vm.ops["(branch0)"])
    vm.rtrn.append(len(vm.body))
    vm.body.append(0)

def xelse():
    vm.body.append(vm.ops["(branch)"])
    vm.body[vm.rtrn.pop()] = len(vm.body)
    vm.body.append(0)

    vm.rtrn.append(len(vm.body)-1)

def xthen():
    vm.body[vm.rtrn.pop()] = len(vm.body)-1

def xbranch():
    vm.ip = vm.code[vm.ip+1]

def xbranch0(x):
    vm.ip += 1

    if x == 0:
    	vm.ip = vm.code[vm.ip]

def xbranch1(x):
    vm.ip += 1

    if x == 1:
    	vm.ip = vm.code[vm.ip]


def zeros(x): 	    return numpy.zeros(x)
def array(x, type): 
    print x
    if type ==  16 : type = "short"
    if type == -16 : type = "ushort"
    if type ==  32 : type = "int"
    if type ==  64 : type = "long"
    if type == -32 : type = "float"
    if type == -64 : type = "double"

    return numpy.zeros(x, type)


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

def mkmark() : vm.rtrn.append(len(vm.stak))
def mklist() :
	if len(vm.rtrn) == 0 :
		f = 0
	else :
		f = vm.rtrn.pop()

	l = [x.value for x in vm.stak[f:]]

	vm.stak = vm.stak[:f]

	return l

def imstack(im, dim) :
	if dim == 1: return numpy.hstack(im)
	if dim == 2: return numpy.vstack(im)
	if dim == 3: return numpy.dstack(im)

	raise Exception("stack dimension must be 1, 2, or 3")

vm.ops = { 
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

    "abs":     	{ "op": abs,		"imm" : 0, "signature": [num]      },
    "min":     	{ "op": min,		"imm" : 0, "signature": [num, num] },
    "max":     	{ "op": max,		"imm" : 0, "signature": [num, num] },

    "amin":    	{ "op": numpy.amin,	"imm" : 0, "signature": [num, Int] },
    "amax":    	{ "op": numpy.amax,	"imm" : 0, "signature": [num, Int] },
    "sum":    	{ "op": numpy.sum,	"imm" : 0, "signature": [num, Int] },
    "prod":    	{ "op": numpy.prod,	"imm" : 0, "signature": [num, Int] },
    "mean":    	{ "op": numpy.mean,	"imm" : 0, "signature": [num, Int] },
    "median":   { "op": numpy.median,	"imm" : 0, "signature": [num, Int]},
    "std":      { "op": numpy.std,	"imm" : 0, "signature": [num, Int]},
    "var":      { "op": numpy.var,	"imm" : 0, "signature": [num, Int]},

    "normal":  	{ "op": normal, 	"imm" : 0, "signature": [num, num, num]},
    "poisson": 	{ "op": numpy.random.poisson,"imm" : 0, "signature": [num, num]},

    "shape":	{ "op": getshape,	"imm" : 0, "signature": [num] },
    "shape!":	{ "op": setshape,	"imm" : 0, "signature": [num, num] },

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
    ".rc":      { "op": macro,		"imm" : 0, "signature": [str] },
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


    "(":	{ "op": comment,	"imm" : 1, "signature": [] },

    "stack":    { "op": imstack,	"imm" : 0, "signature": [num, int] },
    "[]": 	{ "op": pyslice,	"imm" : 0, "signature": [num, str] },
    "array":    { "op": array,  	"imm" : 0, "signature": [num, str] },
    "zeros":    { "op": zeros,  	"imm" : 0, "signature": [num] },

    "list":	{ "op": list,		"imm" : 0, "signature": [any] },
    "flat":	{ "op": flatten,	"imm" : 0, "signature": [any] },
}

# Main script action
#
vm.name  = ""	# Colon definition pieces.
vm.body  = []
vm.state = 0

vm.ip   = 0	# Colon execution state
vm.code = []

vm.input = []	# Machine state
vm.stak  = []
vm.rtrn  = []

try : 
    file = os.path.join(Home, ".imrpn", "imrpn-extend.py")

    if os.path.exists(file) and os.path.isfile(file) : 
	imports = __import__("imrpn-extend").init()
except:
    pass

start = sorted(set([os.path.join(Home, ".imrpn", "imrpn.rc")
		  , os.path.join(os.getcwd(), ".imrpn")]))

for file in start :
    if os.path.exists(file) and os.path.isfile(file) : macro(file)

if len(sys.argv) == 1:
    print cat(os.path.join(Home, ".imrpn", "README"))
else:
    outer(sys.argv[1:] + ["..", "."])			# Evaluate the command line & Dump the stack.

