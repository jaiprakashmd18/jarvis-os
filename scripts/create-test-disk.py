#!/usr/bin/env python3
"""Create only the dedicated fresh test image via QEMU's built-in qcow2 driver.

Uses QMP blockdev-create, so a separate qemu-img download is unnecessary. Refuses
all existing files and never opens a host block device.
"""
from pathlib import Path
import json
import os
import subprocess
import time

root=Path(__file__).resolve().parents[1]
path=root/'build/qemu/install-disk.qcow2'
path.parent.mkdir(parents=True,exist_ok=True)
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
p=subprocess.Popen(['qemu-system-x86_64','-machine','none','-display','none','-nodefaults','-S','-qmp','stdio'],
                   stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
serial=0

def request(command,arguments=None):
    global serial
    serial+=1
    message={'execute':command,'id':serial}
    if arguments is not None: message['arguments']=arguments
    p.stdin.write(json.dumps(message)+'\n');p.stdin.flush()
    while True:
        line=p.stdout.readline()
        if not line: raise RuntimeError('QMP exited: '+p.stderr.read()[-1000:])
        result=json.loads(line)
        if result.get('id')==serial:
            if 'error' in result: raise RuntimeError(str(result['error']))
            return result.get('return')

try:
    hello=json.loads(p.stdout.readline());assert 'QMP' in hello
    request('qmp_capabilities')
    request('blockdev-create',{'job-id':'jarvis-create-disk','options':{
        'driver':'qcow2','file':{'driver':'file','filename':str(path)},'size':40*1024**3}})
    for _ in range(200):
        jobs=request('query-jobs')
        job=next((j for j in jobs if j['id']=='jarvis-create-disk'),None)
        if job is None: break
        if job.get('error'): raise RuntimeError(job['error'])
        if job['status']=='concluded':
            request('job-dismiss',{'id':'jarvis-create-disk'});break
        if job['status']=='pending': request('job-finalize',{'id':'jarvis-create-disk'})
        time.sleep(.05)
    else: raise RuntimeError('Disk creation did not complete')
    request('quit')
    p.wait(timeout=5)
    with path.open('rb') as f:
        header=f.read(32)
    assert header[:4]==b'QFI\xfb' and int.from_bytes(header[24:32],'big')==40*1024**3
    print('Created fresh 40 GiB qcow2 test disk:',path)
finally:
    if p.poll() is None: p.terminate();p.wait(timeout=5)
