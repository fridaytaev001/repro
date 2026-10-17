import json
import os
from pathlib import Path
import sys

import pytest

from app.agents.repair import RepairRun,RepairWorkspace,digest,run_command
from app.agents.coordinator import RunManager
from app.runs import CaseStore
from app.settings import Settings,ROOT
from test_verification import candidate_case


def confirmed_case(url='http://127.0.0.1:8000/'):
    case = candidate_case(url)
    case.update(outcome='confirmed',verification={'status':'pass'},stage='finished',
        report={'complaint':'Coupon vanished.','expected_behavior':'Preserve SAVE10.'})
    return case


class ScriptedRepair:
    execution_mode = 'test'
    def __init__(self,settings,on_request=None):
        self.index=0
        self.request=on_request
    async def discover(self):
        self.request('request',{})
        return {'id':'scripted-repair-test'}
    async def close(self):
        pass
    async def chat(self,messages,tools):
        self.request('request',{})
        source=(ROOT/'demo_store/store.js').read_text(encoding='utf-8')
        old=next(line.strip() for line in source.splitlines() if 'if (cart.editingFromReview)' in line)
        line=next(i for i,s in enumerate(source.splitlines(),1) if 'if (cart.editingFromReview)' in s)
        steps=[('read_source',{'path':'store.js'}),('patch_source',{'path':'store.js','old':old,
            'new':'// Preserve the applied coupon across address-only edits.'}),
            ('finish_repair',{'cause':'The review-origin address-save handler clears the valid coupon before rendering review. Preserve coupon state while updating the address.','source_lines':[line]})]
        name,args=steps[self.index]
        self.index+=1
        return {'message':{'role':'assistant','content':None,'tool_calls':[{'id':str(self.index),
            'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]},
            'usage':{'total_tokens':100},'model':'scripted-repair-test','response_id':str(self.index),
            'request_id':None,'finish_reason':'tool_calls'}


def test_source_paths_and_protected_fixture_are_not_repair_writable(tmp_path):
    workspace=RepairWorkspace(tmp_path/'job',confirmed_case())
    original=digest(ROOT/'demo_store/store.js')
    for path in ['../baseline/store.js','../protected/fixture.json','.env','index.html',str(ROOT/'demo_store/store.js')]:
        with pytest.raises(ValueError,match='Only candidate'):
            workspace.path(path)
    workspace.patch('store.js','let cart = freshCart();','let cart = freshCart(); // isolated test')
    assert digest(ROOT/'demo_store/store.js')==original
    (workspace.protected/'fixture.json').write_text('{}')
    with pytest.raises(ValueError,match='Protected'):
        workspace.patch('store.js','let cart','const cart')


@pytest.mark.asyncio
async def test_registered_process_does_not_inherit_credentials(tmp_path,monkeypatch):
    monkeypatch.setenv('CRUSOE_API_KEY','synthetic-must-not-leak')
    result=await run_command([sys.executable,'-c',"import os; print('CRUSOE_API_KEY' in os.environ)"],tmp_path)
    assert result['returncode']==0
    assert result['stdout'].strip()=='False'


@pytest.mark.browser
@pytest.mark.asyncio
async def test_real_before_after_gate_uses_same_frozen_check_and_preserves_original(tmp_path):
    case=confirmed_case()
    original=digest(ROOT/'demo_store/store.js')
    result=await RepairRun(CaseStore(tmp_path),case,Settings(api_key='synthetic'),ScriptedRepair).run()
    assert result['status']=='verified',result
    assert result['execution_mode']=='test'
    assert case['outcome']=='fixed_verified'
    assert result['baseline']['returncode']==1
    assert result['baseline']['result']['regression']=='fail'
    assert result['candidate']['returncode']==0
    assert result['candidate']['result']['regression']=='pass'
    assert result['candidate']['result']['controls']['status']=='pass'
    assert digest(ROOT/'demo_store/store.js')==original


@pytest.mark.asyncio
async def test_setup_failure_cannot_count_as_baseline_proof(tmp_path,monkeypatch):
    case=confirmed_case()
    async def setup_failure(self,*args):
        return {'returncode':2,'result':{'regression':'inconclusive','controls':{'status':'not_run'}}}
    monkeypatch.setattr(RepairRun,'check',setup_failure)
    result=await RepairRun(CaseStore(tmp_path),case,Settings(api_key='synthetic'),ScriptedRepair).run()
    assert result['status']=='rejected'
    assert case['outcome']=='confirmed'
    assert not result['calls']


@pytest.mark.asyncio
async def test_candidate_failure_preserves_confirmation(tmp_path,monkeypatch):
    case=confirmed_case()
    async def failure(self,*args):
        return {'returncode':1,'result':{'regression':'fail','controls':{'status':'pass'}}}
    monkeypatch.setattr(RepairRun,'check',failure)
    result=await RepairRun(CaseStore(tmp_path),case,Settings(api_key='synthetic'),ScriptedRepair).run()
    assert result['status']=='rejected'
    assert case['outcome']=='confirmed'
    assert result['candidate']['returncode']==1


@pytest.mark.asyncio
async def test_queued_repair_cancel_preserves_confirmed_defect(tmp_path):
    case=confirmed_case()
    manager=RunManager(CaseStore(tmp_path),lambda:Settings())
    manager.enqueue_repair(case)
    manager.cancel(case)
    assert case['outcome']=='confirmed'
    count=case['event_count']
    manager.cancel(case)
    assert case['event_count']==count
