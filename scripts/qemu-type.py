#!/usr/bin/env python3
"""Type a command into the dedicated diskless QEMU test guest's active console."""
import socket
import sys
import time
from pathlib import Path
keys={',':'comma','{':'shift-bracket_left','}':'shift-bracket_right',' ':'spc','/':'slash','-':'minus','_':'shift-minus','.':'dot',':':'shift-semicolon',';':'semicolon','|':'shift-backslash','&':'shift-7','=':'equal','"':'shift-apostrophe',"'":'apostrophe','(':'shift-9',')':'shift-0','>':'shift-dot','<':'shift-comma','*':'shift-8','?':'shift-slash','~':'shift-grave','$':'shift-4','!':'shift-1','@':'shift-2','[':'bracket_left',']':'bracket_right','`':'grave','\\':'backslash'}
root=Path(__file__).resolve().parents[1]
s=socket.socket(socket.AF_UNIX);s.settimeout(2);s.connect(str(root/'build/qemu/monitor.sock'));s.recv(4096)
for c in sys.argv[1]+('' if '--no-enter' in sys.argv[2:] else '\n'):
    key='ret' if c=='\n' else (keys.get(c) or ('shift-'+c.lower() if c.isupper() else c))
    s.sendall(f'sendkey {key} 20\n'.encode());time.sleep(.10)
    try: s.recv(8192)
    except socket.timeout: pass
s.close()
