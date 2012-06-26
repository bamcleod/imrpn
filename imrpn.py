#!/usr/bin/env python
#
import os
import sys

import numpy
import pyfits

import re
import operator

import StringIO

class xpa(object):
    def fp():
	pass

    def __init__(self, target, debug=0):
	self.target = target
	self.debug  = debug

	if ( self.debug == 2 ) :
	    self.xpaset = "echo xpaset "
	    self.xpaget = "echo xpaget "
	else :
	    self.xpaset = "xpaset "
	    self.xpaget = "xpaget "

    def set(self, params, buffer=None):
	if ( buffer == None ) :
	    p = " -p"
	else :
	    p = ""

	if ( self.debug == 1 ) :
	    print "xpaset%(0)s %(1)s %(2)s" % { '0':p, '1': self.target, '2':params }
	    if ( buffer != None ) :
		print buffer
	else :
	    fp = os.popen("%(0)s%(1)s %(2)s %(3)s" % { '0':self.xpaset, '1':p, '2':self.target, '3':params }, "wb")

	    if ( buffer == xpa.fp ) :
		return fp

	    if ( buffer != None ) :
		fp.write(buffer)
	    fp.close()

    def get(self, params, buffer=None):
	fp = os.popen("%(0)s%(1)s %(2)s" % { '0':self.xpaget, '1':self.target, '2':params }, "r")

	if ( buffer == xpa.fp ) :
	    return fp

	buffer = fp.read() 
	fp.close()

	return buffer

# Fetch and Store variables
#
varib = {}

def store(value, name): varib[name] = value
def fetch(name): return varib[name]
	

# Standard stack ops
#
def dup(x):
    stak.append(x)
    stak.append(x)

def rot(x, y, z):
    stak.append(z)
    stak.append(x)
    stak.append(y)

def drop(x): return None
def swap(x, y):
    stak.append(y)
    stak.append(x)

def extparse(file, deffile="", defextn=0):
    x = file.split(",")

    if ( x[0] != "" ) : file = x[0]
    else: 		file = deffile

    if ( len(x) == 2 ): extn  = x[1]
    else: 		extn  = defextn

    return (file, extn)

def dot(result):					# Generic output operator
    if ( type(result) == str and result[:4] == "ds9:" ):# Maybe push the result to ds9?
	    (target, frame) = extparse(result[4:], "ds9")

	    result = num(stak.pop())

	    try:
		if ( frame != 0 ) :
		    xpa(target).set("frame " + frame)

		fp = xpa(target).set("fits", xpa.fp)

	    except TypeError:
		print "imrpn cannot talk to ds9: " + target + "," + str(frame)
	   	exit(1)

	    hdu = pyfits.PrimaryHDU(result)
	    try:
		hdu.writeto(fp)
		fp.close()
	    except(ValueError, IOError):
		print "imrpn cannot write to ds9: " + target + "," + str(frame)
	   	exit(1)


	    return None

    if len(numpy.shape(result)) == 0: 			# Just a scalar
	print result

	return None

    if sys.stdout.isatty() : 				# Last chance, write FITS to stdout?
	sys.stderr.write("Refuse to write image to a tty.\n")
	exit(1)

    hdu = pyfits.PrimaryHDU(result)
    hdu.writeto(sys.stdout)

    return None


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

 
def any(x): return     x
def chr(x): return str(x)
def num(x) :
    if ( type(x) == str ) :
	try:
	    return float(x)
	except ValueError:
	    pass

	if ( x[:4] == "ds9:" ):
	    (target, frame) = extparse(x[4:], "ds9")

	    if ( frame != 0 ) :
		xpa(target).set("frame " + frame)

	    x = xpa(target).get("file").strip()

	    if ( x == "" ):
		print "imrpn: cannot get file name from ds9: " + target + "," + str(frame)
		exit(1)

	    if ( x == "stdin" ):
		return pyfits.open(StringIO.StringIO(xpa(target).get("fits", xpa.fp).read())
				, mode="readonly")[0].data

	(file, extn) = extparse(x)

	return pyfits.open(file)[extn].data

	try:
		pass
	except IOError:
	    print "imrpn: cannot read file: " + x
	    exit(1)

    return x


# Run a file as input.  Can be used to import ":" definitions
#
def macro(file):
	fp = open(file)
	data = re.sub(re.compile("#.*\n" ) ,"" ,  fp.read()).split()
	fp.close()
	return data

def mcode():     outer(macro(input.pop(0)))


# Import python code and define the new operators.
#
def defopr(name, func, signature) :
    ops[name] = { "op" : func, "imm": 0, "signature": signature }

__builtins__.num    = num	# Cast functions must be available in the new module
__builtins__.any    = any	# so stuff them in __builtins__
__builtins__.chr    = chr
__builtins__.defopr = defopr

