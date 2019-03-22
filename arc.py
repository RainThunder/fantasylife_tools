#!/usr/bin/env python
"""A module that support sub-archive file in Fantasy Life."""

from __future__ import division, print_function, unicode_literals
import os
import sys
import argparse
from collections import namedtuple
from struct import unpack, error as struct_error


class InvalidFileError(Exception):
    pass


class Arc(object):
    """"""
    MAGIC = b'R \rC'
    FileEntry = namedtuple(
        'FileEntry',
        [
            'path', 'unknown1', 'unknown2', 'unknown3', 'file_length',
            'path_offset', 'file_offset'
        ]
    )
    
    def __init__(self, path):
        self.path = path
        self.file_entries = []
        
        file = open(self.path, 'rb')
        magic = file.read(4)
        if magic != Arc.MAGIC:
            raise InvalidFileError('Invalid file.')

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        if file_size < 0x14:
            raise InvalidFileError('File is too small.')

        file.seek(4, os.SEEK_SET)
        self.data_length, self.unknown1, self.unknown2, \
            file_entries_offset = unpack('<4I', file.read(0x10))
        if 0x14 + self.data_length != file_size:
            raise InvalidFileError('Invalid file.')

        file.seek(file_entries_offset, os.SEEK_SET)
        raw_file_entries = file.read()
        for offset in range(0, len(raw_file_entries), 0x14):
            u1, path_length, u2, u3, file_length, path_offset, file_offset = \
                unpack('<BBH4I', raw_file_entries[offset:offset + 0x14])
            file.seek(path_offset, os.SEEK_SET)
            path = file.read(path_length).decode('ascii')
            entry = Arc.FileEntry(path, u1, u2, u3,
                                  file_length, path_offset, file_offset)
            self.file_entries.append(entry)

        self.file = file

    @property
    def file_count(self):
        """File count."""
        return len(self.file_entries)
            
    def getdata(self, file_index):
        """Get data of the file at `file_index`."""
        entry = self.file_entries[file_index]
        self.file.seek(entry.file_offset)
        return self.file.read(entry.file_length)
            
    def getfilepath(self, file_index):
        """Get file path of file at file_index."""
        return self.file_entries[file_index].path


def unpack_file(filepath, outdir):
    """Unpack file in `filepath` to `outdir`."""
    bin = Arc(filepath)
    for file_index in range(bin.file_count):
        outpath = os.path.join(
            outdir, bin.getfilepath(file_index).replace('/', os.sep))
        outsubdir = os.path.dirname(outpath)
        if not os.path.isdir(outsubdir):
            os.makedirs(outsubdir)
        print(outpath)
        with open(outpath, 'wb') as file:
            file.write(bin.getdata(file_index))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default='archive\\bin',
                        help='path to bin file.')
    parser.add_argument('-o', '--out', default='bin', help='output folder')
    args = parser.parse_args()

    if os.path.isfile(args.path):
        unpack_file(args.path, args.out)

    elif os.path.isdir(args.path):
        for dirpaths, dirnames, filenames in os.walk(args.path):
            for filename in filenames:
                path = os.path.join(dirpaths, filename)
                try:
                    unpack_file(path, args.out)
                    print(path)
                except (TypeError, struct_error):
                    pass

    else:
        print('{} is not an existing file or folder.'.format(args.path))