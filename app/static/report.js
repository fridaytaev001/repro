const reportDialog=document.querySelector('#report-dialog');
document.querySelector('#report-problem').addEventListener('click',()=>reportDialog.showModal());
document.querySelector('#report-from-checkout').addEventListener('click',()=>reportDialog.showModal());
document.querySelector('#close-report').addEventListener('click',()=>reportDialog.close());
document.querySelector('#report-form').addEventListener('submit',async event=>{
  event.preventDefault();
  const button=document.querySelector('#submit-report');
  const error=document.querySelector('#report-error');
  button.disabled=true; error.textContent='';
  try {
    const payload={...Object.fromEntries(new FormData(event.target)),target_id:'demo-store',page_url:location.origin+location.pathname};
    const response=await fetch('/api/reports',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!response.ok) throw new Error(response.status===503?'Your report could not be saved. Please try again.':'Please check the report fields and try again.');
    const result=await response.json();
    location.assign(result.status_url);
  } catch(reason) { error.textContent=reason.message || 'Could not connect. Please try again.'; button.disabled=false; }
});
