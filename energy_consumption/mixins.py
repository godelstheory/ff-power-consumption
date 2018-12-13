class NameMixin(object):
    """ Give a class a name attribute
    """

    @property
    def name(self):
        return self.__class__.__name__.decode('utf-8')

    @name.setter
    def name(self, value):
        raise AttributeError('name is a reference to __class__.__name__')