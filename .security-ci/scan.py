"""Fail-closed source/image gate. Raw scanner output is never printed or uploaded."""
import argparse
import collections
import json
import os
import pathlib
import re
import subprocess
import tempfile

POLICY = pathlib.Path(__file__).resolve().parent
SKIP = {'.git', 'node_modules', '.venv', 'venv', '.dart_tool', '.security-ci', '.security-ci-reports'}

def issue(kind, path='', rule='', severity='ERROR', line=None):
    item={'kind':kind,'path':str(path),'rule':str(rule),'severity':str(severity)}
    if isinstance(line,int): item['line']=line
    return item

def evaluate_trivy(data, image=False):
    if data.get('SchemaVersion') != 2 or not isinstance(data.get('Results',[]),list):
        raise ValueError('invalid Trivy report')
    result=[]
    if image and (not data.get('Metadata',{}).get('ImageID') or data.get('ArtifactType')!='container_image'):
        raise ValueError('missing image identity')
    if data.get('Metadata',{}).get('OS',{}).get('EOSL'):
        result.append(issue('unsupported-os'))
    if image and not any(t.get('Packages') for t in data.get('Results',[])):
        result.append(issue('coverage',rule='image-package-inventory-empty'))
    for target in data.get('Results',[]):
        for v in target.get('Vulnerabilities') or []:
            if v.get('FixedVersion') or v.get('Severity') in ('HIGH','CRITICAL'):
                result.append(issue('vulnerability',target.get('Target'),v.get('VulnerabilityID'),v.get('Severity','UNKNOWN')))
        for s in target.get('Secrets') or []:
            result.append(issue('secret',target.get('Target'),s.get('RuleID'),s.get('Severity','HIGH'),s.get('StartLine')))
    return result

def evaluate_semgrep(data):
    if not isinstance(data.get('results'),list) or not isinstance(data.get('errors'),list):
        raise ValueError('invalid Semgrep report')
    result=[]
    for e in data['errors']:
        result.append(issue('scan-error',e.get('path',''),'semgrep-'+str(e.get('type','error'))))
    for f in data['results']:
        result.append(issue('code',f.get('path'),f.get('check_id'),'HIGH',f.get('start',{}).get('line')))
    return result

def coverage(root):
    """Do not interpret unpinned/unsupported dependency declarations as clean."""
    result=[]; manifests=0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:]=[d for d in dirs if d not in SKIP and not pathlib.Path(directory,d).is_symlink()]
        folder=pathlib.Path(directory)
        for name in files:
            p=folder/name; rel=p.relative_to(root).as_posix()
            if p.is_symlink():
                result.append(issue('coverage',rel,'symlink-not-scanned')); continue
            if name=='.semgrepignore' and p.read_text(errors='replace').strip():
                result.append(issue('coverage',rel,'custom-semgrep-exclusions-not-approved'))
            if name=='package.json':
                manifests+=1
                # A root workspace lock covers child manifests.
                parents=[folder]+[x for x in folder.parents if x==root or root in x.parents]
                if not any((x/lock).is_file() for x in parents for lock in ('package-lock.json','pnpm-lock.yaml','yarn.lock','npm-shrinkwrap.json','bun.lock','bun.lockb')):
                    result.append(issue('coverage',rel,'missing-js-lockfile'))
            if name in ('pubspec.yaml','Podfile','Package.swift','pyproject.toml'):
                manifests+=1
                locks={'pubspec.yaml':['pubspec.lock'],'Podfile':['Podfile.lock'],'Package.swift':['Package.resolved'],'pyproject.toml':['uv.lock','poetry.lock','pdm.lock']}[name]
                if not any((folder/lock).is_file() for lock in locks):
                    result.append(issue('coverage',rel,'missing-lockfile'))
            if re.fullmatch(r'requirements(?:[._-].+)?\.txt',name):
                manifests+=1
                for n,raw in enumerate(p.read_text(errors='replace').splitlines(),1):
                    value=raw.split('#',1)[0].strip()
                    if not value or value.startswith(('--hash=', '--index-url ', '--extra-index-url ')) or value=='\\': continue
                    if not re.match(r'^[A-Za-z0-9_.-]+(?:\[[^]]+\])?\s*==\s*[^\s*;]+',value):
                        result.append(issue('coverage',rel,'unresolved-python-dependency',line=n))
            # Deterministic supplement to scanner defaults; never retain the value.
            if p.stat().st_size < 5_000_000:
                content=p.read_bytes()
                if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',content):
                    result.append(issue('secret',rel,'private-key-material','CRITICAL'))
    return result,manifests

