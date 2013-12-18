#!/usr/bin/env python2.7
#
import os, sys, operator, numpy

sys.path.insert(0, os.path.join(os.getenv("HOME"), ".imrpn"))
sys.path.insert(0, ".imrpn")
sys.path.insert(0, ".")

import xpa, fits, dotable

Dot = dotable.Dotable

vm = Dot()

Home = os.getenv("HOME")
Conf = os.path.join(Home,  ".imrpn")

vm.varib   = {} 						# Fetch and Store variables
vm.primary = True

								#
def store(value, name):
    vm.varib[name] = value

def fetch(name):
    if type(name) == list :
	data = num(vm.stak.pop().value)

	return data[name]

    return vm.varib[name]

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
	    extn  = x[1]

    else: 	     extn  = defextn

    return (file, extn)

def dot(result):						# Generic output operator
    if type(result) == str and result[:4] == "ds9:" :		# Maybe push the result to ds9?
	    (target, frame) = extparse(result[4:], "ds9", 0)

	    result = num(vm.stak.pop()).value

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

def Str(x): return  ( x, None )
def Any(x): return  ( x, None )
def Num(x) :
    hdu = None

    if type(x) == list :
	return ( map(Num, x), None )

    if type(x) == str  :
	try:
	    return ( int(x), None )
	except ValueError:
	    pass

	try:
	    return ( float(x), None )
	except ValueError:
	    pass

	if x[:4] == "ds9:" :
	    (target, frame) = extparse(x[4:], "ds9", 0)

	    if ( frame != 0 ) :
		xpa.xpa(target).set("frame " + frame)

	    x = xpa.xpa(target).get("file").strip()

	    if x == "" :
		print "imrpn: cannot get file name from ds9: " + target + "," + str(frame)
		exit(1)

	    if x == "stdin" :
	        hdu = fits.open(xpa.xpa(target).get("fits", xpa.xpa.fp))[0]
		return ( hdu.data, hdu )

	if x == "stdin" :
	    try:
	        hdu = fits.open(sys.stdin)[0]
		x   = hdu.data
	    except IOError:
	        sys.stderr.write("Error opening fits from stdin.\n")
		exit(1)

	else:
	    (file, extn) = extparse(x)

	    try:
		x = fits.open(file)

		if type(extn) == list or type(extn) == slice:
		    x = numpy.dstack([hdu.data for hdu in x[extn]])
		else :
		    found = 0

		    try:
			x = x[int(extn)].data
		    except:
			for hdu in x[1:]:
			    try:
				if hdu.EXTNAME == extn:
				    found = 1
				    break
			    except IndexError:
				pass
			
			if not found :
			    print "imrpn: hdu has no EXTNAME : " + file + " " + extn
			    exit(1)
			else :
			    x = hdu.data

		if x == None :
		    print "imrpn: hdu has no data : " + file + " " + str(extn)
		    exit(1)

	    except IOError:
		print "imrpn: cannot read file: " + x
		exit(1)

    return ( x, hdu )

def cat(file) : 						# Return the contents of a file.
    fp = open(file);  data = fp.read();  fp.close();

    return data

def macro(file): outer(cat(file).split())			# Run a file as input.

def rpndef(name, func, signature) : 				# Import python code and define the new operators.
    vm.ops[name] = { "op" : func, "imm": 0, "signature": signature }

__builtins__.Num    = Num					# Cast functions must be available in the new module
__builtins__.Any    = Any					# so stuff them in __builtins__
__builtins__.Str    = Str
__builtins__.Int    = Int
__builtins__.rpndef = rpndef

def pcode(file): 
    __import__(file).init()

def pydef(dentry): 						# Run a python def off the stack
    operands = []
    header   = None

    for ( x, cast ) in zip(range(-len(dentry["signature"]), 0, 1)	# Pop each arg from the stack
			 , dentry["signature"]): 			# in reverse order.

	top = vm.stak.pop(x)

	( oper, head )  = cast(top.value)

	operands.append(oper)					# Cast the stak value to the expected type.

	if header == None : 					# The first operand that has an associated header labels the result.
	    if head == None :
		header = None ; # top.header
	    else :
	    	header = head

    result = dentry["op"](*operands)					# Make the call.

    if result != None :
	vm.stak.append(Dot(value=result, header=header))

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
    try:
	if   int(type) ==  16 : type = "int16"
	elif int(type) == -16 : type = "uint16"
	elif int(type) ==  32 : type = "int32"
	elif int(type) ==  64 : type = "int64"
	elif int(type) == -32 : type = "float32"
	elif int(type) == -64 : type = "float64"
    except:
	pass

    if hasattr(x, "astype") and callable(getattr(x, "astype")):
	return x.astype(type)
    else:
	return numpy.zeros(x, type)


