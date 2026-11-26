"""Local/CI entry point. Docker is required; no production credentials are passed."""
import argparse, os, pathlib, subprocess, tempfile

def run(cmd):
    return subprocess.run(cmd,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['source','image']);p.add_argument('target',nargs='?',default='.')
    p.add_argument('--report',default='security-report.json');args=p.parse_args()
    policy=pathlib.Path(__file__).resolve().parent
    tag='elamp-security:tmp-'+str(os.getpid())
    report=pathlib.Path(args.report).resolve();report.parent.mkdir(parents=True,exist_ok=True)
    try:
        run(['docker','build','--platform','linux/amd64','--label','dev.workspace.lifecycle=temporary','--label','dev.workspace.task=elamp-security-ci','-t',tag,str(policy)])
        source=pathlib.Path(args.target).resolve()
        if not source.exists(): raise ValueError('scan target does not exist')
        mount=source if source.is_dir() else source.parent
        target='/src' if source.is_dir() else '/src/'+source.name
        # Scanner output stays outside the read-only source and includes no snippets/secrets.
        identity=['--user',str(os.getuid())+':'+str(os.getgid())] if hasattr(os,'getuid') else []
        result=subprocess.run(['docker','run','--rm','--cap-drop=ALL','--security-opt=no-new-privileges','--env','HOME=/tmp']+identity+['--mount','type=bind,source='+str(mount)+',target=/src,readonly','--mount','type=bind,source='+str(report.parent)+',target=/reports',tag,args.mode,target,'--report','/reports/'+report.name])
        return result.returncode
    finally:
        subprocess.run(['docker','image','rm',tag],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__': raise SystemExit(main())
