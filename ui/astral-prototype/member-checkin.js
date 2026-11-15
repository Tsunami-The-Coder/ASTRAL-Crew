(function(){
'use strict';var $=function(id){return document.getElementById(id);},busy=false,draft=null,lastCrew=null,keepProgress=false;
function crew(){return $('mission-crew-select').value||'AST-01';}
function bundle(){return window.AstralMissionView.current();}
function format(v,n){return typeof v==='number'?v.toFixed(n||0):'Missing';}
function time(v){return new Date(v).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'medium',timeZone:'UTC'})+' UTC';}
function cells(target,member){
 target.replaceChildren();var bio=member.biometrics||{},rad=member.radiation||{},gravity=member.gravity||{};
 [['Pulse',bio.heart_rate_bpm,'bpm',0],['RMSSD proxy',bio.hrv_rmssd_ms,'ms',1],['EDA',bio.eda_microsiemens,'µS',2],['Motion',bio.motion_level,'',2],['Radiation rate',rad.dose_equivalent_rate_msv_per_day,'mSv/day',2],['Bone trend',gravity.illustrative_bone_density_percent_of_start,'%',2]].forEach(function(item){
  var e=document.createElement('div'),label=document.createElement('small'),reading=document.createElement('b'),available=typeof item[1]==='number'&&Number.isFinite(item[1]);
  label.textContent=item[0]+(!available&&item[2]?' · '+item[2]:'');reading.textContent=available?item[1].toFixed(item[3])+(item[2]?' '+item[2]:''):'Missing';
  if(!available)e.className='missing-value';e.append(label,reading);target.append(e);
 });
}
function invalidate(){draft=null;$('member-draft-values').hidden=true;$('member-draft-time').textContent='';$('member-checkin-submit').disabled=true;}
function audio(){var id=crew(),sample=$('member-voice').value;
 if(!window.AstralBackendConnected){$('member-audio').removeAttribute('src');$('member-audio').load();$('member-input-note').textContent='Offline replay — start the local backend to play samples or submit entries.';return;}
 if(sample.startsWith('artemis-'))$('member-audio').src='/submission-assets/audio/'+sample+'.wav';
 else if(sample.startsWith('ravdess-')){var file=sample==='ravdess-calm'?'03-01-02-01-01-01-01.wav':sample==='ravdess-neutral'?'03-01-01-01-01-01-01.wav':'03-01-06-01-01-01-01.wav';$('member-audio').src='/submission-assets/audio/ravdess/'+file;}
 else $('member-audio').src='/api/lab/audio/'+sample+'?crew_id='+encodeURIComponent(id);
 $('member-input-note').textContent=sample.startsWith('artemis-')?'NASA recording · features only · no verified personal baseline.':sample.startsWith('ravdess-')?'RAVDESS Actor 01 · acted emotion label, not a stress label. Features only in this simulated crew entry.':'Synthetic sample · scored against this member’s generated baseline.';
}
function refresh(){var id=crew(),data=bundle(),entries=(data.member_entries||{})[id]||[],saved=(data.overview.snapshot.payload.crew_checkins||{})[id];
 if(lastCrew!==id){lastCrew=id;invalidate();$('member-voice').value='calm';$('member-wearable').value='rest';audio();$('member-checkin-result').textContent='';$('member-processing').hidden=true;}
 $('member-checkin-title').textContent='New entry · '+id;
 var latest=entries[0];
 if(latest){$('member-latest-time').textContent=time(latest.timestamp);$('member-latest-kind').textContent=latest.kind==='preloaded'?'PRELOADED · SYNTHETIC':'SUBMITTED · SYNTHETIC';cells($('member-latest-values'),latest.member);}
 else {var replay=(data.overview.snapshot.payload.crew||[]).find(function(m){return m.crew_id===id;});$('member-latest-time').textContent=time(data.overview.snapshot.timestamp);$('member-latest-kind').textContent='REPLAY · SYNTHETIC';if(replay)cells($('member-latest-values'),replay);else $('member-latest-values').replaceChildren();}
 $('member-history-count').textContent=entries.length+' '+(entries.length===1?'entry':'entries');$('member-history-list').replaceChildren();entries.forEach(function(e){var row=document.createElement('div');row.className='entry-history-row';var date=document.createElement('b'),detail=document.createElement('span');date.textContent=time(e.timestamp);detail.textContent=(e.kind==='preloaded'?'Preloaded reference':e.voice+' · '+e.wearable)+' · '+format(e.member.biometrics.heart_rate_bpm)+' bpm';row.append(date,detail);$('member-history-list').append(row);});
 var count=Object.keys(data.overview.snapshot.payload.crew_checkins||{}).length;$('checkin-roster-summary').textContent=count===5?'5 / 5 member inputs submitted.':count+' / 5 submitted · remaining members use generated references.';
 $('member-checkin-state').textContent=saved?'Submitted':'Preloaded';
}
async function request(path,body){
 if(!window.AstralBackendConnected)throw Error('Local backend unavailable. Start the demo server to generate or save entries.');
 var tracked=path==='/api/crew/checkin'||path==='/api/mission/analyze',interval=null,stopped=false;
 if(tracked){body.operation_id=crypto.randomUUID();keepProgress=true;document.querySelectorAll('.processing-track').forEach(function(track){track.hidden=false;track.setAttribute('aria-busy','true');Array.from(track.children).forEach(function(child){child.dataset.status='pending';});});}
 async function progress(){try{var response=await fetch('/api/progress',{cache:'no-store'}),state=await response.json();if(stopped||state.operation_id!==body.operation_id)return;document.querySelectorAll('.processing-track').forEach(function(track){Array.from(track.children).forEach(function(child,i){child.dataset.status=state.steps[['validation','features','analysis','save'][i]];});track.setAttribute('aria-busy',String(state.status==='running'));track.setAttribute('aria-label',state.status==='complete'?'Pipeline completed in '+(state.elapsed_ms/1000).toFixed(1)+' seconds':'Backend stage: '+state.stage);});}catch(error){/* Request result remains authoritative if progress polling is unavailable. */}}
 if(tracked)interval=setInterval(progress,200);
 try{var r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),data=await r.json();if(tracked)await progress();if(!r.ok)throw Error(data.error);return data;}
 catch(error){if(tracked)document.querySelectorAll('.processing-track').forEach(function(track){var active=track.querySelector('[data-status=running]')||track.firstElementChild;if(active)active.dataset.status='failed';});throw error;}
 finally{stopped=true;clearInterval(interval);if(tracked)document.querySelectorAll('.processing-track').forEach(function(track){track.setAttribute('aria-busy','false');});}
}
function lock(value,generating){busy=value;document.querySelectorAll('#mission-crew-tabs button,#member-voice,#member-wearable,#mission-crew-select,#crew-previous,#crew-next,#demo-run,#mission-checkin-cabin').forEach(function(e){e.disabled=value;});$('member-generate').disabled=value||!window.AstralBackendConnected;$('member-checkin-submit').disabled=value||!draft||!window.AstralBackendConnected;$('mission-recheck').disabled=value||!window.AstralBackendConnected;if(generating){keepProgress=false;document.querySelectorAll('.processing-track').forEach(function(track){track.hidden=true;});}else $('member-processing').hidden=!(value||keepProgress);$('member-processing').classList.toggle('running',value);}
$('mission-checkin-cabin').addEventListener('change',invalidate);
document.addEventListener('astral-connection-changed',function(){if(!busy){lock(false);audio();}});
$('member-voice').onchange=function(){invalidate();audio();};$('member-wearable').onchange=invalidate;
$('member-generate').onclick=async function(){if(busy)return;lock(true,true);$('member-checkin-result').textContent='Generating a draft…';try{draft=await request('/api/crew/draft',{crew_id:crew(),voice:$('member-voice').value,wearable:$('member-wearable').value,scenario:$('mission-checkin-cabin').value});cells($('member-draft-values'),draft.member);$('member-draft-values').hidden=false;$('member-draft-time').textContent='Draft generated '+time(draft.generated_at)+' · synthetic';$('member-checkin-result').textContent='Review the readings, then submit.';}catch(e){$('member-checkin-result').textContent=e.message;}finally{lock(false);}};
$('member-checkin-form').onsubmit=async function(event){event.preventDefault();if(busy||!draft)return;var id=crew();lock(true);$('member-checkin-result').textContent='Processing locally… input validation, features, models and cross-check.';try{var data=await request('/api/crew/checkin',{crew_id:id,draft_id:draft.draft_id});window.AstralMissionView.load(data,'Saved crew entries');var entry=data.overview.current_analysis,flags=entry.report.findings.filter(function(f){return f.crew_id===id||(f.crew_ids||[]).includes(id);});$('member-checkin-result').textContent='✓ Saved '+time(data.member_entries[id][0].timestamp)+' · '+window.AstralResultText.member(entry.report,id).title+'. '+window.AstralResultText.member(entry.report,id).detail;invalidate();}catch(e){$('member-checkin-result').textContent='Entry not saved: '+e.message;}finally{lock(false);}};
$('mission-recheck').onclick=async function(){if(busy)return;lock(true);$('mission-recheck-status').textContent='Checking saved crew inputs and cabin…';try{var data=await request('/api/mission/analyze',{scenario:$('mission-checkin-cabin').value});window.AstralMissionView.load(data,'Crew + cabin analysis');$('mission-recheck-status').textContent='✓ Analysis complete. '+window.AstralResultText.mission(data.overview.current_analysis.report);}catch(e){$('mission-recheck-status').textContent=e.message;}finally{lock(false);}};
document.addEventListener('astral-crew-selected',function(){refresh();if(!busy)lock(false);});document.addEventListener('astral-data-changed',function(){var actual=bundle().overview.snapshot.payload.scenario;if(Array.from($('mission-checkin-cabin').options).some(function(o){return o.value===actual;}))$('mission-checkin-cabin').value=actual;refresh();});refresh();lock(false);
})();