def pyslice(data, s):
    sx = []
    for dim in s :
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
    "sin":     	{ "op": numpy.sin,	"imm" : 0, "signature": [Num] },
    "cos":     	{ "op": numpy.cos,	"imm" : 0, "signature": [Num] },
    "tan":     	{ "op": numpy.tan,	"imm" : 0, "signature": [Num] },
    "arctan":  	{ "op": numpy.arctan,	"imm" : 0, "signature": [Num] },
    "arctan2":  { "op": numpy.arctan2,	"imm" : 0, "signature": [Num, Num] },
    "atan":  	{ "op": numpy.arctan,	"imm" : 0, "signature": [Num] },
    "atan2":    { "op": numpy.arctan2,	"imm" : 0, "signature": [Num, Num] },
    "sqrt":    	{ "op": numpy.sqrt,	"imm" : 0, "signature": [Num] },
    "log":    	{ "op": numpy.log,	"imm" : 0, "signature": [Num] },
    "log10":   	{ "op": numpy.log10,	"imm" : 0, "signature": [Num] },
    "exp":    	{ "op": numpy.exp,	"imm" : 0, "signature": [Num] },

    "abs":     	{ "op": abs,		"imm" : 0, "signature": [Num]      },
    "min":     	{ "op": min,		"imm" : 0, "signature": [Num, Num] },
    "max":     	{ "op": max,		"imm" : 0, "signature": [Num, Num] },

    "amin":    	{ "op": numpy.amin,	"imm" : 0, "signature": [Num, Int] },
    "amax":    	{ "op": numpy.amax,	"imm" : 0, "signature": [Num, Int] },
    "sum":    	{ "op": numpy.sum,	"imm" : 0, "signature": [Num, Int] },
    "prod":    	{ "op": numpy.prod,	"imm" : 0, "signature": [Num, Int] },
    "mean":    	{ "op": numpy.mean,	"imm" : 0, "signature": [Num, Int] },
    "median":   { "op": numpy.median,	"imm" : 0, "signature": [Num, Int]},
    "std":      { "op": numpy.std,	"imm" : 0, "signature": [Num, Int]},
    "var":      { "op": numpy.var,	"imm" : 0, "signature": [Num, Int]},

    "normal":  	{ "op": normal, 	"imm" : 0, "signature": [Num, Num, Num]},
    "poisson": 	{ "op": numpy.random.poisson,"imm" : 0, "signature": [Num, Num]},

    "shape":	{ "op": getshape,	"imm" : 0, "signature": [Num] },
    "shape!":	{ "op": setshape,	"imm" : 0, "signature": [Num, Num] },

    "+": 	{ "op": operator.add,	"imm" : 0, "signature": [Num, Num] },
    "-": 	{ "op": operator.sub,	"imm" : 0, "signature": [Num, Num] },
    "*": 	{ "op": operator.mul,	"imm" : 0, "signature": [Num, Num] },
    "/": 	{ "op": operator.div,	"imm" : 0, "signature": [Num, Num] },
    "**": 	{ "op": operator.pow,	"imm" : 0, "signature": [Num, Num] },
    "^": 	{ "op": operator.pow,	"imm" : 0, "signature": [Num, Num] },

    "and": 	{ "op": operator.and_,	"imm" : 0, "signature": [Num, Num] },
    "or": 	{ "op": operator.or_,	"imm" : 0, "signature": [Num, Num] },
    "not": 	{ "op": operator.not_,	"imm" : 0, "signature": [Num] },

    "dup":	{ "op": dup,            "imm" : 0, "signature": [Any] },
    "rot":	{ "op": rot,            "imm" : 0, "signature": [Any, Any, Any] },
    "drop":	{ "op": drop,           "imm" : 0, "signature": [Any] },
    "swap":	{ "op": swap,           "imm" : 0, "signature": [Any, Any] },

    ".":	{ "op": dot,            "imm" : 0, "signature": [Any] },
    "..":       { "op": dotdot,		"imm" : 1, "signature": [] },

    "!":	{ "op": store,		"imm" : 0, "signature": [Any, Str] },
    "@":	{ "op": fetch,		"imm" : 0, "signature": [Str] },

    ".py":      { "op": pcode,		"imm" : 0, "signature": [Str] },
    ".rc":      { "op": macro,		"imm" : 0, "signature": [Str] },
    "python":   { "op": python,		"imm" : 0, "signature": [Str] },
    ":": 	{ "op": colon,		"imm" : 0, "signature": [] },
    ";": 	{ "op": semi,		"imm" : 1, "signature": [] },
    "\"": 	{ "op": quote,		"imm" : 1, "signature": [] },

    "(lit)": 	{ "op": lit, 		"imm" : 0, "signature": [] },
    "(dotdot)":	{ "op": xdotdot, 	"imm" : 0, "signature": [Any] },

    "if":    	{ "op": xif,            "imm" : 1, "signature": [] },
    "then":     { "op": xthen,          "imm" : 1, "signature": [] },
    "else":     { "op": xelse,          "imm" : 1, "signature": [] },
    "begin":    { "op": xbegin,         "imm" : 1, "signature": [] },
    "repeat":   { "op": xrepeat,        "imm" : 1, "signature": [] },
    "while":    { "op": xwhile,         "imm" : 1, "signature": [] },
    "until":    { "op": xuntil,         "imm" : 1, "signature": [] },

    "(branch)": { "op": xbranch,        "imm" : 0, "signature": [] },
    "(branch0)":{ "op": xbranch0,       "imm" : 0, "signature": [Num] },
    "(branch1)":{ "op": xbranch1,       "imm" : 0, "signature": [Num] },
    "[":	{ "op": mkmark,		"imm" : 0, "signature": [] },
    "]":	{ "op": mklist,		"imm" : 0, "signature": [] },


    "(":	{ "op": comment,	"imm" : 1, "signature": [] },

    "stack":    { "op": imstack,	"imm" : 0, "signature": [Num, Int] },
    "[]": 	{ "op": pyslice,	"imm" : 0, "signature": [Num, Str] },
    "array":    { "op": array,  	"imm" : 0, "signature": [Num, Any] },
    "zeros":    { "op": zeros,  	"imm" : 0, "signature": [Num] },

    "list":	{ "op": list,		"imm" : 0, "signature": [Any] },
    "flat":	{ "op": flatten,	"imm" : 0, "signature": [Any] },
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

