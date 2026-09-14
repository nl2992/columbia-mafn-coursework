#!/usr/bin/env python3
"""Start the archive viewer and its local answer model; stop owned processes with Ctrl-C."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import webbrowser
from urllib.request import ProxyHandler, build_opener

ROOT=Path(__file__).resolve().parents[1]


def available(url):
    try:
        with build_opener(ProxyHandler({})).open(url,timeout=1) as response:
            return response.status==200
    except OSError:
        return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true',help='Open the archive in the default browser after startup')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:
        raise SystemExit('Choose a port between 1024 and 65535.')
    url=f'http://127.0.0.1:{args.port}/'
    if available(url+'api/health'):
        print(f'Archive service is already running: {url}')
        if args.open:webbrowser.open(url)
        return
    processes=[];log=None
    try:
        if not available('http://127.0.0.1:11434/api/tags'):
            binary=shutil.which('ollama')
            if not binary:
                raise SystemExit('Install Ollama with brew install ollama; see rag/README.md for model setup.')
            logs=ROOT/'.rag/logs';logs.mkdir(parents=True,exist_ok=True)
            log=(logs/'ollama.log').open('a')
            env={**os.environ,'OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_NO_CLOUD':'1',
                 'OLLAMA_MODELS':str(ROOT/'.rag/models/ollama'),'OLLAMA_NUM_PARALLEL':'1',
                 'OLLAMA_CONTEXT_LENGTH':'8192','OLLAMA_DEBUG_LOG_REQUESTS':'false'}
            model=subprocess.Popen([binary,'serve'],env=env,stdout=log,stderr=log)
            processes.append(model)
            for _ in range(40):
                if available('http://127.0.0.1:11434/api/tags'):break
                if model.poll() is not None:raise SystemExit('Local model startup failed; see .rag/logs/ollama.log')
                time.sleep(.25)
            else:raise SystemExit('Local model startup timed out')
        from rag_copilot import LocalGenerator
        if not LocalGenerator().status()['available']:
            raise SystemExit('Model not installed. With Ollama running, use: ollama pull qwen3:4b')
        server=subprocess.Popen([sys.executable,str(ROOT/'scripts/rag_search.py'),'serve','--port',str(args.port)],cwd=ROOT)
        processes.append(server)
        for _ in range(80):
            if available(url+'api/health'):break
            if server.poll() is not None:raise SystemExit('Archive service startup failed')
            time.sleep(.25)
        else:raise SystemExit('Archive service startup timed out')
        print(f'Open {url} — Ctrl-C stops this launcher’s services.',flush=True)
        if args.open:webbrowser.open(url)
        server.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        if log:log.close()


if __name__=='__main__':main()
