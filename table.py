#!/usr/bin/env python

from __future__ import division, print_function, unicode_literals
from collections import OrderedDict, namedtuple
from struct import Struct, calcsize


###############################################################################
# TABLE STUFF
###############################################################################   
class Table(list):
    """Table class."""
    def itercolumn(self, index):
        """Get column iterator."""
        for row in self:
            yield row[index]

    def totext(self):
        """Returns table in tab-delimited text format."""
        return '\n'.join([row.totext() for row in self])


class TypedTable(list):
    """Table with simple type checking. Not recommended."""

    def __init__(self, iterable=None):
        self.rowclass = None
        if iterable:
            for element in iterable:
                self.__check(element)
            list.__init__(iterable)
        else:
            list.__init__()

    def __check(self, element):
        if self.rowclass is None:
            self.rowclass = element.__class__
            return
        if not isinstance(element, self.rowclass):
            raise TypeError('a {} object is required, not {}'
                .format(self.rowclass.__name__, element.__class__.__name__))

    def __setitem__(self, index, element):
        self.__check(element)
        list.__setitem__(self, index, element)

    def append(self, element):
        self.__check(element)
        list.append(self, element)

    def extend(self, iterable):
        for element in iterable:
            self.__check(element)
        list.extend(self, element)

    def insert(self, index, element):
        self.__check(element)
        list.insert(self, element)


def feed(cls, bytes_obj, get_string_hook=None):
    """Feed the data and returns row object."""
    rawdata = cls.struct_obj.unpack(bytes_obj)
    data = []
    for info, element in zip(cls.columns, rawdata):
        if info['type'] == 'str' and get_string_hook is not None:
            data.append(get_string_hook(element))
        elif info['type'].startswith('bit'):
            data.append(element)
            for bitcolumn in info['columns']:
                data.append((element >> bitcolumn['offset']) & ((1 << bitcolumn['length']) - 1))
        elif info['type'].startswith('enum'):
            data.append(info['enum'][format(element)])
        else:
            data.append(element)
    return cls._make(data)


def totext(self):
    """Returns row data in tab-delimited text format."""
    words = []
    column_index = 0
    for column in self.columns:
        if column['type'].startswith('bit'):
            column_index += 1
            for bitcolumn in column['columns']:
                words.append(format(self[column_index], bitcolumn['format']))
                column_index += 1
        elif column['type'] == 'gap':
            words.append(hexlify(self[column_index]))
            column_index += 1
        else:
            words.append(format(self[column_index], column['format']))
            column_index += 1
    return '\t'.join(words)


def tobytes(self):
    """Return row data as bytes object."""
    rowdata = []
    for column in self.columns:
        if column['type'].startswith('bit'):
            bitdata = self.__getattr__(column['name'])
            for bitcolumn in column['columns']:
                bitdata |= ((1 << bitcolumn['length']) - 1) << bitcolumn['offset']
                bitdata &= self.__getattr__(bitcolumn['name']) << bitcolumn['offset']
            rowdata.append(bitdata)
        else:
            rowdata.append(self.__getattr__(column['name']))
    return self.struct_obj.pack(*rowdata)


def newrowclass(tableinfo):
    """Create a new row class.

    If no 'endianess' key was found in tableinfo, little endian was chosen
    by default.
    
    Parameters:
    - ``tableinfo``: Contains row structure, should be loaded from .json file.
    """
    # Get column names and struct string
    columns = []
    types = {'s8': 'b', 'u8': 'B', 's16': 'h', 'u16': 'H', 's32': 'i',
        'u32': 'I', 's64': 'q', 'u64': 'Q', 'f32': 'f', 'str': 'I',
        'ptr': 'I', 'bit8': 'B', 'bit16': 'H', 'bit32': 'I', 'bit64': 'Q',
        'enum8': 'B', 'enum16': 'H'}
    gapstart = 0
    newtableinfo = []
    try:
        structstr = tableinfo['endianess']
    except KeyError:
        structstr = '<'
    for column in tableinfo['columns']:
        if column['offset'] > gapstart:
            structstr += '{}s'.format(column['offset'] - gapstart)
            name = 'c{}'.format(gapstart)
            columns.append(name)
            newtableinfo.append(OrderedDict([
                ('type', 'gap')
            ]))

        if column['type'].startswith('bit'):
            columns.append(column['name'])
            columns.extend([c['name'] for c in column['columns']])
        else:
            columns.append(column['name'])
        newtableinfo.append(column)
        structchr = types[column['type']]
        gapstart = column['offset'] + calcsize(structchr)
        structstr += structchr
    if gapstart < tableinfo['row_length']:
        structstr += '{}s'.format(tableinfo['row_length'] - gapstart)
        name = 'c{}'.format(gapstart)
        columns.append(name)
        newtableinfo.append(OrderedDict([
            ('type', 'gap')
        ]))

    Row = namedtuple('Row', columns)
    Row.columns = newtableinfo
    Row.struct_obj = Struct(structstr)
    Row.feed = classmethod(feed)
    Row.totext = totext
    Row.tobytes = tobytes

    print(columns)
    print(structstr)

    return Row


if __name__ == '__main__':
    pass
