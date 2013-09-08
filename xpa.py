import os

debug = 0

class xpa(object):
    def fp():
	pass

    def __init__(self, target):
	self.target = target

	if ( debug == 2 ) :
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

	cmd = "%(0)s%(1)s %(2)s %(3)s" % { '0':self.xpaset, '1':p, '2':self.target, '3':params }

	if ( debug == 1 ) :
	    print cmd, buffer
	else :
	    fp = os.popen(cmd, "wb")

	    if ( buffer == xpa.fp ) :
		return fp

	    if ( buffer != None ) :
		fp.write(buffer)
	    fp.close()

    def get(self, params, buffer=None):
	cmd = "%(0)s%(1)s %(2)s" % { '0':self.xpaget, '1':self.target, '2':params }

	fp = os.popen(cmd, "r")

	if ( buffer == xpa.fp ) :
	    return fp

	buffer = fp.read() 
	fp.close()

	return buffer
