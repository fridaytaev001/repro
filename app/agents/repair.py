"""Bounded source repair in a per-case copy, gated by protected checks."""
import asyncio
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from uuid import uuid4

from app.handoff import fixture_for
from app.providers.crusoe import CrusoeClient, ProviderError
from app.settings import ROOT


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RepairWorkspace:
    sources = {'store.js':ROOT/'demo_store/store.js','index.html':ROOT/'demo_store/index.html',
               'rules.html':ROOT/'demo_store/rules.html','style.css':ROOT/'app/static/style.css',
               'report.js':ROOT/'app/static/report.js'}

    def __init__(self, directory, case):
        self.directory = Path(directory).resolve()
        self.baseline = self.directory/'baseline'
        self.candidate = self.directory/'candidate'
        self.protected = self.directory/'protected'
        self.protected.mkdir(parents=True)
        for site in [self.baseline,self.candidate]:
            site.mkdir()
            for name,source in self.sources.items():
                shutil.copyfile(source,site/name)
        self.original_hashes = {str(source):digest(source) for source in self.sources.values()}
        for source in [ROOT/'app/agents/verifier.py',ROOT/'app/tools/browser.py',ROOT/'scripts/replay_case.py']:
            self.original_hashes[str(source)] = digest(source)
        fixture = fixture_for(case)
        if fixture is None:
            raise ValueError('A frozen confirmed candidate is required.')
        (self.protected/'fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
        shutil.copyfile(ROOT/'scripts/check_repair.py',self.protected/'check_repair.py')
        self.protected_hashes = {str(p):digest(p) for p in [*self.baseline.iterdir(),*self.protected.iterdir()]}
        self.baseline_identity = hashlib.sha256(json.dumps(self.protected_hashes,sort_keys=True).encode()).hexdigest()
        self.edits = 0

    def path(self, value):
        # This milestone permits one source file, never tests, HTML, fixtures,
        # criteria, baseline, environment, logs, or arbitrary directories.
        if value != 'store.js':
            raise ValueError('Only candidate store.js is available to the repairer.')
        path = self.candidate/value
        if path.is_symlink() or not path.resolve().is_relative_to(self.candidate):
            raise ValueError('Source path escaped the isolated copy.')
        return path

    def read(self, path):
        content = self.path(path).read_text(encoding='utf-8')
        return '\n'.join(f'{i}: {line}' for i,line in enumerate(content.splitlines(),1))

    def patch(self,path,old,new):
        self.check_integrity()
        if self.edits >= 3 or not old or len(old)>8000 or len(new)>8000:
            raise ValueError('Repair edit budget exceeded or replacement is invalid.')
        target = self.path(path)
        content = target.read_text(encoding='utf-8')
        if content.count(old)!=1:
            raise ValueError('Patch must match exactly one existing source span.')
        target.write_text(content.replace(old,new,1),encoding='utf-8')
        self.edits += 1

    def check_integrity(self):
        for name,expected in {**self.protected_hashes,**self.original_hashes}.items():
            if digest(name)!=expected:
                raise ValueError('Protected baseline/check/fixture or original source changed.')


async def run_command(command, cwd, timeout=60):
    # No shell, credentials, inherited PYTHON startup hooks, or arbitrary commands.
    environment = {key:value for key,value in os.environ.items()
                   if key.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP','HOME','USERPROFILE','PLAYWRIGHT_BROWSERS_PATH'}}
    environment.update(PYTHONPATH=str(ROOT),PYTHONUTF8='1')
    process = await asyncio.create_subprocess_exec(*map(str,command),cwd=cwd,env=environment,
                                                 stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:
        stdout,stderr = await asyncio.wait_for(process.communicate(),timeout)
    except (TimeoutError,asyncio.CancelledError):
        process.kill()
        await process.communicate()
        raise
    return {'returncode':process.returncode,'stdout':stdout.decode(errors='replace')[-8000:],
            'stderr':stderr.decode(errors='replace')[-8000:]}


REPAIR_TOOLS = [{'type':'function','function':{'name':name,'description':description,'parameters':{
    'type':'object','properties':properties,'required':required,'additionalProperties':False}}}
    for name,description,properties,required in [
        ('read_source','Read bounded isolated candidate source with line numbers.',{'path':{'type':'string','enum':['store.js']}},['path']),
        ('search_source','Search isolated candidate source for a literal string.',{'path':{'type':'string','enum':['store.js']},'query':{'type':'string','maxLength':200}},['path','query']),
        ('patch_source','Replace exactly one source span, at most three edits. Only store.js can change.',{
            'path':{'type':'string','enum':['store.js']},'old':{'type':'string','maxLength':8000},'new':{'type':'string','maxLength':8000}},['path','old','new']),
        ('finish_repair','Propose the patch for independent checks. Cite source lines and explain the cause.',{
            'cause':{'type':'string','maxLength':1000},'source_lines':{'type':'array','items':{'type':'integer','minimum':1},'minItems':1,'maxItems':12}},['cause','source_lines'])]]


class RepairRun:
    def __init__(self,store,case,settings,provider_factory=CrusoeClient):
        self.store,self.case,self.settings,self.provider_factory = store,case,settings,provider_factory

    def event(self,kind,summary,**data):
        self.store.event(self.case,kind,summary,**data)

    async def check(self,workspace,site,label):
        workspace.check_integrity()
        output = workspace.protected/label
        receipt = await run_command([sys.executable,workspace.protected/'check_repair.py',
            '--site',site,'--fixture',workspace.protected/'fixture.json','--output',output],ROOT)
        receipt['result'] = json.loads((output/'result.json').read_text(encoding='utf-8'))
        log = workspace.protected/(label+'.json')
        log.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        receipt['artifact_id'] = self.store.register(self.case,log,'application/json')
        if (output/'evidence.zip').is_file():
            receipt['evidence_id'] = self.store.register(self.case,output/'evidence.zip','application/zip')
        workspace.check_integrity()
        self.event('repair_check',f'Protected {label} check completed.',check=receipt)
        return receipt

    async def run(self):
        if self.case.get('outcome')!='confirmed' or (self.case.get('verification') or {}).get('status')!='pass':
            raise ValueError('Repair requires an independently confirmed defect.')
        started = time.monotonic()
        repair = {'id':str(uuid4()),'status':'running','execution_mode':'live','calls':[],
                  'provider_requests':0,'usage_tokens':0,'patch_count':0}
        self.case.update(stage='repairing',repair=repair,message='Testing an isolated source repair; the original demo remains the baseline.')
        self.event('repair_started',self.case['message'])
        provider = None
        try:
            if not self.settings.api_key:
                raise ProviderError('missing_key','Repair requires the local Crusoe key.')
            workspace = RepairWorkspace(self.store.directory(self.case['id'])/repair['id'],self.case)
            repair['baseline_identity'] = workspace.baseline_identity
            repair['protected_hashes'] = workspace.protected_hashes
            baseline = await self.check(workspace,workspace.baseline,'baseline')
            repair['baseline'] = baseline
            if baseline['returncode']!=1 or baseline['result']['regression']!='fail' or baseline['result']['controls']['status']!='pass':
                raise ValueError('Baseline did not fail the intended behavior assertion with passing controls.')
            def request(kind,data):
                if kind=='request':
                    if repair['provider_requests']>=10:
                        raise ValueError('Repair provider request limit reached.')
                    repair['provider_requests']+=1
            provider = self.provider_factory(self.settings,on_request=request)
            repair['execution_mode'] = getattr(provider,'execution_mode','test')
            catalog = await provider.discover()
            repair['model'] = catalog['id']
            messages = [{'role':'system','content':'You repair an independently confirmed synthetic store defect. Read the isolated source, identify the cause with line citations, and make a minimal source patch. You can edit only store.js. Do not weaken rules, hide UI, replace totals with constants, or change tests/fixtures. You cannot run commands. The host independently runs frozen checks afterward. Use tools, then finish_repair; do not claim verified before those checks.'},
                        {'role':'user','content':json.dumps({'candidate':self.case['candidate'],'criteria':self.case['acceptance']})}]
            finished = False
            while not finished:
                if repair['usage_tokens'] + len(json.dumps(messages))//2 + self.settings.max_output_tokens > 50000:
                    raise ValueError('Repair token budget reached.')
                result = await provider.chat(messages,REPAIR_TOOLS)
                repair['calls'].append({k:result[k] for k in ['model','response_id','request_id','usage','finish_reason']})
                repair['usage_tokens'] += (result.get('usage') or {}).get('total_tokens') or len(json.dumps(messages))//2+self.settings.max_output_tokens
                assistant = result['message']
                messages.append(assistant)
                calls = assistant.get('tool_calls') or []
                if not 1<=len(calls)<=4:
                    raise ValueError('Repair model did not make bounded tool progress.')
                for call in calls:
                    function = call['function']
                    args = json.loads(function['arguments'])
                    try:
                        name = function['name']
                        if finished:
                            raise ValueError('Repair proposal already finished.')
                        if name=='read_source':
                            output = {'source':workspace.read(args['path'])}
                        elif name=='search_source':
                            query = args['query']
                            if not isinstance(query,str) or not 1<=len(query)<=200:
                                raise ValueError('Invalid search query.')
                            output = {'matches':[line for line in workspace.read(args['path']).splitlines() if query in line][:30]}
                        elif name=='patch_source':
                            workspace.patch(args['path'],args['old'],args['new'])
                            repair['patch_count'] = workspace.edits
                            self.event('repair_patch','Applied a constrained patch to isolated store.js.')
                            output = {'applied':True,'patch_count':workspace.edits}
                        elif name=='finish_repair':
                            lines = args['source_lines']
                            if not workspace.edits or not isinstance(args['cause'],str) or not 10<=len(args['cause'])<=1000 or not isinstance(lines,list) or not 1<=len(lines)<=12 or any(type(n)!=int or not 1<=n<=len((workspace.baseline/'store.js').read_text(encoding='utf-8').splitlines()) for n in lines):
                                raise ValueError('Patch and valid source-line diagnosis are required.')
                            repair['cause'],repair['source_lines'] = args['cause'],lines
                            output = {'proposed':True,'verified':False}
                            finished = True
                        else:
                            raise ValueError('Unknown repair tool.')
                    except (ValueError,KeyError,TypeError) as error:
                        output = {'error':str(error)[:250] if type(error)==ValueError else 'Invalid repair tool arguments.'}
                    messages.append({'role':'tool','tool_call_id':call['id'],'content':json.dumps(output)})
            workspace.check_integrity()
            before = (workspace.baseline/'store.js').read_text(encoding='utf-8')
            after = (workspace.candidate/'store.js').read_text(encoding='utf-8')
            patch = ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/demo_store/store.js',tofile='b/demo_store/store.js'))
            patch_path = workspace.protected/'repair.diff'
            patch_path.write_text(patch,encoding='utf-8')
            repair['diff_id'] = self.store.register(self.case,patch_path,'text/x-diff')
            node = shutil.which('node')
            if not node:
                raise ValueError('Node.js is required for the registered syntax check.')
            syntax = await run_command([node,'--check',workspace.candidate/'store.js'],ROOT,10)
            repair['syntax'] = syntax
            if syntax['returncode']:
                raise ValueError('Candidate JavaScript syntax check failed.')
            candidate = await self.check(workspace,workspace.candidate,'candidate')
            repair['candidate'] = candidate
            workspace.check_integrity()
            if candidate['returncode']!=0 or candidate['result']['regression']!='pass' or candidate['result']['controls']['status']!='pass':
                raise ValueError('Candidate did not pass the identical protected regression and required controls.')
            repair.update(status='verified',message='The identical protected regression fails on baseline and passes on the isolated candidate; required controls and syntax also pass.')
            self.case.update(outcome='fixed_verified',message='Repair verified in an isolated copy. The original demo still contains its seeded bug.')
        except asyncio.CancelledError:
            repair.update(status='rejected',message='Repair interrupted; established defect confirmation is preserved.')
            raise
        except Exception as error:
            repair.update(status='rejected',message=str(error) if isinstance(error,(ValueError,ProviderError)) else f'Repair blocked by {type(error).__name__}.')
            self.case.update(outcome='confirmed',message='Defect remains confirmed. '+repair['message'])
        finally:
            repair['elapsed_seconds'] = round(time.monotonic()-started,2)
            if provider:
                await provider.close()
            self.case['stage'] = 'finished'
            self.event('repair_finished',repair.get('message','Repair stopped.'),repair_status=repair['status'])
        return repair
