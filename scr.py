#!/usr/bin/env python
"""A Python module which supports SCR file in Fantasy Life game.

Compatible with Python 2 and 3.
"""

from __future__ import division, print_function, unicode_literals
import argparse
import io
import json
import os
import sys
from binascii import hexlify
from collections import OrderedDict, namedtuple
from struct import calcsize, pack, unpack
try:
    from itertools import izip as zip
except ImportError:
    pass

from .table import Table, newrowclass


DEBUG = True

###############################################################################
# SCR
###############################################################################
class TableManager(object):
    """Manage all tables in Fantasy Life game."""
    tables = None

    def __init__(self):
        if TableManager.tables is None:
            path = os.path.join(os.path.dirname(__file__), 'tables.json')
            with open(path, 'r') as file:
                TableManager.tables = json.load(file, object_pairs_hook=OrderedDict)

    def loadtable(self, name, *args):
        """Load a table.

        Params:
        * `name`: Table name, as defined in tables.json file.
        * `*args`: List of table parameters. The first parameters is language \
          in most case. If no table parameter specified, return all tables \
          in an OrderedDict object.
        """
        info = TableManager.tables[name]
        Row = newrowclass(info)
        filepaths = info['paths']
        if len(args) > 0:
            for arg in args:
                filepaths = filepaths[arg]
            with open(filepaths, 'rb') as file:
                scrfile = SCR(file.read())
            table = Table()
            for bytes_obj in scrfile.iterrowbytes():
                row = Row.feed(bytes_obj, get_string_hook=scrfile.getstring)
                table.append(row)
            return table

        else:
            tables = OrderedDict()
            for name, filepath in filepaths.items():
                with open(filepath, 'rb') as file:
                    scrfile = SCR(file.read())
                table = Table()
                for bytes_obj in scrfile.iterrowbytes():
                    row = Row.feed(bytes_obj, get_string_hook=scrfile.getstring)
                    table.append(row)
                tables[name] = table
            return tables

    def appendmultiple(self, name, filepath, firstlanguage):
        """Add multiple tables to tables.json.

        Params:
        * `name`: Table name.
        * `filepath`: Path of the first scr file.
        * `firstlanguage`: Language code of the first file.

        Raise `ValueError` if `name` already exists in tables.json.
        """
        if name in TableManager.tables:
            raise ValueError('"{}" table already exists'.format(name))
        scr = load(filepath)
        dirname = os.path.dirname(filepath)
        fileindex, ext = os.path.splitext(os.path.basename(filepath))
        fileindex = int(fileindex)
        languages = ['jp', 'ae', 'af', 'de', 'en', 'es', 'fr', 'it', 'uk']
        paths = OrderedDict()
        firstindex = -1
        for i, language in enumerate(languages):
            if firstlanguage == language:
                firstindex = i
            if firstindex >= 0:
                paths[language] = os.path.join(dirname,
                    '{:08d}{}'.format(fileindex + i - firstindex, ext))\
                    .replace('\\', '/')
        TableManager.tables[name] = OrderedDict([
            ('paths', paths),
            ('row_length', scr.row_length),
            ('columns', [])
        ])

    def save(self):
        """Save table data to file to tables.json."""
        with open('tables.json', 'w') as file:
            json.dump(self.tables, file, separators=(',', ': '), indent=4)


class UnsupportedSCRError(TypeError):
    pass