def command_json(command, output, cwd):
    env=dict(os.environ)
    # Semgrep's base image assumes /src; Cloud Build uses /workspace instead.
    env.pop('SEMGREP_IN_DOCKER',None)
    completed=subprocess.run(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1500)
    if completed.returncode != 0:
        raise RuntimeError('scanner failed (exit '+str(completed.returncode)+')')
    return json.loads(output.read_text())

def scan(mode, target):
    findings=[]; metadata={}
    with tempfile.TemporaryDirectory(prefix='elamp-gate-') as scratch:
        scratch=pathlib.Path(scratch); report=scratch/'trivy.json'
        base=['trivy','--config',str(POLICY/'empty.yaml'),'--cache-dir','/tmp/elamp-trivy-cache']
        common=['--scanners','vuln,secret','--format','json','--output',str(report),'--ignorefile','/dev/null','--secret-config','','--timeout','20m','--list-all-pkgs','--quiet']
        if mode=='source':
            root=pathlib.Path(target).resolve()
            findings,manifests=coverage(root);metadata['dependency_manifests']=manifests
            args=base+['fs']+common+['--skip-dirs','.git','--skip-dirs','.security-ci','--skip-dirs','.security-ci-reports',str(root)]
        else:
            root=pathlib.Path('/tmp')
            args=base+['image']+common+['--input',str(pathlib.Path(target).resolve())]
        data=command_json(args,report,root)
        findings+=evaluate_trivy(data,mode=='image')
        metadata['image_id']=data.get('Metadata',{}).get('ImageID')
        if mode=='source':
            targets=[str(x.get('Target','')).replace('\\','/') for x in data.get('Results',[])]
            for directory,dirs,files in os.walk(root):
                dirs[:]=[d for d in dirs if d not in SKIP and not pathlib.Path(directory,d).is_symlink()]
                for filename in files:
                    if filename not in ('package-lock.json','pnpm-lock.yaml','yarn.lock','pubspec.lock','Podfile.lock','Package.resolved','uv.lock','poetry.lock','pdm.lock','requirements.txt'): continue
                    path=pathlib.Path(directory,filename);rel=path.relative_to(root).as_posix()
                    if path.is_symlink(): continue
                    # Missing parser evidence is a coverage gap, never a clean bill.
                    if path.stat().st_size and not any(t.endswith(rel) for t in targets):
                        findings.append(issue('coverage',rel,'dependency-file-not-assessed'))
        if mode=='source':
            report=scratch/'semgrep.json'
            args=['semgrep','scan','--config',str(POLICY/'rules.yml'),'--metrics=off','--disable-version-check','--disable-nosem','--no-git-ignore','--json','--output',str(report),'--quiet']
            for skip in sorted(SKIP): args+=['--exclude',skip]
            args+=[str(root)]
            data=command_json(args,report,root)
            findings+=evaluate_semgrep(data)
            metadata['code_files_scanned']=len(data.get('paths',{}).get('scanned',[]))
        return findings,metadata

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['source','image']);p.add_argument('target');p.add_argument('--report')
    args=p.parse_args()
    try:
        findings,metadata=scan(args.mode,args.target)
    except Exception as e:
        # Exception messages may include raw source/credentials: publish only the type.
        findings=[issue('scan-error',rule=type(e).__name__)]; metadata={}
    result={'policy':'elamp-security-v1','mode':args.mode,'passed':not findings,'counts':dict(collections.Counter(f['kind'] for f in findings)),'findings':findings,'metadata':metadata}
    if args.report:
        dest=pathlib.Path(args.report);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(result,indent=2),encoding='utf-8')
    # Counts only in CI log. Redacted locations are in the report.
    print(json.dumps({k:v for k,v in result.items() if k!='findings'}))
    return 1 if findings else 0

if __name__=='__main__':
    raise SystemExit(main())
