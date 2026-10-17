const id=location.pathname.split('/').pop();
(async()=>{
  try {
    const response=await fetch(`/api/runs/${encodeURIComponent(id)}`);
    if(!response.ok) throw new Error(response.status===404?'This report could not be found.':'The saved report is temporarily unavailable.');
    const data=await response.json();
    document.querySelector('#case-heading').textContent='Your report is in.';
    document.querySelector('#case-message').textContent=data.message;
    document.querySelector('#case-id').textContent=`CASE / ${data.id}`;
    document.querySelector('#case-date').textContent=new Date(data.created_at).toLocaleString();
    document.querySelector('#complaint').textContent=data.report.complaint;
    document.querySelector('#expected').textContent=data.report.expected_behavior;
    document.querySelector('#steps').textContent=data.report.steps || 'No steps supplied — that is okay.';
    document.querySelector('#page-url').textContent=data.report.page_url;
    document.querySelector('#case-details').hidden=false;
  } catch(error) { document.querySelector('#case-heading').textContent='We could not open this report.'; document.querySelector('#case-message').textContent=error.message; }
})();