class SCR(object):
    """SCR file."""
    colors = {
        0: 'Black',
        3: 'Red',
        4: 'Green'
    }
    buttons = {
        0: 'A',
        1: 'B',
        2: 'X',
        3: 'D-Pad',
        4: 'Circle Pad',
        5: 'L', # Big L
        6: 'R', # Big R
        7: 'L',
        8: 'R',
        9: 'Y', # Big Y
        10: 'Y'
    } # There are also big Y, big L and big R button in the images

    def __init__(self, raw):
        self.raw = raw
        table_info_offset = unpack('<I', self.raw[0x14:0x18])[0]
        self.row_count, self.row_length, self.table_offset = \
            unpack('<3I', self.raw[table_info_offset:table_info_offset + 12])
    
    def getstring(self, offset, tag=False):
        """Return string at `offset`."""
        pos = offset
        strings = []
        while True:
            if self.raw[pos:pos + 4] == b'\xE9\xFF\xFF\xFF': # Branch
                byte_count = unpack('<H', self.raw[pos + 22:pos + 24])[0]
                pos += 24
                strings.append(self.raw[pos:pos + byte_count - 2]
                    .decode('utf-16le'))
                strings.append(' / ')

                pos += byte_count
                if self.raw[pos:pos + 2] == b'\xFF\xFF':
                    pos += 2
                byte_count = unpack('<H', self.raw[pos + 2:pos + 4])[0]
                strings.append(self.raw[pos + 4:pos + 2 + byte_count]
                    .decode('utf-16le'))
                pos = pos + 4 + byte_count

            elif self.raw[pos:pos + 4] == b'\xF1\xFF\xFF\xFF':
                # Pause, press A to continue
                strings.append('\\n')
                pos = pos + 8

            elif self.raw[pos:pos + 4] == b'\xF4\xFF\xFF\xFF': # Display furinaga
                byte_count = unpack('<H', self.raw[pos + 10:pos + 12])[0]
                #strings.append(self.raw[pos + 12:pos + 10 + byte_count])
                pos = pos + 12 + byte_count

            elif self.raw[pos:pos + 4] == b'\xF5\xFF\xFF\xFF': # Choice
                choice_count = unpack('<I', self.raw[pos + 12:pos + 16])[0]
                pos += 16 + 4 * choice_count
                strings.append(' (' if len(strings) > 0 else '(')
                for choice_index in range(choice_count):
                    byte_count = unpack('<H', self.raw[pos + 4:pos + 6])[0]
                    choice_end_pos = pos + 8
                    while choice_end_pos < pos + 8 + byte_count and \
                        self.raw[choice_end_pos:choice_end_pos + 2] != b'\0\0':
                        choice_end_pos += 2
                    strings.append(self.raw[pos + 8:choice_end_pos].decode('utf-16le'))
                    if choice_index != choice_count - 1:
                        strings.append(' / ')
                    pos = pos + 8 + byte_count
                strings.append(')')

            elif self.raw[pos:pos + 4] == b'\xF6\xFF\xFF\xFF': # Variables
                unpacked = unpack('<II', self.raw[pos + 4:pos + 12])
                strings.append('({}, {})'.format(*unpacked))
                pos += 12

            elif self.raw[pos:pos + 4] == b'\xF7\xFF\xFF\xFF': # Text color
                pos += 12

            elif self.raw[pos:pos + 4] == b'\xF9\xFF\xFF\xFF': # Buttons
                button = unpack('<I', self.raw[pos + 8:pos + 12])[0]
                if button in SCR.buttons:
                    strings.append(SCR.buttons[button])
                else:
                    strings.append('?')
                pos += 12

            elif self.raw[pos:pos + 4] == b'\xF0\xFF\xFF\xFF': # Line break
                strings.append('\\n')
                pos += 8

            elif self.raw[pos:pos + 4] == b'\xF1\xFF\xFF\xFF':
                pos += 8

            elif self.raw[pos:pos + 2] == b'\xFF\xFF':
                pos += 2

            elif self.raw[pos:pos + 2] != b'\0\0':
                strings.append(self.raw[pos:pos + 2].decode('utf-16le'))
                pos += 2

            else:
                break
        return ''.join(strings)

    def iterrowbytes(self):
        """Yield a memoryview object of raw bytes of a row."""
        mv = memoryview(self.raw)
        for row_index in range(self.row_count):
            offset = self.table_offset + row_index * self.row_length
            yield mv[offset:offset + self.row_length]

    def tolines(self, struct=None, string_offsets=[]):
        """Dump the data into a list of tab-delimited lines.
        
        Params:
        * `struct`: Python struct format string. If None, dump raw bytes.
        * `string_offsets`: String offsets.
        """
        table_info_offset = unpack('<I', self.raw[0x14:0x18])[0]
        row_count, column_count, table_offset = \
            unpack('<3I', self.raw[table_info_offset:table_info_offset + 12])

        table = []
        for row_index in range(row_count):
            row = []
            local_offset = table_offset + row_index * column_count
            row.append('0x{:08X}'.format(local_offset))
            row.append('0x{:04X}'.format(row_index))

            # Dump the strings
            for offset_index in range(len(string_offsets)):
                offset = string_offsets[offset_index]
                string_offset = unpack('<I',
                    self.raw[local_offset + offset:local_offset + offset + 4])[0]
                row.append(self.getstring(string_offset))

            # Dump all bytes in the row.
            rowbytes = self.raw[local_offset:local_offset + column_count]
            if struct is None:
                try:
                    row.extend([format(ord(b), '02X') for b in rowbytes])
                except TypeError:
                    row.extend([format(b, '02X') for b in rowbytes])
            else:
                unpacked = unpack(struct, rowbytes)
                for num in unpacked:
                    row.append(format(num))

            table.append('\t'.join(row))

        return table


def load(path):
    """Load a file."""
    with open(path, 'rb') as scrfile:
        magic = scrfile.read(4)
        if magic == b'\x13\x80\x03\x1D':
            scrfile.seek(0)
            raw = scrfile.read()
        else:
            scrfile.seek(0x10)
            magic = scrfile.read(4)
            if magic == b'\x13\x80\x03\x1D':
                scrfile.seek(0x10)
                raw = scrfile.read()
            else:
                raise UnsupportedSCRError('unsupported file.')
    return SCR(raw)


def test_load():
    tm = TableManager()
    table = tm.loadtable('items', 'uk')
    print(table[47])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='path to input file')
    parser.add_argument('--str', nargs='*', help='string offsets (relative)')
    parser.add_argument('--struct', default=None, help='Python struct format string')
    parser.add_argument('-a', '--addtable', metavar=('name', 'file', 'language'),
        nargs=3, help='add multiple tables to tables.json')
    if DEBUG:
        parser.add_argument('-t', '--test', help='run tests')
    args = parser.parse_args()

    if DEBUG and args.test:
        name = 'test_' + args.test
        print('Running {}...'.format(name))
        globals()[name]()

    elif args.addtable:
        tm = TableManager()
        tm.appendmultiple(*args.addtable)
        tm.save()

    elif args.file:
        scr = load(args.file)
        string_offsets = []
        if args.str is not None:
            string_offsets = [int(x) for x in args.str]
        outpath = os.path.splitext(os.path.basename(args.file))[0] + '_table.txt'
        with io.open(outpath, mode='w', encoding='utf-8') as file:
            file.write('\n'.join(
                scr.tolines(string_offsets=string_offsets, struct=args.struct)
            ))
