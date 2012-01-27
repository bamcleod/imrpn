#!/usr/bin/env python

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
def fetch(name):        return varib[name]
	

# Standard stack ops
#
def dup(x):
    stack.append(x)
    stack.append(x)

def rot(x, y, z):
    stack.append(z)
    stack.append(x)
    stack.append(y)

def drop(x): return None
def swap(x, y):
    stack.append(y)
    stack.append(x)

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

	    result = num(stack.pop())

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

# Colon definition
#
def colon() :
    global input

    name  = input[0]					# Pull the definition out of the input.
    body  = input[1:input.index(";")]
    input = input[len(body)+2:]

    ops[name] = { "op": lambda : inner(body), "signature": [] }


def dotdot() :
    op = ops[input.pop(0)]
    while ( len(stack) and len(stack) >= len(op["signature"]) ): pydef(op)
 
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

	try:
	    (file, extn) = extparse(x)

	    return pyfits.open(file)[extn].data

	except IOError:
	    print "imrpn: cannot read file: " + x
	    exit(1)

    return x


# Run a file as input.  Can be used to import ":" definitions
#
def macro(file): return re.sub(re.compile("#.*\n" ) ,"" ,  open(file).read()).split()
def mcode():     outer(macro(input.pop(0)))


# Import python code and define the new operators.
#
def defopr(name, func, signature) :
    ops[name] = { "op" : func, "signature": signature }

__builtins__.num    = num	# Cast functions must be available in the new module
__builtins__.any    = any	# so stuff them in __builtins__
__builtins__.chr    = chr
__builtins__.defopr = defopr

def pcode(): mod = __import__(input.pop(0)).init()

ops = { 
    "abs":     	{ "op": abs,		"signature": [num] },
    "sin":     	{ "op": numpy.sin,	"signature": [num] },
    "mean":    	{ "op": numpy.mean,	"signature": [num] },
    "median":  	{ "op": numpy.median,	"signature": [num]},
    "+": 	{ "op": operator.add,	"signature": [num, num] },
    "-": 	{ "op": operator.sub,	"signature": [num, num] },
    "*": 	{ "op": operator.mul,	"signature": [num, num] },
    "/": 	{ "op": operator.div,	"signature": [num, num] },
    "**": 	{ "op": operator.pow,	"signature": [num, num] },

    "dup":	{ "op": dup,            "signature": [any] },
    "rot":	{ "op": rot,            "signature": [any, any, any] },
    "drop":	{ "op": drop,           "signature": [any] },
    "swap":	{ "op": swap,           "signature": [any, any] },

    ".":	{ "op": dot,            "signature": [any] },
    "..":       { "op": dotdot,		"signature": [] },

    "!":	{ "op": store,		"signature": [any, chr] },
    "@":	{ "op": fetch,		"signature": [chr] },

    "\\":       { "op":  mcode,		"signature": [] },
    ".py":      { "op": pcode,		"signature": [] },
    ":": 	{ "op": colon,		"signature": [] },
}


# Run a python def off the stack
#
def pydef(dentry):
    operands = []
    for (x, filter) in zip(range(-len(dentry["signature"]), 0, 1)
			 , dentry["signature"]):
	operands.append(filter(stack.pop(x)))

    result = dentry["op"](*operands)

    if ( result != None ) :
	stack.append(result)

# The inner loop - threads the words of a colon def, unlike 4th this does late binding by
# looking up strings in the ops table.  This makes the definition of "inner" and ":"
# simpler, as there is no code pointer and ":" just has to compile a list of strings.  But 
# there are also no flow control words.
#
ip = 0

def inner(code):
    global ip 

    saved = ip

    ip = 0
    while ( ip < len(code) ):
	if code[ip] in ops :		# Lookup operator, convert args and call
	    pydef(ops[code[ip]])
	else:
	    stack.append(code[ip])

	ip = ip + 1

    ip = saved


# The outer loop - consumes input and corrosponds to 4th's evaluate
#
def outer(Input):
    global input

    saved = input
    input = Input

    while ( len(input) ) :
	arg = input.pop(0)

	if arg in ops :		# Lookup operator, convert args and call
	    pydef(ops[arg])
	else:
	    stack.append(arg)

    input = saved


# Main script action
#
input = []
stack = []

start = [".imrpn"] 			# Read in any startup files.

if ( os.getcwd() != os.getenv("HOME") ) :
     start = [os.path.join(os.getenv("HOME"), ".imrpn")] + start

for file in start :
     if ( os.path.exists(file) ) : outer(macro(file))

if not sys.stdin.isatty() :             # If there is something on stdin, try to read it as FITS
    try:
        sys.stdin = os.fdopen(sys.stdin.fileno(), 'rb', 0)
        stack.append(pyfits.open(sys.stdin,mode="readonly")[0].data)
    except IOError:
        sys.stderr.write("Error opening fits from stdin.\n")

outer(sys.argv[1:] + ["..", "."])	# Evaluate the command line & Dump the stack.
