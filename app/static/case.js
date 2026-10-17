const id=location.pathname.split('/').pop();
const endpoint='/api/runs/'+encodeURIComponent(id);
let cursor=0;
let polling=false;
const text=(selector,value)=>{document.querySelector(selector).textContent=value??'';};
function element(tag,value){const node=document.createElement(tag);node.textContent=value;return node;}
function screenshot(artifactId){
  const link=document.createElement('a');
  link.href=endpoint+'/artifacts/'+encodeURIComponent(artifactId);
  link.target='_blank';link.rel='noopener';
  const image=document.createElement('img');image.src=link.href;image.alt='Actual browser evidence';image.loading='lazy';
  link.append(image);return link;
}
function render(data){
  const stages={received:'Your report is in.',queued:'An investigation is queued.',investigating:'Following the evidence.',verifying:'Checking in a fresh session.',awaiting_verification:'A candidate worth checking.',finished:'The investigation stopped.'};
  const outcomes={fixed_verified:'A repair passed in an isolated copy.',confirmed:'The bug is independently confirmed.',blocked:'The investigation is blocked.',not_reproduced:'No reproduction established.',needs_information:'More information is needed.'};
  text('#case-heading',outcomes[data.outcome]||stages[data.stage]||'Your report is in.');
  text('#case-message',data.message);
  let mode=data.execution_mode==='live'&&data.calls?.length?'LIVE CRUSOE':data.execution_mode==='test'?'TEST EXECUTION':data.execution_mode==='live'?'CRUSOE / NO MODEL RESPONSE':'PROVIDER UNAVAILABLE';
  if(!data.investigation_enabled)mode='INVESTIGATION DISABLED';
  text('#execution-mode',mode+' / '+(data.outcome||data.stage).replaceAll('_',' ').toUpperCase());
  text('#case-id','CASE / '+data.id);
  text('#case-date',new Date(data.created_at).toLocaleString());
  text('#complaint',data.report.complaint);text('#expected',data.report.expected_behavior);
  text('#steps',data.report.steps||'No steps supplied — that is okay.');text('#page-url',data.report.page_url);
  document.querySelector('#case-details').hidden=false;
  const active=['queued','investigating','verifying','repairing'].includes(data.stage);
  document.querySelector('#cancel-run').hidden=!active;
  document.querySelector('#start-run').hidden=active||!data.investigation_enabled||data.stage==='awaiting_verification'||['confirmed','fixed_verified'].includes(data.outcome);
  document.querySelector('#verify-run').hidden=active||!data.investigation_enabled||!data.candidate||['confirmed','fixed_verified'].includes(data.outcome);
  document.querySelector('#repair-run').hidden=active||!data.investigation_enabled||data.outcome!=='confirmed';
  document.querySelector('#repair-panel').hidden=!data.repair;
  if(data.repair){
    const r=data.repair;
    text('#repair-heading',r.status==='verified'?'Verified repair, original demo preserved':r.status==='running'?'Testing an isolated source change':'Repair rejected; defect remains confirmed');
    text('#repair-message',r.message||'Frozen baseline and candidate checks are running.');
    text('#repair-cause',r.cause?'Proposed cause: '+r.cause+' (store.js lines '+r.source_lines.join(', ')+')':'');
    text('#repair-proof','Baseline regression: '+(r.baseline?.result?.regression||'not measured')+' · Candidate regression: '+(r.candidate?.result?.regression||'not measured')+' · Candidate controls: '+(r.candidate?.result?.controls?.status||'not measured'));
    document.querySelector('#repair-diff').hidden=!r.diff_id;
    if(r.diff_id)document.querySelector('#repair-diff').href=endpoint+'/artifacts/'+encodeURIComponent(r.diff_id);
  }
  document.querySelector('#handoff-panel').hidden=active;
  text('#handoff-note',data.candidate?'Includes actual replay steps, frozen criteria, screenshots/traces, and separate reproduction and regression tests. The reproduction test passes on the buggy target; the regression test should fail until a repair is verified.':'Report and existing evidence are available. Replay and tests are unavailable until a candidate exists.');
  for(const [selector,kind] of [['#download-report-md','markdown'],['#download-report-json','json'],['#download-bundle','bundle']])document.querySelector(selector).href=endpoint+'/exports/'+kind;
  text('#run-budget',data.model?data.model+' · '+(data.browser_action_count||0)+' browser actions · '+(data.provider_request_count||0)+' provider requests':'');
  document.querySelector('#criteria-panel').hidden=!data.acceptance;
  if(data.acceptance){
    text('#criteria-version','FROZEN ACCEPTANCE CHECKS / VERSION '+data.acceptance.version);
    const list=document.querySelector('#criteria');list.replaceChildren();
    for(const check of data.acceptance.checks){list.append(element('li',check.description+' — expected: '+check.expected));}
  }
  document.querySelector('#candidate-panel').hidden=!data.candidate;
  if(data.candidate){
    text('#candidate-label',['confirmed','fixed_verified'].includes(data.outcome)?'CANDIDATE / INDEPENDENTLY CONFIRMED':'CANDIDATE / REQUIRES INDEPENDENT VERIFICATION');
    text('#candidate-summary',data.candidate.summary);text('#candidate-expected',data.candidate.expected_behavior);text('#candidate-observed',data.candidate.observed_behavior);
    const steps=document.querySelector('#candidate-steps');steps.replaceChildren();
    for(const step of data.candidate.steps){steps.append(element('li',step.action+(step.target?' '+step.target.name:'')+(step.value?' → '+step.value:'')+(step.url?' '+step.url:'')));}
    const evidence=document.querySelector('#candidate-evidence');
    if(evidence.dataset.attempt!==data.attempt_id){evidence.replaceChildren(...data.candidate.evidence_ids.map(screenshot));evidence.dataset.attempt=data.attempt_id;}
  }
  document.querySelector('#verification-panel').hidden=!data.verification;
  if(data.verification){
    const v=data.verification;
    text('#verification-heading',data.stage==='verifying'?'Fresh-session replay in progress':v.status==='pass'?'Rule violation observed independently':v.status==='fail'?'Candidate was not reproduced':'Verification is inconclusive');
    text('#verification-reason',v.reason||'Fresh-session replay is running.');
    text('#verification-budget',(v.action_count||0)+' replay actions · '+(v.elapsed_seconds??'…')+' seconds · '+v.policy);
    const list=document.querySelector('#verification-values');list.replaceChildren();
    for(const row of v.observations){if(row.values.total!==null)list.append(element('li','Step '+row.step+': total '+row.values.total+'; coupon '+(row.values.coupon||'none')+'; '+row.values.stage));}
    const evidence=document.querySelector('#verification-evidence');
    const ids=(v.violations||[]).map(x=>x.evidence_id);
    const key=v.id+ids.join(',');
    if(evidence.dataset.version!==key){evidence.replaceChildren(...ids.map(screenshot));evidence.dataset.version=key;}
  }
}
function appendEvents(events){
  if(events.length)document.querySelector('#timeline-panel').hidden=false;
  for(const event of events){
    const item=document.createElement('li');
    item.append(element('span',new Date(event.timestamp).toLocaleTimeString()),element('strong',event.summary));
    if(event.experiment)item.append(element('p',event.experiment));
    if(event.prior_result)item.append(element('p','Previous result: '+event.prior_result));
    if(event.result?.observation){const details=document.createElement('details');details.append(element('summary','Read browser observation'),element('pre',event.result.observation.text));const a=document.createElement('a');a.href=endpoint+'/artifacts/'+encodeURIComponent(event.result.evidence_id);a.textContent='Open actual screenshot ↗';a.target='_blank';a.rel='noopener';details.append(a);item.append(details);}
    document.querySelector('#timeline').append(item);
    cursor=event.seq;
  }
}
async function refresh(){
  if(polling)return;
  polling=true;
  try{
    const response=await fetch(endpoint);
    if(!response.ok)throw new Error(response.status===404?'This report could not be found.':'The saved report is temporarily unavailable.');
    const data=await response.json();render(data);
    const eventsResponse=await fetch(endpoint+'/events?after='+cursor);
    if(eventsResponse.ok)appendEvents((await eventsResponse.json()).events);
    if(['queued','investigating','verifying','repairing'].includes(data.stage))setTimeout(refresh,1500);
  }catch(error){text('#case-heading','We could not open this report.');text('#case-message',error.message);}
  finally{polling=false;}
}
for(const [selector,action] of [['#start-run','start'],['#cancel-run','cancel'],['#verify-run','verify'],['#repair-run','repair']]){
  document.querySelector(selector).addEventListener('click',async event=>{
    event.target.disabled=true;text('#run-error','');
    try{const response=await fetch(endpoint+'/'+action,{method:'POST'});if(!response.ok){const detail=(await response.json()).detail;throw new Error(typeof detail==='string'?detail:'Could not update this case.');}await refresh();}
    catch(error){text('#run-error',error.message);}finally{event.target.disabled=false;}
  });
}
refresh();
