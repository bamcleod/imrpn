import numpy, shutil, shlex, sys
import builtins as __builtin__

def swapped() : 
    return numpy.ndarray((1),dtype='i2', buffer=str(chr(1) + chr(0)))[0] == 1

def fmtcard(name, value, comment="") :
    if type(value) == int :
        return ("{:8s}= {:>31d}  / {:35s}").format(name, value, comment)

    if type(value) == str :
        return ("{:8s}= '{:>30s}' / {:35s}").format(name, value, comment)

    if type(value) == float :
        return ("{:8s}= {:>31f}  / {:35s}").format(name, value, comment)

    if type(value) == bool :
        if value:
            return ("{:8s}= {:>31s}  / {:35s}").format(name, "T", comment)
        else :
            return ("{:8s}= {:>31s}  / {:35s}").format(name, "F", comment)
    
def parcard(card) :
    name    = card[0:8].strip()
    value   = shlex.split(card[10:])[0]
    comment = " ".join(shlex.split(card[10:])[1:]).lstrip("/").strip()

    try:
        value = int(value)
    except:
        try:
            value = float(value)
        except:
            pass

    return [name, value, comment]


class Huh(Exception): pass
class EOF(Exception): pass
class BadEOF(Exception): pass

dtype2bitpix = { 8: "u1", "int16": 16, "uint16": -16, "int32": 32, "int64": 64, "float32": -32, "float64": -64 }
bitpix2dtype = { 8: "u1", 16: "i2", 32: "i4", 64: "i8", -32: "f4", -64: "f8" }

class header(object) :
    def __init__(self, fp, primary=True, cards=None) :

        self.card = []
        self.file   = fp
        self.shape  = []
        self.bitpix = 0
        self.head   = { "GCOUNT": [0, 1], "PCOUNT": [0, 0], "BSCALE": [0, 1], "BZERO": [0, 1] }

        if type(fp) == str :
            fp = __builtin__.open(fp, "rb")

        if hasattr(fp, 'read') :
            try:    self.hoff = fp.tell()
            except: self.hoff = 0

            card = fp.read(80)

            if len(card) == 0  : raise EOF
            if len(card) != 80 : raise BadEOF

            if   card[0:8] == "SIMPLE  " : pass
            elif card[0:8] == "XTENSION" : pass
            else : raise Exception("This doesn't appear to be a FITS file")

            self.card.append(card)

            while 1 :
                card = fp.read(80)

                if card[0:8] == "END     " : break

                self.card.append(card)

                if card[8] == "=" :
                    name = card[0:8].strip()
                    valu = card[10:]  

            while self.card[-1] == "" :                 # Delete blank cards after END
                self.card.pop[-1]

            self.ncard     = len(self.card)+1
            self.headbloks = ((self.ncard*80)+(2880-1))/2880
            self.headbytes = self.headbloks * 2880

            if len(self.card) % 80 != 0 :
                try :   fp.seek(self.hoff + self.headbytes, 0)
                except: fp.read(self.headbytes - (len(self.card)+1) * 80)

            try:    self.doff = fp.tell()
            except: self.doff = 0

        elif isinstance(fp, numpy.ndarray) :

            if primary :
                self.card.append(fmtcard("SIMPLE", True))
            else:
                self.card.append(fmtcard("XTENSION", "IMAGE"))

            self.card.append(fmtcard("BITPIX", dtype2bitpix[str(fp.dtype)]))

            naxis = fp.shape
            if len(naxis) == 1 :                        # Force NAXIS >= 2
                naxis = [naxis[0], 1]

            self.card.append(fmtcard("NAXIS", len(naxis)))

            #for i, j in enumerate(range(len(naxis)-1, -1, -1)) :
            for i in range(0, len(naxis)) :
                axis = "NAXIS" + str(i+1)
                self.card.append(fmtcard(axis, naxis[len(naxis)-i-1]))

            self.ncard     = len(self.card)+1
            self.headbloks = ((self.ncard*80)+(2880-1))/2880
            self.headbytes = self.headbloks * 2880

        else:
            raise Huh

        for i, card in enumerate(self.card) :           # Hash card in head for easy lookup
            try :
                name, value, comment = parcard(card)
                self.head[name] = (i, value)
            except:
                pass
            
        if cards != None :                              # Mix in extra cards from user.
            if isinstance(cards, header):
                cards = cards.card

            if type(cards) == list :
                for card in cards :
                    name, value, comment = parcard(card)

                    if not name in self.head :
                        self.head[name] = (len(self.card), value)
                        self.card.append(card)

            elif type(cards) == dict :
                for name in cards.keys() :
                    if not name in self.head :
                        self.head[name] = (len(self.card), cards[name])
                        self.card.append(fmtcard(name, cards[name], None))

            self.ncard     = len(self.card)+1
            self.headbloks = ((self.ncard*80)+(2880-1))/2880
            self.headbytes = self.headbloks * 2880
        
        self.bscale = float(self.head["BSCALE"][1])     # Cache for easy use.
        self.bzero  = float(self.head["BZERO"][1])
        self.bitpix = int(self.head["BITPIX"][1])
        self.pixlbytes = abs(self.bitpix/8)

        if int(self.head["NAXIS"][1]) == 0 or int(self.head["GCOUNT"][1]) == 0 :
            self.datapixls = 0
        else :
            self.datapixls = 1                          # Compute data sizes

            for i in range(1, int(self.head["NAXIS"][1]) + 1) :
                axis = int(self.head["NAXIS" + str(i)][1])
                setattr(self, "NAXIS" + str(i), axis)
                self.datapixls = self.datapixls * axis

                self.shape.insert(0, axis)

            self.datapixls = int(self.head["GCOUNT"][1]) * ( int(self.head["PCOUNT"][1]) + self.datapixls)

        self.databytes = self.datapixls * self.pixlbytes
        self.databloks = (self.databytes+(2880-1))/2880

    def __setitem__(self, indx, value) :
        if ( type(indx) == str ) :
            if self.head.has_key(indx) :

                self.head[indx] = (self.head[indx][0], value)

                name, old, comment = parcard(self.card[self.head[indx][0]])

                self.card[self.head[indx][0]] = fmtcard(name, value, comment)

            else:
                self.head[indx] = (len(self.card), value)
                self.card.append(fmtcard(indx, value))

                self.ncard     = len(self.card)+1
                self.headbloks = ((self.ncard*80)+(2880-1))/2880
                self.headbytes = self.headbloks * 2880

    def __getattr__(self, indx) :
        return self.__getitem__(indx)

    def __contains__(self, indx) :
        if ( type(indx) == str ) :
            return indx in self.head

        raise KeyError(indx)
        
    def __getitem__(self, indx) :
        if ( type(indx) == str ) :
            return self.head[indx][1]

        raise KeyError(indx)

    def dataskip(self) :
        try:    self.file.seek(self.databloks*2880, 1)
        except: self.file.read(self.databloks*2880)

    def datacopy(self, other) :
        other.write(self.file.read(self.databloks*2880))        # This one liners fails?

    def write(self, other) :
        for card in self.card :
            other.write(card)

        other.write("END" + " " * 77)
        other.write(" " * (self.headbytes - (len(self.card)+1) * 80))

