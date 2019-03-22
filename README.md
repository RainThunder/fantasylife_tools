# fantasylife_tools
A collection of tools and documentation for the Fantasy Life game on the Nintendo 3DS.

# Tools
## Requirements
* Python 2 or Python 3
* A method to access the game files. I recommended using [GodMode9](https://github.com/d0k3/GodMode9) on a hacked 3DS. You can also try [fuse-3ds](https://github.com/ihaveamac/fuse-3ds) if you have access to an encrypted ROM dump.
* [3ds-xfsatool](https://github.com/polaris-/3ds-xfsatool)
** After extracting the game files, you have to extract `_file_archive.bin` using 3ds-xfsatool.

## List of tools and usage
### scr.py
* Dump data from .scr files inside `_file_archive.bin` to a tab-delimited text file.
* See the help message with `python scr.py --help`

### arc.py
* Extract certain .bin files inside `_file_archive.bin`. It is recommended to use this tool with a folder which contains all files extracted by 3ds-xfsatool.
* Usage: `python arc.py <file / folder>`

# Documentation
* https://github.com/RainThunder/fantasylife_tools/wiki

# Credits
* [andibad](https://github.com/andibadra) for inspiring me to datamine this game.
