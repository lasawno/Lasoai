"""Stop only this checkout's Reflex server tree; Linux/Codespaces, no secrets."""
from pathlib import Path
import os
import signal
import subprocess
import time


def select_processes(records, app_dir):
    """Select server launchers/workers in this app directory and descendants."""
    selected = set()
    for pid, record in records.items():
        if record['cwd'] != str(app_dir):
            continue
        args = record['args']
        words = [Path(arg).name for arg in args]
        reflex_run = any(words[i:i+2] == ['reflex', 'run'] for i in range(len(words)-1))
        worker = any(word in {'granian', 'uvicorn', 'granian.exe'} for word in words)
        if reflex_run or worker:
            selected.add(pid)
    changed = True
    while changed:
        before = len(selected)
        selected.update(pid for pid, record in records.items() if record['ppid'] in selected)
        changed = len(selected) != before
    return selected


def snapshot():
    result = {}
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit(): continue
        try:
            if folder.stat().st_uid != os.getuid(): continue
            stat = (folder/'stat').read_text().rsplit(')',1)[1].split()
            if stat[0] == 'Z': continue
            result[int(folder.name)] = {'ppid':int(stat[1]), 'start':stat[19],
                'cwd':str((folder/'cwd').resolve(strict=True)),
                'args':(folder/'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0')}
        except (OSError, ValueError, IndexError): continue
    return result


def main():
    if not Path('/proc').is_dir(): raise SystemExit('This stop command requires Linux/Codespaces.')
    root = Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
    records = snapshot()
    selected = select_processes(records, root/'apps/reflex') - {os.getpid(),os.getppid()}
    if not selected:
        print('No matching Reflex server process found for this checkout.');return
    def alive():
        now=snapshot()
        return {pid for pid in selected if pid in now and now[pid]['start']==records[pid]['start']}
    def send(sig):
        for pid in alive():
            try: os.kill(pid,sig)
            except ProcessLookupError: pass
    print(f'Stopping {len(selected)} process(es) belonging to this Reflex app.')
    send(signal.SIGTERM)
    deadline=time.monotonic()+4
    while alive() and time.monotonic()<deadline:time.sleep(.1)
    if alive():
        print('Escalating remaining app processes after the graceful-stop deadline.')
        send(signal.SIGKILL)
    deadline=time.monotonic()+2
    while alive() and time.monotonic()<deadline:time.sleep(.1)
    if alive():raise SystemExit('Some selected processes remain; do not start a duplicate server.')
    print('Reflex app process tree stopped. Source files and browser drafts were not deleted.')


if __name__ == '__main__': main()
