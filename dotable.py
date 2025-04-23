
class Dotable(object):
    def __init__(self, **keywordargs): self.__dict__.update(keywordargs)

    def __getitem__(self, indx):
        return self.__dict__[indx]

    def __setitem__(self, indx, value):
        self.__dict__[indx] = value

    def __iter__(self) :
        return iter(self.__dict__)

    def keys(self) :
        return self.__dict__.keys()