def pcode(): mod = __import__(input.pop(0)).init()


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
    stak.append(code[ip])

def colon():
    global name, body, state 

    name  = input.pop(0)
    body  = []
    state = 1

def semi():
    global state


    text = list(body)

    #for x in text:
    #	print x

    ops[name] = { "op": lambda : inner(list(text)), "imm": 0, "signature": [] }
    state     = 0

# The outer loop - consumes input and corrosponds to 4th's evaluate
#
def outer(Input):
    global input

    saved = input
    input = Input

    while ( len(input) ) :
	word = input.pop(0)

	#print "outer ", word

	if word in ops:		# Lookup word
	    #print "	op"
	    if ( state and not ops[word]["imm"] ):
		body.append(ops[word])
	    else:
		pydef(ops[word])
	else:
	    #print "	lit"
	    if ( state ):
		body.append(ops["(lit)"])
		body.append(word)
	    else:
		stak.append(word)

    input = saved

def xbegin():
    rtrn.append(ip)

def xrepeat():
    body.append(ops["(branch)"])
    body.append(rtrn.pop())

def xwhile():
    body.append(ops["not"])
    body.append(ops["(branch0)"])
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
    body[rtrn.pop()] = len(body)

def xbranch():
    global ip

    ip = code[ip+1]

def xbranch0(x):
    global ip

    ip += 1

    if not x:
    	ip = code[ip]

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

ops = { 
    "abs":     	{ "op": abs,		"imm" : 0, "signature": [num] },
    "sin":     	{ "op": numpy.sin,	"imm" : 0, "signature": [num] },
    "mean":    	{ "op": numpy.mean,	"imm" : 0, "signature": [num] },
    "median":  	{ "op": numpy.median,	"imm" : 0, "signature": [num]},
    "+": 	{ "op": operator.add,	"imm" : 0, "signature": [num, num] },
    "-": 	{ "op": operator.sub,	"imm" : 0, "signature": [num, num] },
    "*": 	{ "op": operator.mul,	"imm" : 0, "signature": [num, num] },
    "/": 	{ "op": operator.div,	"imm" : 0, "signature": [num, num] },
    "**": 	{ "op": operator.pow,	"imm" : 0, "signature": [num, num] },
    "[]": 	{ "op": pyslice,	"imm" : 0, "signature": [num, str] },

    "dup":	{ "op": dup,            "imm" : 0, "signature": [any] },
    "rot":	{ "op": rot,            "imm" : 0, "signature": [any, any, any] },
    "drop":	{ "op": drop,           "imm" : 0, "signature": [any] },
    "swap":	{ "op": swap,           "imm" : 0, "signature": [any, any] },

    ".":	{ "op": dot,            "imm" : 0, "signature": [any] },
    "..":       { "op": dotdot,		"imm" : 1, "signature": [] },

    "!":	{ "op": store,		"imm" : 0, "signature": [any, chr] },
    "@":	{ "op": fetch,		"imm" : 0, "signature": [chr] },

    "\\":       { "op":  mcode,		"imm" : 0, "signature": [] },
    ".py":      { "op": pcode,		"imm" : 0, "signature": [] },
    ":": 	{ "op": colon,		"imm" : 0, "signature": [] },
    ";": 	{ "op": semi,		"imm" : 1, "signature": [] },

    "(lit)": 	{ "op": lit, 		"imm" : 0, "signature": [] },
    "(dotdot)":	{ "op": xdotdot, 	"imm" : 0, "signature": [any] },

    "if":    	{ "op": xif,            "imm" : 1, "signature": [] },
    "then":     { "op": xthen,          "imm" : 1, "signature": [] },
    "else":     { "op": xelse,          "imm" : 1, "signature": [] },
    "begin":    { "op": xbegin,         "imm" : 1, "signature": [] },
    "repeat":   { "op": repeat,         "imm" : 1, "signature": [] },

    "(branch)": { "op": xbranch,        "imm" : 0, "signature": [] },
    "(branch0)":{ "op": xbranch0,       "imm" : 0, "signature": [num] },
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

start = sorted(set([os.path.join(os.getenv("HOME"), ".imrpn"), os.path.join(os.getcwd(), ".imrpn")]))

for file in start :
     if ( os.path.exists(file) ) : outer(macro(file))

if not sys.stdin.isatty() :             # If there is something on stdin, try to read it as FITS
    try:
        sys.stdin = os.fdopen(sys.stdin.fileno(), 'rb', 0)
        stak.append(pyfits.open(sys.stdin,mode="readonly")[0].data)
    except IOError:
        sys.stderr.write("Error opening fits from stdin.\n")

outer(sys.argv[1:] + ["..", "."])	# Evaluate the command line & Dump the stack.