class hdu(header) :
    def __init__(self, fp, primary=True, cards=None) :
        if type(fp) == str :
            fp = __builtin__.open(fp, "rb");

        super(hdu, self).__init__(fp, primary=primary, cards=cards)

        if hasattr(fp, 'read') :
            if self.databytes > 0 :
                self.data = numpy.fromfile(fp, dtype=bitpix2dtype[self.bitpix], count=self.datapixls)

                if swapped() :
                    self.data.byteswap(True)

                if self.bitpix == 16 and self.bzero == 32768 :
                    self.data *= self.bscale
                    self.data += self.bzero
                    self.data.dtype = ">u2"

                fp.read(self.databloks*2880 - self.databytes)   # Read the padd.
            
                if len(self.shape) :
                    self.data.shape = self.shape

            else:
                self.data = None

        elif isinstance(fp, numpy.ndarray) :
            self.data = fp

        else:
            raise Huh

    def writeto(self, other) :
        if type(other) == str :
            other = __builtin__.open(other, "wb");

        super(hdu, self).write(other)

        if self.bitpix == 16 and self.bzero == 32768 :
            self.data /= self.bscale
            self.data -= self.bzero

        if swapped() :
            self.data.byteswap(True)

        self.data.tofile(other)

        if swapped() :
            self.data.byteswap(True)

        if self.bitpix == 16 and self.bzero == -32768 :
            self.data += self.bzero
            self.data *= self.bscale

        other.write("\0" * (self.databloks*2880 - self.databytes))


def open(fp) :
    opened = 0

    if type(fp) == str :
        opened = 1
        fp = __builtin__.open(fp, mode="rb");

    headers = []

    while 1 :
        try :
            hdr = hdu(fp)
        except EOF:
            break

        headers.append(hdr)

    if opened :
        fp.close()

    return headers

